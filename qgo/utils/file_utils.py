# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""File system utilities for QGo."""

from __future__ import annotations

import difflib
from pathlib import Path

from qgo.models import _EXT_TO_LANG

# Extensions that are definitely binary / should not be read as text
_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".class", ".pyc", ".pyo",
    ".o", ".a", ".lib", ".wasm",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".flac", ".wav",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".db", ".sqlite", ".sqlite3",
}


def read_file(path: Path | str) -> str:
    """Read a text file and return its content.

    Raises FileNotFoundError if the file does not exist.
    """
    return Path(path).read_text(encoding="utf-8", errors="replace")


def write_file(path: Path | str, content: str) -> None:
    """Write *content* to *path*, creating parent directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def create_file(path: Path | str, content: str = "") -> None:
    """Create a new file with *content*. Raises FileExistsError if already present."""
    p = Path(path)
    if p.exists():
        raise FileExistsError(f"File already exists: {path}")
    write_file(p, content)


def is_text_file(path: Path | str) -> bool:
    """Return True if the file is likely a text file (not binary)."""
    p = Path(path)
    if p.suffix.lower() in _BINARY_EXTENSIONS:
        return False
    # Peek at first 8 KB for null bytes (binary indicator)
    try:
        chunk = p.read_bytes()[:8192]
        return b"\x00" not in chunk
    except (PermissionError, OSError):
        return False


def get_file_language(path: Path | str) -> str:
    """Return the programming language name for syntax highlighting."""
    return _EXT_TO_LANG.get(Path(path).suffix.lower(), "")


def get_file_extension(path: Path | str) -> str:
    """Return the lowercase file extension (e.g. '.py')."""
    return Path(path).suffix.lower()


def make_diff(original: str, updated: str, filename: str = "file") -> str:
    """Generate a unified diff between two strings."""
    original_lines = original.splitlines(keepends=True)
    updated_lines = updated.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        updated_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def find_files(
    root: Path | str,
    patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
    max_files: int = 1000,
) -> list[Path]:
    """Recursively find text files under *root*.

    Args:
        root: Directory to search.
        patterns: Glob patterns to include (e.g. ["*.py", "*.js"]).
                  If None, includes all text files.
        ignore_patterns: Glob patterns to exclude.
        max_files: Maximum files to return.
    """
    import fnmatch

    root_path = Path(root)
    files: list[Path] = []
    ignore = set(ignore_patterns or [])

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        # Check ignore patterns
        if any(fnmatch.fnmatch(str(path), p) for p in ignore):
            continue
        if any(fnmatch.fnmatch(path.name, p) for p in ignore):
            continue
        # Check include patterns
        if patterns:
            if not any(fnmatch.fnmatch(path.name, p) for p in patterns):
                continue
        else:
            if not is_text_file(path):
                continue
        files.append(path)
        if len(files) >= max_files:
            break

    return files
