"""Data models and type definitions for QGo."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Role(str, Enum):
    """LLM message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class EditFormat(str, Enum):
    """Available code editing formats."""

    EDITBLOCK = "editblock"   # SEARCH/REPLACE blocks (default, most reliable)
    WHOLE = "whole"           # Full file replacement
    UDIFF = "udiff"           # Unified diff format
    ARCHITECT = "architect"   # Two-pass plan + implement


@dataclass
class Message:
    """A single LLM conversation message."""

    role: str
    content: str
    images: list[str] = field(default_factory=list)  # base64 or URLs
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to litellm/OpenAI API format."""
        if self.images:
            content: list = [{"type": "text", "text": self.content}]
            for img in self.images:
                if img.startswith("data:") or img.startswith("http"):
                    content.append({"type": "image_url", "image_url": {"url": img}})
            return {"role": self.role, "content": content}
        return {"role": self.role, "content": self.content}


@dataclass
class EditBlock:
    """Represents a single code edit operation."""

    filename: str
    original: str   # Text to search for (empty = create new file)
    updated: str    # Replacement text
    is_new_file: bool = False

    def __post_init__(self) -> None:
        if not self.original.strip():
            self.is_new_file = True


@dataclass
class FileContext:
    """A file loaded into the AI context."""

    path: Path
    content: str
    tokens: int = 0
    language: str = ""
    read_only: bool = False

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if not self.language:
            self.language = _detect_language(self.path)

    def to_prompt_str(self) -> str:
        """Format file for inclusion in a prompt."""
        fence = "```"
        return f"{fence}{self.language}\n{self.path}\n{self.content}\n{fence}"


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
        )


@dataclass
class ChatSession:
    """A full chat session state."""

    model: str
    messages: list[Message] = field(default_factory=list)
    files: list[FileContext] = field(default_factory=list)
    edit_format: EditFormat = EditFormat.EDITBLOCK
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str, images: Optional[list[str]] = None) -> None:
        self.messages.append(Message(role=role, content=content, images=images or []))

    def clear_history(self) -> None:
        self.messages.clear()

    def get_file(self, path: str) -> Optional[FileContext]:
        p = Path(path)
        for f in self.files:
            if f.path == p or f.path.name == p.name:
                return f
        return None


# Language detection helper
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".ps1": "powershell",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "rst",
    ".sql": "sql",
    ".lua": "lua",
    ".vim": "vim",
    ".dockerfile": "dockerfile",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".dart": "dart",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}


def _detect_language(path: Path) -> str:
    """Detect the programming language from a file path."""
    name = path.name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    return _EXT_TO_LANG.get(path.suffix.lower(), "")
