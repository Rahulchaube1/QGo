# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Base coder — core chat + edit loop for QGo."""

from __future__ import annotations

import subprocess
from abc import abstractmethod
from pathlib import Path

from qgo.config import Config
from qgo.llm.base import BaseLLM
from qgo.models import EditBlock, FileContext, Message, TokenUsage

# ─── System prompt ────────────────────────────────────────────────────────

_SYSTEM_PROMPT_TEMPLATE = """\
You are QGo — an exceptionally skilled senior software engineer and AI coding assistant.
You have deep expertise across all programming languages, frameworks, and paradigms.

Your capabilities:
- Understand complex codebases quickly and accurately
- Write clean, idiomatic, well-documented code
- Fix bugs with surgical precision
- Refactor code while preserving all existing behavior
- Add features following the existing patterns and conventions
- Write comprehensive tests
- Explain your changes clearly and concisely

## Your working context
{repo_map}

## Files in this conversation
{files_section}

## Rules
1. **Be precise**: Only change what is necessary. Do not refactor unrelated code.
2. **Be complete**: Always provide the complete, working implementation.
3. **Follow conventions**: Match the existing code style, naming, and patterns.
4. **Explain changes**: Briefly describe what you changed and why.
5. **Edit format**: {edit_format_instructions}
"""

_EDIT_FORMAT_INSTRUCTIONS: dict[str, str] = {
    "editblock": """\
Use SEARCH/REPLACE blocks to make changes. Format:

<<<<<<< SEARCH
(exact existing code to replace)
=======
(new replacement code)
>>>>>>> REPLACE

Rules:
- The SEARCH block must match the existing file content EXACTLY (whitespace, indentation, etc.)
- To create a new file, use an empty SEARCH block
- Multiple edits can be made with multiple SEARCH/REPLACE blocks
- Always include the filename before each block like: `path/to/file.py`
""",
    "whole": """\
Return the complete content of each file you modify, wrapped in a fenced code block:

```python
# path/to/file.py
(complete file content here)
```

Always include the full file — never truncate or use ellipsis.
""",
    "udiff": """\
Return changes as a unified diff:

```diff
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,5 +10,7 @@
 (context)
-old line
+new line
 (context)
```
""",
}


