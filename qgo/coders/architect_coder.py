# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Architect coder — two-pass: plan with a strong model, implement with a fast model."""

from __future__ import annotations

from qgo.coders.base_coder import BaseCoder
from qgo.coders.editblock_coder import EditBlockCoder
from qgo.llm.base import BaseLLM
from qgo.models import EditBlock

_ARCHITECT_SYSTEM = """\
You are an expert software architect. Your task is to analyze the request and produce
a detailed, step-by-step implementation plan.

Think through:
1. Which files need to be created or modified?
2. What are the key changes to each file?
3. What is the correct order of operations?
4. Are there any edge cases or potential issues?

Produce a clear, structured plan. Do NOT write the actual code — just describe what needs
to be done in each file. Be specific about function names, class names, and logic.
"""

_ARCHITECT_TO_EDITOR = """\
Here is the implementation plan from the architect:

{plan}

Now implement all of these changes exactly as planned.
Use SEARCH/REPLACE blocks to make the edits.
"""


class ArchitectCoder(BaseCoder):
    """Two-pass coder: architect model plans, editor model implements.

    Pass 1 (Architect): Uses a strong reasoning model (e.g., o1, claude-3-opus)
                         to produce a detailed implementation plan.
    Pass 2 (Editor):    Uses a fast coding model (e.g., gpt-4o, claude-3-5-sonnet)
                         to implement the plan with SEARCH/REPLACE blocks.
    """

    edit_format = "architect"

    def __init__(
        self,
        llm: BaseLLM,
        editor_llm: BaseLLM | None = None,
        **kwargs,
    ) -> None:
        super().__init__(llm=llm, **kwargs)
        # If no separate editor LLM provided, use the same one
        self.editor_llm = editor_llm or llm
        self._editor_coder = EditBlockCoder(
            llm=self.editor_llm,
            git_repo=self.git_repo,
            repo_map=self.repo_map,
            config=self.config,
            io=self.io,
        )

    def run(self, user_message: str) -> str:
        """Two-pass execution: plan then implement."""
        self.refresh_files()

        # --- Pass 1: Architectural planning ---
        self._info("🏗️  Architect is planning the changes...")
        plan_messages = self._build_architect_messages(user_message)
        plan = self._send_with_system(plan_messages, _ARCHITECT_SYSTEM)

        if self.io:
            self.io.print_info(f"\n📋 Plan:\n{plan}\n")

        # --- Pass 2: Implementation ---
        self._info("⚙️  Editor is implementing the plan...")
        implement_message = _ARCHITECT_TO_EDITOR.format(plan=plan)

        # Sync chat files to editor coder
        self._editor_coder.chat_files = self.chat_files
        self._editor_coder.messages = self.messages.copy()

        result = self._editor_coder.run(implement_message)

        # Sync back
        self.chat_files = self._editor_coder.chat_files
        self.messages = self._editor_coder.messages

        return f"**Plan:**\n{plan}\n\n**Implementation:**\n{result}"

    def parse_edits(self, response: str) -> list[EditBlock]:
        return []

    def apply_edits(self, response: str) -> list[str]:
        return []

    def _build_architect_messages(self, user_message: str) -> list[dict]:
        """Build messages for the architect pass (no edit format instructions)."""
        messages = []

        # Include file context
        if self.chat_files:
            file_parts = []
            for fc in self.chat_files:
                file_parts.append(
                    f"### {fc.path}\n```{fc.language}\n{fc.content}\n```"
                )
            files_context = "\n\n".join(file_parts)
            messages.append({
                "role": "user",
                "content": f"Here are the relevant files:\n\n{files_context}"
            })
            messages.append({
                "role": "assistant",
                "content": "I've reviewed the files. What changes would you like me to plan?"
            })

        messages.append({"role": "user", "content": user_message})
        return messages

    def _send_with_system(self, messages: list[dict], system: str) -> str:
        """Send messages with a custom system prompt."""
        full_messages = [{"role": "system", "content": system}] + messages
        result = self.llm.complete(full_messages, stream=False)
        return str(result)
