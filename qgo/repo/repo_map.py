# Copyright (c) 2024 Rahul Chaube. All Rights Reserved.
#
# QGo — AI Coding Assistant
# Author: Rahul Chaube
# License: Apache-2.0

"""Repository mapper — builds a structured map of the codebase for LLM context.

Uses regex-based symbol extraction (no external tree-sitter dependency)
to identify classes, functions, and methods across 20+ languages.
Applies a simple relevance ranking to prioritise the most relevant symbols.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pathspec

# ─── Symbol extraction patterns per language ──────────────────────────────

_PATTERNS: dict[str, list[tuple[str, str]]] = {
    # (type_label, regex_pattern)
    ".py": [
        ("class", r"^class\s+(\w+)"),
        ("def", r"^(?:    |\t)?def\s+(\w+)"),
        ("async def", r"^(?:    |\t)?async\s+def\s+(\w+)"),
    ],
    ".js": [
        ("class", r"^class\s+(\w+)"),
        ("function", r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
        ("const", r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\("),
        ("arrow", r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
    ],
    ".ts": [
        ("class", r"^(?:export\s+)?class\s+(\w+)"),
        ("interface", r"^(?:export\s+)?interface\s+(\w+)"),
        ("type", r"^(?:export\s+)?type\s+(\w+)\s*="),
        ("function", r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
        ("const", r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\("),
        ("enum", r"^(?:export\s+)?enum\s+(\w+)"),
    ],
    ".go": [
        ("func", r"^func\s+(?:\([^)]+\)\s+)?(\w+)"),
        ("type", r"^type\s+(\w+)\s+(?:struct|interface)"),
    ],
    ".rs": [
        ("fn", r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)"),
        ("struct", r"^(?:pub\s+)?struct\s+(\w+)"),
        ("enum", r"^(?:pub\s+)?enum\s+(\w+)"),
        ("trait", r"^(?:pub\s+)?trait\s+(\w+)"),
        ("impl", r"^impl(?:<[^>]*>)?\s+(\w+)"),
    ],
    ".java": [
        ("class", r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)"),
        ("interface", r"^(?:public\s+)?interface\s+(\w+)"),
        ("method", r"^\s+(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)+(\w+)\s*\("),
    ],
    ".cpp": [
        ("class", r"^class\s+(\w+)"),
        ("struct", r"^struct\s+(\w+)"),
        ("function", r"^(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{"),
    ],
    ".c": [
        ("function", r"^(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{"),
        ("struct", r"^(?:typedef\s+)?struct\s+(\w+)"),
    ],
    ".rb": [
        ("class", r"^class\s+(\w+)"),
        ("module", r"^module\s+(\w+)"),
        ("def", r"^\s+def\s+(\w+)"),
    ],
    ".php": [
        ("class", r"^class\s+(\w+)"),
        ("function", r"^(?:public|private|protected)?\s*function\s+(\w+)"),
    ],
    ".swift": [
        ("class", r"^(?:public\s+)?class\s+(\w+)"),
        ("struct", r"^(?:public\s+)?struct\s+(\w+)"),
        ("func", r"^\s+(?:public\s+)?func\s+(\w+)"),
        ("protocol", r"^protocol\s+(\w+)"),
    ],
    ".kt": [
        ("class", r"^(?:data\s+)?class\s+(\w+)"),
        ("fun", r"^(?:    )?fun\s+(\w+)"),
        ("object", r"^object\s+(\w+)"),
    ],
    ".cs": [
        ("class", r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?class\s+(\w+)"),
        ("interface", r"^(?:public\s+)?interface\s+(\w+)"),
        ("method", r"^\s+(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)+(\w+)\s*\("),
    ],
}

# Extend .tsx and .jsx to use .ts and .js patterns
_PATTERNS[".tsx"] = _PATTERNS[".ts"]
_PATTERNS[".jsx"] = _PATTERNS[".js"]

# Files to ignore when mapping
_IGNORE_PATTERNS = [
    ".git/**", "node_modules/**", "__pycache__/**", ".venv/**", "venv/**",
    "*.pyc", "*.pyo", "*.class", "*.o", "*.so", "*.dll", "*.exe",
    "dist/**", "build/**", "*.egg-info/**", ".pytest_cache/**",
    "*.min.js", "*.min.css", "*.map", "*.lock", "package-lock.json",
    "yarn.lock", "Cargo.lock", "go.sum",
]

_TEXT_EXTENSIONS = set(_PATTERNS.keys()) | {
    ".md", ".txt", ".rst", ".yaml", ".yml", ".toml", ".json",
    ".html", ".css", ".scss", ".sql", ".sh", ".bash",
}


class RepoMap:
    """Build and maintain a map of the repository for LLM context.

    The map shows the structure of the codebase — files, classes, functions —
    helping the LLM understand which files are relevant to the current task.
    """

    def __init__(
        self,
        root: str | Path = ".",
        max_map_tokens: int = 2048,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_map_tokens = max_map_tokens
        self._ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", _IGNORE_PATTERNS)
        self._gitignore_spec: Optional[pathspec.PathSpec] = self._load_gitignore()

    # ─── Public API ───────────────────────────────────────────────────

    def get_repo_map(
        self,
        chat_files: list[str | Path] | None = None,
        other_files: list[str | Path] | None = None,
    ) -> str:
        """Return a formatted repository map string for inclusion in the prompt.

        Args:
            chat_files: Files currently in the conversation context.
            other_files: Additional files to scan (defaults to all repo files).
        """
        chat_paths = {Path(f).resolve() for f in (chat_files or [])}

        if other_files is None:
            all_files = self.get_all_files()
        else:
            all_files = [Path(f).resolve() for f in other_files]

        # Files NOT already in chat context
        map_files = [f for f in all_files if f not in chat_paths]

        if not map_files:
            return ""

        tags = self._extract_tags(map_files)
        ranked = self._rank_tags(tags, chat_files or [])
        return self._render_map(ranked)

    def get_all_files(self) -> list[Path]:
        """Return all non-ignored files under the repo root."""
        files: list[Path] = []
        try:
            for path in self.root.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(self.root)
                rel_str = str(rel)
                if self._ignore_spec.match_file(rel_str):
                    continue
                if self._gitignore_spec and self._gitignore_spec.match_file(rel_str):
                    continue
                if path.suffix.lower() in _TEXT_EXTENSIONS:
                    files.append(path)
        except PermissionError:
            pass
        return files

    def get_file_symbols(self, path: Path) -> list[dict]:
        """Extract all symbols (classes, functions, etc.) from a file."""
        return self._extract_file_tags(path)

    # ─── Private helpers ──────────────────────────────────────────────

    def _extract_tags(self, files: list[Path]) -> list[dict]:
        """Extract symbol tags from a list of files."""
        all_tags: list[dict] = []
        for path in files:
            all_tags.extend(self._extract_file_tags(path))
        return all_tags

    def _extract_file_tags(self, path: Path) -> list[dict]:
        """Extract symbol definitions from a single file."""
        tags: list[dict] = []
        ext = path.suffix.lower()
        patterns = _PATTERNS.get(ext, [])
        if not patterns:
            return tags

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except (PermissionError, OSError):
            return tags

        for lineno, line in enumerate(content.splitlines(), start=1):
            for tag_type, pattern in patterns:
                m = re.match(pattern, line)
                if m:
                    name = m.group(1)
                    if name and not name.startswith("_"):
                        tags.append({
                            "file": path,
                            "line": lineno,
                            "type": tag_type,
                            "name": name,
                        })
                    break  # Only one match per line
        return tags

    def _rank_tags(
        self,
        tags: list[dict],
        chat_files: list[str | Path],
    ) -> list[dict]:
        """Sort tags by relevance to the current chat context.

        Files that are closer to (or referenced by) chat_files
        are ranked higher.
        """
        chat_names = {Path(f).stem.lower() for f in chat_files}
        chat_paths = {Path(f).resolve() for f in chat_files}

        def score(tag: dict) -> tuple:
            file_path: Path = tag["file"]
            is_chat = file_path in chat_paths
            name_match = tag["name"].lower() in chat_names or file_path.stem.lower() in chat_names
            # Prefer classes and top-level functions over methods
            type_weight = {"class": 3, "interface": 3, "struct": 2,
                           "def": 1, "func": 1, "function": 1}.get(tag["type"], 0)
            return (not is_chat, not name_match, -type_weight, str(file_path))

        return sorted(tags, key=score)

    def _render_map(self, tags: list[dict]) -> str:
        """Render tags into a readable map string."""
        if not tags:
            return ""

        # Group tags by file
        by_file: dict[Path, list[dict]] = {}
        for tag in tags:
            by_file.setdefault(tag["file"], []).append(tag)

        lines: list[str] = ["```\nRepo map:"]
        total_chars = 0
        max_chars = self.max_map_tokens * 3  # rough char estimate

        for path, file_tags in by_file.items():
            try:
                rel = path.relative_to(self.root)
            except ValueError:
                rel = path
            file_line = str(rel)
            lines.append(file_line)
            for tag in file_tags:
                indent = "  "
                symbol_line = f"{indent}{tag['type']} {tag['name']}:"
                lines.append(symbol_line)
            total_chars += sum(len(line) for line in lines[-len(file_tags)-1:])
            if total_chars > max_chars:
                lines.append("  ... (truncated)")
                break

        lines.append("```")
        return "\n".join(lines)

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """Load .gitignore from the root directory."""
        gitignore = self.root / ".gitignore"
        if gitignore.exists():
            try:
                patterns = gitignore.read_text().splitlines()
                return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            except Exception:
                pass
        return None
