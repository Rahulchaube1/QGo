"""EditBlock coder — uses SEARCH/REPLACE blocks (default, most reliable format)."""

from __future__ import annotations

import re
from pathlib import Path

from qgo.coders.base_coder import BaseCoder
from qgo.models import EditBlock

# Markers
_SEARCH_MARKER = "<<<<<<< SEARCH"
_DIVIDER_MARKER = "======="
_REPLACE_MARKER = ">>>>>>> REPLACE"

# Regex to find filename above an edit block
_FILENAME_RE = re.compile(
    r"^(?:#+\s+)?(?:File:\s*)?`?([^\s`]+\.\w+)`?\s*$",
    re.MULTILINE,
)


class EditBlockCoder(BaseCoder):
    """Coder that uses SEARCH/REPLACE block format.

    The LLM returns edits like::

        path/to/file.py
        <<<<<<< SEARCH
        def old_function():
            pass
        =======
        def new_function():
            return 42
        >>>>>>> REPLACE

    Multiple blocks can be present in a single response.
    Empty SEARCH blocks create new files.
    """

    edit_format = "editblock"

    def parse_edits(self, response: str) -> list[EditBlock]:
        """Parse all SEARCH/REPLACE blocks from the LLM response."""
        blocks: list[EditBlock] = []
        lines = response.splitlines(keepends=True)
        i = 0
        current_file: str | None = None

        while i < len(lines):
            line = lines[i]

            # Track which file we're editing (line before the SEARCH marker)
            if _SEARCH_MARKER in line:
                # Find original text (between SEARCH and =======)
                original_lines: list[str] = []
                i += 1
                while i < len(lines) and _DIVIDER_MARKER not in lines[i]:
                    original_lines.append(lines[i])
                    i += 1

                # Find replacement text (between ======= and REPLACE)
                updated_lines: list[str] = []
                i += 1  # skip =======
                while i < len(lines) and _REPLACE_MARKER not in lines[i]:
                    updated_lines.append(lines[i])
                    i += 1

                original = "".join(original_lines)
                updated = "".join(updated_lines)

                if current_file:
                    blocks.append(EditBlock(
                        filename=current_file,
                        original=original,
                        updated=updated,
                    ))
            else:
                # Check if this line is a filename
                stripped = line.strip().rstrip(":")
                # Look for bare filename pattern or markdown heading with filename
                maybe_file = _try_extract_filename(stripped)
                if maybe_file:
                    current_file = maybe_file
                i += 1

        return blocks

    def apply_edits(self, response: str) -> list[str]:
        """Apply all edits from a response. Returns list of modified file paths."""
        blocks = self.parse_edits(response)
        edited: list[str] = []

        for block in blocks:
            path = Path(block.filename)
            if not path.is_absolute():
                # Try relative to current working directory
                path = Path.cwd() / path

            try:
                if block.is_new_file:
                    # Create new file
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(block.updated, encoding="utf-8")
                    self._info(f"Created: {block.filename}")
                    edited.append(str(path))
                else:
                    if not path.exists():
                        self._warn(f"File not found for editing: {block.filename}")
                        continue

                    current = path.read_text(encoding="utf-8")
                    new_content = self._do_replace(current, block.original, block.updated)

                    if new_content is None:
                        # Try fuzzy matching
                        new_content = self._fuzzy_replace(current, block.original, block.updated)

                    if new_content is None:
                        self._warn(
                            f"Could not find SEARCH block in {block.filename}.\n"
                            f"Looking for:\n{block.original[:200]!r}"
                        )
                        continue

                    path.write_text(new_content, encoding="utf-8")
                    self._info(f"Edited: {block.filename}")
                    edited.append(str(path))

                    # Update in-memory file context
                    for fc in self.chat_files:
                        if fc.path.resolve() == path.resolve():
                            fc.content = new_content

            except Exception as exc:
                self._error(f"Error applying edit to {block.filename}: {exc}")

        return edited

    # ─── Matching helpers ─────────────────────────────────────────────

    @staticmethod
    def _do_replace(content: str, original: str, updated: str) -> str | None:
        """Exact string replacement. Returns None if not found."""
        if original not in content:
            return None
        return content.replace(original, updated, 1)

    @staticmethod
    def _fuzzy_replace(content: str, original: str, updated: str) -> str | None:
        """Try normalised-whitespace matching as a fallback."""
        def normalise(s: str) -> str:
            return re.sub(r"[ \t]+", " ", s.strip())

        norm_orig = normalise(original)
        norm_content = normalise(content)

        if norm_orig not in norm_content:
            # Try line-by-line fuzzy
            orig_lines = original.splitlines()
            content_lines = content.splitlines()
            # Find the block by matching stripped lines
            for start in range(len(content_lines)):
                if len(content_lines) - start < len(orig_lines):
                    break
                if all(
                    content_lines[start + j].strip() == orig_lines[j].strip()
                    for j in range(len(orig_lines))
                ):
                    # Found the block; replace it
                    end = start + len(orig_lines)
                    new_lines = (
                        content_lines[:start]
                        + updated.splitlines()
                        + content_lines[end:]
                    )
                    return "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")
            return None

        # Simple normalised replace
        return content.replace(original.strip(), updated, 1)


def _try_extract_filename(text: str) -> str | None:
    """Check if *text* looks like a file path."""
    if not text:
        return None
    # Must have a file extension and no spaces (unless quoted)
    text = text.strip("`'\"")
    if " " in text and not (text.startswith('"') or text.startswith("'")):
        return None
    # Must contain a dot (for extension) and match path pattern
    if "." in text:
        if re.match(r'^[\w./\\-]+\.\w{1,10}$', text):
            return text
    return None
