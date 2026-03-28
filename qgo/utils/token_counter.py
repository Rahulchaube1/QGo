# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Token counting utilities for QGo."""

from __future__ import annotations


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in *text* for the given *model*.

    Uses tiktoken when available; falls back to a character-based estimate.
    """
    try:
        import tiktoken

        enc_model = _normalise_model(model)
        try:
            enc = tiktoken.encoding_for_model(enc_model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except ImportError:
        # tiktoken not installed — rough estimate: ~4 characters per token
        return max(1, len(text) // 4)
    except Exception:
        # Network error downloading encoding files, or other runtime error
        return max(1, len(text) // 4)


def count_messages_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """Estimate total tokens for a list of message dicts."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content, model)
        elif isinstance(content, list):
            # Vision message format
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += count_tokens(part.get("text", ""), model)
        # Add per-message overhead (~4 tokens)
        total += 4
    return total


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-4o") -> str:
    """Truncate *text* to at most *max_tokens* tokens.

    Truncates at a line boundary to avoid cutting mid-line.
    """
    if count_tokens(text, model) <= max_tokens:
        return text

    lines = text.splitlines(keepends=True)
    result: list[str] = []
    total = 0

    for line in lines:
        line_tokens = count_tokens(line, model)
        if total + line_tokens > max_tokens:
            break
        result.append(line)
        total += line_tokens

    return "".join(result)


def _normalise_model(model: str) -> str:
    """Map model names to tiktoken-compatible names."""
    if "claude" in model or "deepseek" in model or "gemini" in model:
        return "gpt-4o"
    if "gpt-4" in model or "o1" in model or "o3" in model:
        return "gpt-4o"
    if "gpt-3.5" in model:
        return "gpt-3.5-turbo"
    return model
