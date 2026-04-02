# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Slash-command handler for QGo's interactive REPL."""

from __future__ import annotations

import glob as glob_module
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qgo.coders.base_coder import BaseCoder
    from qgo.ui.terminal import QGoIO


class CommandHandler:
    """Processes /commands typed in the QGo REPL.

    Returns True if the command was handled (caller should not also send to LLM),
    or False if it was not a command.
    """

    def __init__(self, coder: "BaseCoder", io: "QGoIO") -> None:
        self.coder = coder
        self.io = io

    def handle(self, text: str) -> bool:
        """Handle a command string. Returns True if it was a command."""
        text = text.strip()
        if not text.startswith("/"):
            return False

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = {
            "/add": self._cmd_add,
            "/drop": self._cmd_drop,
            "/files": self._cmd_files,
            "/diff": self._cmd_diff,
            "/commit": self._cmd_commit,
            "/undo": self._cmd_undo,
            "/clear": self._cmd_clear,
            "/model": self._cmd_model,
            "/models": self._cmd_models,
            "/tokens": self._cmd_tokens,
            "/map": self._cmd_map,
            "/run": self._cmd_run,
            "/web": self._cmd_web,
            "/browse": self._cmd_browse,
            "/image": self._cmd_image,
            "/git": self._cmd_git,
            "/paste": self._cmd_paste,
            "/ls": self._cmd_ls,
            "/config": self._cmd_config,
            "/help": self._cmd_help,
            "/exit": self._cmd_exit,
            "/quit": self._cmd_exit,
            "/agent": self._cmd_agent,
        }.get(cmd)

        if handler:
            handler(args)
            return True

        self.io.print_warning(f"Unknown command: {cmd}  (type /help for commands)")
        return True

    # ─── Command implementations ──────────────────────────────────────

    def _cmd_add(self, args: str) -> None:
        if not args:
            self.io.print_warning("Usage: /add <file> [file2 ...]")
            return
        # Support globs
        added = []
        patterns = args.split()
        for pattern in patterns:
            matches = glob_module.glob(pattern, recursive=True)
            if matches:
                for match in matches:
                    if self.coder.add_file(match):
                        added.append(match)
                        self.io.print_success(f"Added: {match}")
            else:
                if self.coder.add_file(pattern):
                    added.append(pattern)
                    self.io.print_success(f"Added: {pattern}")
                else:
                    self.io.print_warning(f"File not found: {pattern}")
        if not added:
            self.io.print_warning("No files were added.")

    def _cmd_drop(self, args: str) -> None:
        if not args:
            self.io.print_warning("Usage: /drop <file> [file2 ...]")
            return
        for name in args.split():
            if self.coder.drop_file(name):
                self.io.print_success(f"Dropped: {name}")
            else:
                self.io.print_warning(f"Not in context: {name}")

    def _cmd_files(self, args: str) -> None:
        self.io.print_files(self.coder.chat_files)

    def _cmd_diff(self, args: str) -> None:
        if self.coder.git_repo:
            diff = self.coder.git_repo.get_diff()
            if diff:
                self.io.print_diff(diff)
            else:
                self.io.print_info("No uncommitted changes.")
        else:
            self.io.print_warning("Git not available.")

    def _cmd_commit(self, args: str) -> None:
        if not self.coder.git_repo:
            self.io.print_warning("Git not available.")
            return
        msg = args or "QGo: manual commit"
        commit_hash = self.coder.git_repo.commit(msg)
        if commit_hash:
            self.io.print_commit(commit_hash, msg)
        else:
            self.io.print_info("Nothing to commit.")

    def _cmd_undo(self, args: str) -> None:
        if not self.coder.git_repo:
            self.io.print_warning("Git not available.")
            return
        self.coder.git_repo.undo_last_commit()
        self.io.print_success("Undid last commit (changes kept in working tree).")

    def _cmd_clear(self, args: str) -> None:
        self.coder.messages.clear()
        self.io.print_success("Chat history cleared.")

    def _cmd_model(self, args: str) -> None:
        if not args:
            self.io.print_info(f"Current model: {self.coder.llm.model_name}")
            return
        from qgo.llm.litellm_provider import LiteLLMProvider
        self.coder.llm = LiteLLMProvider(
            model=args,
            api_key=self.coder.config.api_key,
            api_base=self.coder.config.api_base,
        )
        self.coder.config.model = args
        self.io.print_success(f"Switched to model: {args}")

    def _cmd_models(self, args: str) -> None:
        from qgo.llm.model_info import format_model_table
        self.io.print_models_table(format_model_table())

    def _cmd_tokens(self, args: str) -> None:
        count = self.coder.token_count
        self.io.print_info(f"Approximate tokens in context: {count:,}")

    def _cmd_map(self, args: str) -> None:
        if self.coder.repo_map:
            chat_files = [str(fc.path) for fc in self.coder.chat_files]
            map_text = self.coder.repo_map.get_repo_map(chat_files=chat_files)
            self.io.print_repo_map(map_text)
        else:
            self.io.print_warning("Repo map not available.")

    def _cmd_run(self, args: str) -> None:
        if not args:
            self.io.print_warning("Usage: /run <shell command>")
            return
        try:
            cmd = shlex.split(args)
            result = subprocess.run(
                cmd, shell=False, capture_output=True, text=True, timeout=60
            )
            output = (result.stdout + result.stderr).strip()
            if output:
                self.io.print_info(f"$ {args}\n{output}")
                # Add to conversation context
                self.coder.messages.append({
                    "role": "user",
                    "content": f"Output of `{args}`:\n```\n{output}\n```",
                })
            else:
                self.io.print_info(f"$ {args}\n(no output)")
        except subprocess.TimeoutExpired:
            self.io.print_error("Command timed out after 60 seconds.")
        except Exception as exc:
            self.io.print_error(f"Error running command: {exc}")

    def _cmd_web(self, args: str) -> None:
        if not args:
            self.io.print_warning("Usage: /web <url>")
            return
        try:
            from qgo.utils.web_scraper import fetch_url
            self.io.print_info(f"Fetching: {args}")
            content = fetch_url(args)
            if content:
                # Add to conversation context
                self.coder.messages.append({
                    "role": "user",
                    "content": f"Content of {args}:\n\n{content[:8000]}",
                })
                self.io.print_success(f"Fetched {len(content)} characters from {args}")
            else:
                self.io.print_warning("No content retrieved.")
        except Exception as exc:
            self.io.print_error(f"Failed to fetch URL: {exc}")

    def _cmd_browse(self, args: str) -> None:
        """Fetch and display a web page with rich browser-like formatting."""
        if not args:
            self.io.print_warning("Usage: /browse <url>")
            return
        url = args.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            from qgo.utils.web_scraper import fetch_page_info
            self.io.print_info(f"Loading: {url}")
            page_info = fetch_page_info(url)
            self.io.print_browse(page_info)
            content = page_info.get("content", "")
            if content:
                self.coder.messages.append({
                    "role": "user",
                    "content": f"Web page content from {url}:\n\n{content[:8000]}",
                })
                self.io.print_success(
                    f"Page content added to context ({len(content):,} chars)."
                )
        except Exception as exc:
            self.io.print_error(f"Failed to browse {url}: {exc}")

    def _cmd_image(self, args: str) -> None:
        """Attach one or more images (local path or URL) to the next message."""
        if not args:
            self.io.print_warning("Usage: /image <path_or_url> [path2 ...]")
            return
        for src in args.split():
            src = src.strip()
            if not src:
                continue
            p = Path(src)
            if p.exists() and p.is_file():
                # Encode local file as a base64 data URL
                try:
                    import base64
                    ext = p.suffix.lower().lstrip(".")
                    mime = {
                        "jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "gif": "image/gif",
                        "webp": "image/webp", "bmp": "image/bmp",
                    }.get(ext, "image/png")
                    data = base64.b64encode(p.read_bytes()).decode("ascii")
                    data_url = f"data:{mime};base64,{data}"
                    self.coder.pending_images.append(data_url)
                    self.io.print_image_added(src, len(self.coder.pending_images))
                except Exception as exc:
                    self.io.print_error(f"Failed to load image {src}: {exc}")
            elif src.startswith(("http://", "https://")):
                # Remote image — pass URL directly (vision models support this)
                self.coder.pending_images.append(src)
                self.io.print_image_added(src, len(self.coder.pending_images))
            else:
                self.io.print_warning(f"Image not found: {src}")
        count = len(self.coder.pending_images)
        if count:
            self.io.print_info(
                f"  {count} image(s) queued — they will be sent with your next message."
            )

    def _cmd_git(self, args: str) -> None:
        if not args:
            self.io.print_warning("Usage: /git <git subcommand>")
            return
        try:
            cmd = ["git"] + shlex.split(args)
            result = subprocess.run(
                cmd, shell=False, capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            if output:
                self.io.print_info(output)
        except Exception as exc:
            self.io.print_error(f"Git error: {exc}")

    def _cmd_paste(self, args: str) -> None:
        try:
            import pyperclip
            content = pyperclip.paste()
            if content:
                self.coder.messages.append({
                    "role": "user",
                    "content": f"Clipboard content:\n```\n{content}\n```",
                })
                self.io.print_success(f"Pasted {len(content)} characters from clipboard.")
            else:
                self.io.print_warning("Clipboard is empty.")
        except Exception as exc:
            self.io.print_error(f"Could not access clipboard: {exc}")

    def _cmd_ls(self, args: str) -> None:
        path = Path(args.strip() or ".")
        if not path.exists():
            self.io.print_warning(f"Path not found: {path}")
            return
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            lines = []
            for item in items:
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    lines.append(f"  📁 {item.name}/")
                else:
                    lines.append(f"  📄 {item.name}")
            self.io.print_info("\n".join(lines) if lines else "(empty)")
        except PermissionError:
            self.io.print_error(f"Permission denied: {path}")

    def _cmd_agent(self, args: str) -> None:
        """Run the multi-agent pipeline (or a single named agent).

        Usage:
            /agent <task description>
            /agent --agent coder <task description>
        """
        if not args:
            self.io.print_warning(
                "Usage: /agent [--agent <name>] <task description>\n"
                "Available agents: planner, coder, reviewer, tester, "
                "debugger, doc_writer, security, refactor"
            )
            return

        # Parse optional --agent flag
        agent_name: str | None = None
        task = args
        parts = args.split(maxsplit=2)
        if len(parts) >= 2 and parts[0] == "--agent":
            agent_name = parts[1]
            task = parts[2] if len(parts) > 2 else ""
            if not task:
                self.io.print_warning("Please provide a task description after --agent <name>.")
                return

        try:
            from qgo.agents.orchestrator import AgentOrchestrator

            files = {
                str(fc.path): fc.content
                for fc in self.coder.chat_files
            }
            orchestrator = AgentOrchestrator(
                llm=self.coder.llm,
                config=self.coder.config,
                io=self.io,
            )
            if agent_name:
                result = orchestrator.run_single(agent_name, task, context={"files": files})
                report = result.output if result.success else f"Agent error: {result.error}"
            else:
                report = orchestrator.run(task, files=files)

            self.io.print_assistant(report)
            # Add the report to conversation context
            self.coder.messages.append({
                "role": "assistant",
                "content": report,
            })
        except ValueError as exc:
            self.io.print_error(str(exc))
        except Exception as exc:
            self.io.print_error(f"Multi-agent pipeline error: {exc}")

    def _cmd_config(self, args: str) -> None:
        self.io.print_info(str(self.coder.config))

    def _cmd_help(self, args: str) -> None:
        self.io.print_help()

    def _cmd_exit(self, args: str) -> None:
        self.io.print_info("Goodbye! 👋")
        raise SystemExit(0)
