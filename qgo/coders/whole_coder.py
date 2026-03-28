"""Whole-file coder — LLM returns complete file contents in fenced code blocks."""

from __future__ import annotations

import re
from pathlib import Path

from qgo.coders.base_coder import BaseCoder
from qgo.models import EditBlock

# Pattern to extract fenced code blocks with an optional filename
# Supports:
#   ```python\n# path/to/file.py\n...```
#   ```python path/to/file.py\n...```
#   path/to/file.py\n```python\n...```
_FENCE_RE = re.compile(
    r"```[\w]*\s*\n(.*?)```",
    re.DOTALL,
)

_FILENAME_IN_FENCE_RE = re.compile(
    r"^#\s*(.+?\.\w+)\s*$",
    re.MULTILINE,
)

_FILENAME_BEFORE_FENCE_RE = re.compile(
    r"(?:^|\n)`?([^\s`]+\.\w+)`?\s*\n```",
)


class WholeCoder(BaseCoder):
    """Coder that replaces entire file contents.

    The LLM is asked to return the complete new content of each file
    it wants to modify, wrapped in fenced code blocks.
    """

    edit_format = "whole"

    def parse_edits(self, response: str) -> list[EditBlock]:
        """Parse whole-file blocks from the LLM response."""
        blocks: list[EditBlock] = []

        # Strategy 1: Find ```lang\n# filename\ncontent```
        for m in _FENCE_RE.finditer(response):
            content = m.group(1)
            # Look for filename comment at start of block
            fn_match = _FILENAME_IN_FENCE_RE.search(content[:200])
            if fn_match:
                filename = fn_match.group(1).strip()
                # Remove the filename comment line from content
                clean = re.sub(r"^#\s*" + re.escape(filename) + r"\s*\n", "", content, count=1)
                blocks.append(EditBlock(filename=filename, original="", updated=clean))
                continue

            # Strategy 2: Look for filename in the text just before the fence
            start = m.start()
            preceding = response[max(0, start - 200):start]
            fn_match2 = re.search(r"`?([^\s`]+\.\w+)`?\s*\n?$", preceding.strip())
            if fn_match2:
                filename = fn_match2.group(1).strip()
                blocks.append(EditBlock(filename=filename, original="", updated=content))

        return blocks

    def apply_edits(self, response: str) -> list[str]:
        """Apply whole-file edits. Returns list of modified file paths."""
        blocks = self.parse_edits(response)
        edited: list[str] = []

        for block in blocks:
            path = Path(block.filename)
            if not path.is_absolute():
                path = Path.cwd() / path

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(block.updated, encoding="utf-8")
                action = "Created" if block.is_new_file or not path.exists() else "Updated"
                self._info(f"{action}: {block.filename}")
                edited.append(str(path))

                # Update in-memory file context
                for fc in self.chat_files:
                    if fc.path.resolve() == path.resolve():
                        fc.content = block.updated

            except Exception as exc:
                self._error(f"Error writing {block.filename}: {exc}")

        return edited
