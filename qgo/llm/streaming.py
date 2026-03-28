# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Streaming response utilities for QGo."""

from __future__ import annotations

from typing import Iterator


class StreamingHandler:
    """Helpers for consuming streaming LLM responses."""

    @staticmethod
    def collect(iterator: Iterator[str]) -> str:
        """Consume a streaming iterator and return the full text."""
        return "".join(iterator)

    @staticmethod
    def print_stream(
        iterator: Iterator[str],
        console=None,
        prefix: str = "",
    ) -> str:
        """Stream text to the terminal, returning the full accumulated text.

        Args:
            iterator: Iterator yielding string chunks from the LLM.
            console: Rich Console instance; if None, prints to stdout.
            prefix: Optional prefix printed before streaming starts.

        Returns:
            The complete response text.
        """
        chunks: list[str] = []

        if console is not None:
            try:
                from rich.live import Live
                from rich.text import Text

                buffer = ""
                if prefix:
                    console.print(prefix, end="")

                with Live(console=console, refresh_per_second=15, transient=False) as live:
                    for chunk in iterator:
                        chunks.append(chunk)
                        buffer += chunk
                        live.update(Text(buffer))

                # Final newline
                console.print()
            except Exception:
                # Fallback to plain print if Rich fails
                for chunk in iterator:
                    chunks.append(chunk)
                    print(chunk, end="", flush=True)
                print()
        else:
            for chunk in iterator:
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            print()

        return "".join(chunks)

    @staticmethod
    def format_cost(
        prompt_tokens: int,
        completion_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
    ) -> str:
        """Return a human-readable cost string."""
        cost = (prompt_tokens / 1000 * cost_per_1k_input +
                completion_tokens / 1000 * cost_per_1k_output)
        total = prompt_tokens + completion_tokens
        return (
            f"Tokens: {total:,} "
            f"({prompt_tokens:,} in + {completion_tokens:,} out) | "
            f"Cost: ${cost:.4f}"
        )


def iter_chunks(response) -> Iterator[str]:
    """Extract text chunks from a litellm streaming response."""
    for chunk in response:
        try:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                yield delta.content
        except (AttributeError, IndexError):
            continue


def extract_text(response) -> str:
    """Extract full text from a non-streaming litellm response."""
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return str(response)