class BaseCoder:
    """Core chat and code-editing engine.

    Subclasses implement *parse_edits()* and *apply_edits()* for a specific
    edit format (SEARCH/REPLACE, whole-file, unified diff, etc.).
    """

    edit_format: str = "editblock"

    def __init__(
        self,
        llm: BaseLLM,
        git_repo=None,
        repo_map=None,
        config: Config | None = None,
        io=None,
    ) -> None:
        self.llm = llm
        self.git_repo = git_repo
        self.repo_map = repo_map
        self.config = config or Config()
        self.io = io  # QGoIO instance for terminal output

        self.chat_files: list[FileContext] = []
        self.messages: list[Message] = []
        self.total_usage = TokenUsage()
        self.pending_images: list[str] = []  # Images queued for the next message

    # ─── File management ──────────────────────────────────────────────

    def add_file(self, path: str | Path, read_only: bool = False) -> bool:
        """Add a file to the conversation context.

        Returns True if the file was added, False if it was already present.
        """
        p = Path(path).resolve()
        if not p.exists():
            self._warn(f"File not found: {path}")
            return False
        # Avoid duplicates
        for existing in self.chat_files:
            if existing.path == p:
                return False
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            tokens = self.llm.count_tokens(content)
            fc = FileContext(path=p, content=content, tokens=tokens, read_only=read_only)
            self.chat_files.append(fc)
            return True
        except Exception as exc:
            self._warn(f"Cannot read {path}: {exc}")
            return False

    def drop_file(self, path: str | Path) -> bool:
        """Remove a file from the conversation context."""
        p = Path(path)
        for i, fc in enumerate(self.chat_files):
            if fc.path == p or fc.path.name == p.name:
                self.chat_files.pop(i)
                return True
        return False

    def refresh_files(self) -> None:
        """Re-read all chat files from disk (picks up external changes)."""
        for fc in self.chat_files:
            if fc.path.exists():
                fc.content = fc.path.read_text(encoding="utf-8", errors="ignore")
                fc.tokens = self.llm.count_tokens(fc.content)

    # ─── Main chat loop ───────────────────────────────────────────────

    def run(self, user_message: str) -> str:
        """Process a user message: send to LLM, apply edits, return response.

        This is the main entry point for the chat loop.
        """
        self.refresh_files()

        # Capture and clear any pending images
        images = self.pending_images[:]
        self.pending_images.clear()

        # Build message list (include images in the current turn if any)
        messages = self._build_messages(user_message, images=images or None)

        # Send to LLM
        response = self._send(messages)

        # Record in history (images attached to this user turn)
        self.messages.append(Message(role="user", content=user_message, images=images))
        self.messages.append(Message(role="assistant", content=response))

        # Apply edits
        edited_files = self.apply_edits(response)

        # Auto-commit
        if edited_files and self.config.auto_commits and self.git_repo:
            commit_hash = self.git_repo.auto_commit(
                edited_files,
                attribution="QGo",
            )
            if commit_hash and self.io:
                self.io.print_commit(commit_hash, user_message[:60])

        # Auto-lint
        if edited_files and self.config.auto_lint and self.config.lint_cmd:
            errors = self.run_linter(edited_files)
            if errors:
                self._info("Lint errors found, asking AI to fix...")
                fix_response = self.fix_linter_errors(errors, edited_files)
                return response + "\n\n---\n\n" + fix_response

        # Refresh files after edits
        self.refresh_files()
        return response

    def _send(self, messages: list[dict]) -> str:
        """Send messages to the LLM and return the complete response."""
        # Warn if the estimated token count approaches the context window
        try:
            def _content_text(content) -> str:
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                return ""

            estimated = sum(
                self.llm.count_tokens(_content_text(m.get("content")))
                for m in messages
            )
            limit = self.llm.context_window
            if estimated > limit * 0.9:
                self._warn(
                    f"⚠️  Context is ~{estimated:,} tokens, close to the "
                    f"{limit:,}-token limit for {self.llm.model_name}. "
                    "Consider using /drop to remove files or /clear to reset history."
                )
        except Exception:
            pass  # Token estimation is best-effort; never block the request

        stream = self.config.stream

        if stream and self.io:
            iterator = self.llm.complete(messages, stream=True)
            if hasattr(iterator, "__iter__"):
                response = self.io.stream_response(iterator)
            else:
                response = str(iterator)
        else:
            result = self.llm.complete(messages, stream=False)
            response = str(result)
            if self.io:
                self.io.print_assistant(response)

        return response

    # ─── Prompt building ──────────────────────────────────────────────

    def _build_messages(self, user_message: str, images: list[str] | None = None) -> list[dict]:
        """Build the full message list to send to the LLM."""
        result: list[dict] = []

        # System prompt
        system = self._build_system_prompt()
        result.append({"role": "system", "content": system})

        # Previous conversation history
        for msg in self.messages[-20:]:  # Keep last 20 messages
            result.append(msg.to_dict())

        # Current user message — include images if any (vision models)
        if images:
            content: list = [{"type": "text", "text": user_message}]
            for img in images:
                content.append({"type": "image_url", "image_url": {"url": img}})
            result.append({"role": "user", "content": content})
        else:
            result.append({"role": "user", "content": user_message})
        return result

    def _build_system_prompt(self) -> str:
        """Build the system prompt including file contents and repo map."""
        # Files section
        if self.chat_files:
            files_parts = []
            for fc in self.chat_files:
                mode = " (read-only)" if fc.read_only else ""
                files_parts.append(
                    f"### {fc.path}{mode}\n"
                    f"```{fc.language}\n{fc.content}\n```"
                )
            files_section = "\n\n".join(files_parts)
        else:
            files_section = "(no files added yet — use /add <filename> to add files)"

        # Repo map section
        repo_map_str = ""
        if self.repo_map:
            chat_paths = [str(fc.path) for fc in self.chat_files]
            repo_map_str = self.repo_map.get_repo_map(chat_files=chat_paths)
            if repo_map_str:
                repo_map_str = f"\n{repo_map_str}\n"

        edit_instructions = _EDIT_FORMAT_INSTRUCTIONS.get(
            self.edit_format, _EDIT_FORMAT_INSTRUCTIONS["editblock"]
        )

        return _SYSTEM_PROMPT_TEMPLATE.format(
            repo_map=repo_map_str or "(no repo map available)",
            files_section=files_section,
            edit_format_instructions=edit_instructions,
        )

    # ─── Edits (abstract) ─────────────────────────────────────────────

    @abstractmethod
    def parse_edits(self, response: str) -> list[EditBlock]:
        """Parse edit blocks from the LLM response."""
        ...

    @abstractmethod
    def apply_edits(self, response: str) -> list[str]:
        """Apply edits from the LLM response, return list of edited file paths."""
        ...

    # ─── Linting / testing ────────────────────────────────────────────

    def run_linter(self, files: list[str]) -> str | None:
        """Run the configured linter on the given files. Returns errors or None."""
        if not self.config.lint_cmd:
            return None
        try:
            cmd = self.config.lint_cmd.split() + [str(f) for f in files]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return (result.stdout + result.stderr).strip()
        except Exception:
            pass
        return None

    def fix_linter_errors(self, errors: str, files: list[str]) -> str:
        """Ask the LLM to fix linter errors."""
        error_msg = (
            f"The linter found these errors:\n\n```\n{errors}\n```\n\n"
            f"Please fix all of these errors. Do not change anything else."
        )
        return self.run(error_msg)

    def run_tests(self) -> str | None:
        """Run the configured test command. Returns output or None."""
        if not self.config.test_cmd:
            return None
        try:
            result = subprocess.run(
                self.config.test_cmd.split(),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return (result.stdout + result.stderr).strip()
        except Exception:
            pass
        return None

    # ─── Helpers ──────────────────────────────────────────────────────

    def _info(self, msg: str) -> None:
        if self.io:
            self.io.print_info(msg)

    def _warn(self, msg: str) -> None:
        if self.io:
            self.io.print_warning(msg)

    def _error(self, msg: str) -> None:
        if self.io:
            self.io.print_error(msg)

    @property
    def token_count(self) -> int:
        """Approximate total tokens used so far."""
        total = 0
        for fc in self.chat_files:
            total += fc.tokens
        for msg in self.messages:
            total += self.llm.count_tokens(msg.content)
        return total
