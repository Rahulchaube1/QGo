"""Interactive REPL for QGo using prompt_toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qgo.coders.base_coder import BaseCoder
    from qgo.ui.terminal import QGoIO

_HISTORY_FILE = Path.home() / ".qgo_history"


def _get_completer(coder: "BaseCoder"):
    """Build a command completer for prompt_toolkit."""
    try:
        from prompt_toolkit.completion import WordCompleter

        commands = [
            "/add", "/drop", "/files", "/diff", "/commit", "/undo", "/clear",
            "/model", "/models", "/tokens", "/map", "/run", "/web", "/git",
            "/paste", "/ls", "/config", "/help", "/exit", "/quit",
        ]
        # Add current files as completions for /add and /drop
        file_names = [str(fc.path.name) for fc in coder.chat_files]
        return WordCompleter(commands + file_names, sentence=True)
    except ImportError:
        return None


def run_repl(coder: "BaseCoder", io: "QGoIO") -> None:
    """Run the interactive REPL loop.

    Handles all user input, command routing, and LLM communication.
    """
    from qgo.ui.commands import CommandHandler

    handler = CommandHandler(coder=coder, io=io)

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.styles import Style

        style = Style.from_dict({
            "prompt": "bold cyan",
        })

        kb = KeyBindings()

        @kb.add("escape", "enter")
        def _newline(event):
            """Alt+Enter inserts a newline."""
            event.current_buffer.insert_text("\n")

        session = PromptSession(
            history=FileHistory(str(_HISTORY_FILE)),
            key_bindings=kb,
            style=style,
            multiline=False,
            complete_while_typing=True,
        )

        while True:
            try:
                completer = _get_completer(coder)
                text = session.prompt(
                    "\n[QGo] > ",
                    completer=completer,
                ).strip()
            except KeyboardInterrupt:
                io.print_info("(Ctrl+C — type /exit to quit)")
                continue
            except EOFError:
                io.print_info("Goodbye! 👋")
                break

            if not text:
                continue

            # Handle /commands
            if handler.handle(text):
                continue

            # Send to LLM
            try:
                io.print_user(text)
                coder.run(text)
            except KeyboardInterrupt:
                io.print_warning("Interrupted.")
            except Exception as exc:
                io.print_error(f"Error: {exc}")

    except ImportError:
        # Fallback: plain input() loop if prompt_toolkit is not installed
        _plain_repl(coder, io, handler)


def _plain_repl(coder: "BaseCoder", io: "QGoIO", handler) -> None:
    """Simple fallback REPL using built-in input()."""
    io.print_info("(prompt_toolkit not available — using basic input mode)")
    while True:
        try:
            text = input("\n[QGo] > ").strip()
        except (KeyboardInterrupt, EOFError):
            io.print_info("Goodbye! 👋")
            break

        if not text:
            continue
        if handler.handle(text):
            continue
        try:
            io.print_user(text)
            coder.run(text)
        except KeyboardInterrupt:
            io.print_warning("Interrupted.")
        except Exception as exc:
            io.print_error(f"Error: {exc}")
