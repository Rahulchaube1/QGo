"""Tests for LLM model info and token counting."""

from __future__ import annotations

import pytest

from qgo.llm.model_info import (
    get_model_info,
    list_models,
    resolve_model,
    format_model_table,
    MODEL_INFO,
)
from qgo.utils.token_counter import count_tokens, count_messages_tokens, truncate_to_tokens


class TestModelInfo:
    def test_gpt4o_info(self):
        info = get_model_info("gpt-4o")
        assert info["context_window"] == 128_000
        assert info["supports_vision"] is True
        assert info["provider"] == "openai"

    def test_unknown_model_defaults(self):
        info = get_model_info("some-unknown-model-xyz")
        assert info["context_window"] == 128_000
        assert info["supports_vision"] is False

    def test_resolve_alias(self):
        assert resolve_model("claude") == "claude-3-7-sonnet-20250219"
        assert resolve_model("4o") == "gpt-4o"
        assert resolve_model("deepseek") == "deepseek/deepseek-chat"

    def test_resolve_no_alias(self):
        assert resolve_model("gpt-4o") == "gpt-4o"

    def test_list_models(self):
        models = list_models()
        assert len(models) > 10
        assert "gpt-4o" in models

    def test_list_models_by_provider(self):
        openai_models = list_models(provider="openai")
        assert all(MODEL_INFO[m]["provider"] == "openai" for m in openai_models)
        assert "gpt-4o" in openai_models

    def test_format_model_table(self):
        table = format_model_table()
        assert "gpt-4o" in table
        assert "openai" in table
        assert "anthropic" in table


class TestTokenCounter:
    def test_count_tokens_nonempty(self):
        # Should return a positive integer
        n = count_tokens("Hello, world!")
        assert isinstance(n, int)
        assert n > 0

    def test_count_tokens_empty(self):
        n = count_tokens("")
        assert n >= 0

    def test_count_tokens_longer_is_more(self):
        short = count_tokens("Hi")
        long = count_tokens("Hello, this is a much longer sentence with many words.")
        assert long > short

    def test_count_messages_tokens(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        total = count_messages_tokens(messages)
        assert total > 0

    def test_truncate_to_tokens(self):
        long_text = "\n".join(f"Line {i}: " + "x" * 20 for i in range(200))
        result = truncate_to_tokens(long_text, max_tokens=50)
        assert count_tokens(result) <= 60  # Allow small margin
        assert len(result) < len(long_text)

    def test_truncate_short_text_unchanged(self):
        short = "Hello world"
        result = truncate_to_tokens(short, max_tokens=1000)
        assert result == short
