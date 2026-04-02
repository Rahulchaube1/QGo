# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Universal LLM provider using litellm — supports 100+ models."""

from __future__ import annotations

import os
import time
from typing import Iterator, Union

from qgo.llm.base import BaseLLM
from qgo.llm.model_info import get_model_info, resolve_model
from qgo.llm.streaming import extract_text, iter_chunks


class LiteLLMProvider(BaseLLM):
    """Universal LLM backend via litellm.

    Supports OpenAI, Anthropic, DeepSeek, Gemini, Groq, Cohere,
    Mistral, Ollama, Azure OpenAI, AWS Bedrock, and any other provider
    supported by litellm.

    Examples::

        # OpenAI
        llm = LiteLLMProvider("gpt-4o", api_key="sk-...")

        # Anthropic Claude
        llm = LiteLLMProvider("claude-3-7-sonnet-20250219")

        # Local Ollama
        llm = LiteLLMProvider("ollama/llama3.2", api_base="http://localhost:11434")

        # DeepSeek
        llm = LiteLLMProvider("deepseek/deepseek-chat", api_key="...")
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        timeout: int = 120,
        max_retries: int = 3,
        **kwargs,
    ) -> None:
        self._model = resolve_model(model)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._api_base = api_base
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._max_retries = max_retries
        self._extra_kwargs = kwargs

        # Auto-detect API key from environment for known providers
        info = get_model_info(self._model)
        provider = info.get("provider", "")
        if not self._api_key:
            self._api_key = self._detect_api_key(provider)

    # ─── BaseLLM interface ────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model

    def complete(
        self,
        messages: list[dict],
        stream: bool = True,
        **kwargs,
    ) -> Union[str, Iterator[str]]:
        """Send messages to the LLM.

        Returns an iterator of text chunks if stream=True,
        or a complete string if stream=False.
        """
        params = self._build_params(stream=stream, **kwargs)
        params["messages"] = messages

        response = self._call_with_retry(params)

        if stream:
            return iter_chunks(response)
        else:
            return extract_text(response)

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken when available, else estimate."""
        try:
            import tiktoken
            # Map model to tiktoken encoding
            enc_model = self._model
            if "claude" in enc_model or "deepseek" in enc_model or "gemini" in enc_model:
                enc_model = "gpt-4o"  # Approximate with gpt-4o encoding
            try:
                enc = tiktoken.encoding_for_model(enc_model)
            except KeyError:
                enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            # Rough estimate: ~4 chars per token
            return len(text) // 4

    # ─── Private helpers ──────────────────────────────────────────────

    def _build_params(self, stream: bool = True, **kwargs) -> dict:
        """Build the litellm.completion() parameter dict."""
        params: dict = {
            "model": self._model,
            "stream": stream,
            "temperature": self._temperature,
            "timeout": self._timeout,
            **self._extra_kwargs,
            **kwargs,
        }
        if self._api_key:
            params["api_key"] = self._api_key
        if self._api_base:
            params["api_base"] = self._api_base
        if self._max_tokens:
            params["max_tokens"] = self._max_tokens
        return params

    def _call_with_retry(self, params: dict):
        """Call litellm.completion with exponential back-off retry."""
        try:
            import litellm
            # Suppress verbose litellm logging
            litellm.suppress_debug_info = True
            litellm.set_verbose = False
        except ImportError as exc:
            raise ImportError(
                "litellm is required. Install it with: pip install litellm"
            ) from exc

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return litellm.completion(**params)
            except litellm.exceptions.RateLimitError as e:
                wait = 2 ** attempt
                time.sleep(wait)
                last_error = e
            except litellm.exceptions.APIConnectionError as e:
                wait = 2 ** attempt
                time.sleep(wait)
                last_error = e
            except litellm.exceptions.Timeout as e:
                wait = 2 ** attempt
                time.sleep(wait)
                last_error = e
            except Exception as e:
                raise e

        raise RuntimeError(
            f"LLM call failed after {self._max_retries} retries: {last_error}"
        ) from last_error

    @staticmethod
    def _detect_api_key(provider: str) -> str | None:
        """Auto-detect API key from environment for common providers."""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "google": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "cohere": "COHERE_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "ollama": None,  # No API key needed
        }
        env_var = env_vars.get(provider)
        if env_var:
            return os.environ.get(env_var)
        return None

    def __repr__(self) -> str:
        return f"LiteLLMProvider(model={self._model!r})"
