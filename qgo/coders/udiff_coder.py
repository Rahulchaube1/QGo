"""Unified-diff coder — LLM returns changes as standard unified diffs."""

from __future__ import annotations

import re
from pathlib import Path

from qgo.coders.base_coder import BaseCoder
from qgo.models import EditBlock

_DIFF_BLOCK_RE = re.compile(
    r"```diff\n(.*?)```",
    re.DOTALL,
)

_UNIFIED_HEADER_RE = re.compile(
    r"^--- (?:a/)?(.+?)\s*\n\+\+\+ (?:b/)?(.+?)\s*$",
    re.MULTILINE,
)


class UDiffCoder(BaseCoder):
    """Coder that applies unified diffs produced by the LLM."""

    edit_format = "udiff"

    def parse_edits(self, response: str) -> list[EditBlock]:
        """Parse unified diff blocks from the response."""
        blocks: list[EditBlock] = []

        for m in _DIFF_BLOCK_RE.finditer(response):
            diff_text = m.group(1)
            # Find target filename
            h = _UNIFIED_HEADER_RE.search(diff_text)
            if h:
                filename = h.group(2).strip()
                blocks.append(EditBlock(
                    filename=filename,
                    original=diff_text,  # Store raw diff as "original"
                    updated="",           # Updated is derived by applying diff
                ))

        return blocks

    def apply_edits(self, response: str) -> list[str]:
        """Apply unified diffs to files. Returns list of modified paths."""
        blocks = self.parse_edits(response)
        edited: list[str] = []

        for block in blocks:
            path = Path(block.filename)
            if not path.is_absolute():
                path = Path.cwd() / path

            try:
                original = ""
                if path.exists():
                    original = path.read_text(encoding="utf-8")

                new_content = self._apply_diff(original, block.original)
                if new_content is None:
                    self._warn(f"Failed to apply diff to {block.filename}")
                    continue

                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new_content, encoding="utf-8")
                self._info(f"Edited (udiff): {block.filename}")
                edited.append(str(path))

                for fc in self.chat_files:
                    if fc.path.resolve() == path.resolve():
                        fc.content = new_content

            except Exception as exc:
                self._error(f"Error applying diff to {block.filename}: {exc}")

        return edited

    @staticmethod
    def _apply_diff(original: str, diff: str) -> str | None:
        """Apply a unified diff to *original* text."""
        lines = original.splitlines(keepends=True)
        diff_lines = diff.splitlines()

        result: list[str] = list(lines)
        offset = 0  # Tracks line offset from insertions/deletions

        hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        i = 0
        while i < len(diff_lines):
            m = hunk_re.match(diff_lines[i])
            if m:
                orig_start = int(m.group(1)) - 1  # 0-indexed
                i += 1

                hunk_removes: list[str] = []
                hunk_adds: list[str] = []

                while i < len(diff_lines) and not diff_lines[i].startswith("@@"):
                    line = diff_lines[i]
                    if line.startswith("-"):
                        hunk_removes.append(line[1:])
                    elif line.startswith("+"):
                        hunk_adds.append(line[1:])
                    elif line.startswith(" "):
                        hunk_removes.append(line[1:])
                        hunk_adds.append(line[1:])
                    i += 1

                # Apply hunk
                actual_start = orig_start + offset
                # Verify remove block matches
                end = actual_start + len(hunk_removes)
                if end <= len(result):
                    result[actual_start:end] = [
                        line + ("\n" if not line.endswith("\n") else "")
                        for line in hunk_adds
                    ]
                    offset += len(hunk_adds) - len(hunk_removes)
            else:
                i += 1

        return "".join(result)
