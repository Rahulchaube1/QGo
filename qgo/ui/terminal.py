# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Rich-based terminal I/O for QGo — beautiful, readable output."""

from __future__ import annotations

from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

# Custom colour theme
_THEME = Theme({
    "qgo.user": "bold cyan",
    "qgo.assistant": "bold green",
    "qgo.info": "dim white",
    "qgo.warning": "bold yellow",
    "qgo.error": "bold red",
    "qgo.success": "bold green",
    "qgo.commit": "bold magenta",
    "qgo.filename": "bold blue",
    "qgo.prompt": "bold white",
})

_BANNER = """\
 ██████╗  ██████╗  ██████╗
██╔═══██╗██╔════╝ ██╔═══██╗
██║   ██║██║  ███╗██║   ██║
██║▄▄ ██║██║   ██║██║   ██║
╚██████╔╝╚██████╔╝╚██████╔╝
 ╚══▀▀═╝  ╚═════╝  ╚═════╝
"""


class QGoIO:
    """All terminal input/output for QGo.

    Wraps Rich for beautiful formatted output including Markdown rendering,
    syntax-highlighted code, coloured diffs, and live streaming responses.
    """

    def __init__(self, fancy: bool = True, width: int | None = None) -> None:
        self.fancy = fancy
        self.console = Console(theme=_THEME, width=width, highlight=False)
        self.err_console = Console(theme=_THEME, stderr=True, width=width, highlight=False)

    # ─── Banner ───────────────────────────────────────────────────────

    def print_banner(self, model: str = "", version: str = "0.1.0") -> None:
        """Print the QGo startup banner."""
        from rich.align import Align

        banner_text = Text(_BANNER, style="bold cyan")
        subtitle = Text(f"v{version}", style="dim white")
        if model:
            subtitle.append(f"  ·  model: {model}", style="bold white")
        subtitle.append("  ·  type /help for commands", style="dim white")

        self.console.print()
        self.console.print(Align.center(banner_text))
        self.console.print(Align.center(subtitle))
        self.console.print()

    # ─── Message printing ─────────────────────────────────────────────

    def print_user(self, text: str) -> None:
        """Print the user's message."""
        self.console.print(f"[qgo.user]You:[/] {text}")

    def print_assistant(self, text: str) -> None:
        """Print a complete assistant response with Markdown rendering."""
        self.console.print()
        if self.fancy:
            try:
                md = Markdown(text)
                self.console.print(
                    Panel(md, title="[qgo.assistant]QGo[/]", border_style="green", padding=(0, 1))
                )
            except Exception:
                self.console.print(f"[qgo.assistant]QGo:[/] {text}")
        else:
            self.console.print(f"[qgo.assistant]QGo:[/] {text}")
        self.console.print()

    def stream_response(self, iterator: Iterator[str]) -> str:
        """Live-stream the assistant's response to the terminal.

        Returns the complete response text.
        """
        self.console.print()
        chunks: list[str] = []
        buffer = ""

        try:
            with Live(
                Text(""),
                console=self.console,
                refresh_per_second=15,
                vertical_overflow="visible",
            ) as live:
                for chunk in iterator:
                    chunks.append(chunk)
                    buffer += chunk
                    # Show as markdown in real time
                    try:
                        live.update(Markdown(buffer))
                    except Exception:
                        live.update(Text(buffer))
        except Exception:
            # Fallback: plain streaming
            for chunk in iterator:
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            print()

        self.console.print()
        return "".join(chunks)

    # ─── Status messages ──────────────────────────────────────────────

    def print_info(self, text: str) -> None:
        self.console.print(f"[qgo.info]{text}[/]")

    def print_warning(self, text: str) -> None:
        self.console.print(f"[qgo.warning]⚠  {text}[/]")

    def print_error(self, text: str) -> None:
        self.err_console.print(f"[qgo.error]✗  {text}[/]")

    def print_success(self, text: str) -> None:
        self.console.print(f"[qgo.success]✓  {text}[/]")

    def print_commit(self, commit_hash: str, message: str) -> None:
        self.console.print(
            f"[qgo.commit]📦 Committed:[/] [bold]{commit_hash[:8]}[/] {message}"
        )

    # ─── File listings ────────────────────────────────────────────────

    def print_files(self, files: list, title: str = "Files in context") -> None:
        """Print the list of files currently in context."""
        if not files:
            self.console.print("[qgo.info]No files in context.[/]")
            return
        lines = Text()
        for fc in files:
            ro = " (read-only)" if getattr(fc, "read_only", False) else ""
            tokens = getattr(fc, "tokens", 0)
            path = getattr(fc, "path", fc)
            lines.append(f"  {path}{ro}", style="qgo.filename")
            lines.append(f"  ({tokens:,} tokens)\n", style="dim white")
        self.console.print(Panel(lines, title=title, border_style="blue"))

    # ─── Code / diff display ──────────────────────────────────────────

    def print_code(self, code: str, language: str = "python", filename: str = "") -> None:
        """Print syntax-highlighted code."""
        title = filename or language
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title=title, border_style="blue"))

    def print_diff(self, diff: str) -> None:
        """Print a coloured unified diff."""
        syntax = Syntax(diff, "diff", theme="monokai")
        self.console.print(Panel(syntax, title="Diff", border_style="yellow"))

    def print_repo_map(self, map_text: str) -> None:
        """Print the repository map."""
        if not map_text:
            self.console.print("[qgo.info]No repo map available.[/]")
            return
        syntax = Syntax(map_text.strip("`").strip(), "text", theme="monokai")
        self.console.print(Panel(syntax, title="Repository Map", border_style="cyan"))

    # ─── Tables ───────────────────────────────────────────────────────

    def print_models_table(self, table_text: str) -> None:
        """Print model information."""
        self.console.print(
            Panel(table_text, title="Available Models", border_style="cyan")
        )

    def print_history(self, history: list[dict]) -> None:
        """Print git commit history."""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("Hash", style="magenta", width=8)
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Author", style="green", width=15)
        table.add_column("Message")
        for entry in history:
            table.add_row(
                entry.get("short_hash", ""),
                entry.get("date", ""),
                entry.get("author", ""),
                entry.get("subject", ""),
            )
        self.console.print(table)

    def print_token_usage(self, prompt: int, completion: int, cost: float) -> None:
        """Print token usage statistics."""
        total = prompt + completion
        self.console.print(
            f"[qgo.info]Tokens:[/] {total:,} "
            f"({prompt:,} in + {completion:,} out) | "
            f"[qgo.info]Cost:[/] ${cost:.4f}"
        )

    def print_help(self) -> None:
        """Print the help text."""
        help_md = """\
## QGo Commands

| Command | Description |
|---------|-------------|
| `/add <files>` | Add files to context |
| `/drop <files>` | Remove files from context |
| `/files` | List files in context |
| `/diff` | Show last git diff |
| `/commit [msg]` | Commit changes |
| `/undo` | Undo last commit |
| `/clear` | Clear chat history |
| `/model <name>` | Switch LLM model |
| `/models` | List available models |
| `/tokens` | Show token usage |
| `/map` | Show repository map |
| `/run <cmd>` | Run shell command |
| `/web <url>` | Fetch URL as context |
| `/git <cmd>` | Run git command |
| `/paste` | Paste clipboard content |
| `/ls [path]` | List directory files |
| `/config` | Show current config |
| `/help` | Show this help |
| `/exit` or `/quit` | Exit QGo |

**Tips:**
- Press **Enter** to send, **Alt+Enter** for newline in message
- Press **Ctrl+C** to cancel current input
- Press **Ctrl+D** to exit
- Use `/add *.py` to add multiple files with glob patterns
"""
        self.console.print(Markdown(help_md))
