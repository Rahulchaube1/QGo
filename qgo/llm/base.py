"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator, Union


class BaseLLM(ABC):
    """Abstract interface for all LLM providers used by QGo."""

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        stream: bool = True,
        **kwargs,
    ) -> Union[str, Iterator[str]]:
        """Send messages to the LLM and return the response.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            stream: If True, return an iterator of text chunks.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Full response string if stream=False,
            or an iterator of string chunks if stream=True.
        """
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate token count for the given text."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier string."""
        ...

    @property
    def context_window(self) -> int:
        """Maximum input tokens this model supports."""
        from qgo.llm.model_info import get_model_info
        info = get_model_info(self.model_name)
        return info.get("context_window", 128_000)

    @property
    def max_output_tokens(self) -> int:
        """Maximum output tokens this model supports."""
        from qgo.llm.model_info import get_model_info
        info = get_model_info(self.model_name)
        return info.get("max_output", 4096)

    @property
    def supports_vision(self) -> bool:
        """Whether this model accepts image inputs."""
        from qgo.llm.model_info import get_model_info
        info = get_model_info(self.model_name)
        return info.get("supports_vision", False)

    @property
    def provider(self) -> str:
        """The provider name (openai, anthropic, etc.)."""
        from qgo.llm.model_info import get_model_info
        info = get_model_info(self.model_name)
        return info.get("provider", "unknown")
