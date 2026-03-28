"""Tests for EditBlockCoder — SEARCH/REPLACE editing engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from qgo.coders.editblock_coder import EditBlockCoder, _try_extract_filename
from qgo.models import EditBlock


# ─── Helper ───────────────────────────────────────────────────────────────

def make_coder(tmp_path):
    """Create an EditBlockCoder with a stub LLM."""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.count_tokens.return_value = 10
    llm.model_name = "gpt-4o"
    coder = EditBlockCoder(llm=llm)
    return coder


# ─── parse_edits tests ────────────────────────────────────────────────────

class TestParseEdits:
    def test_single_block(self):
        response = """\
main.py
<<<<<<< SEARCH
def foo():
    pass
=======
def foo():
    return 42
>>>>>>> REPLACE
"""
        coder = EditBlockCoder.__new__(EditBlockCoder)
        coder.chat_files = []
        blocks = coder.parse_edits(response)
        assert len(blocks) == 1
        assert blocks[0].filename == "main.py"
        assert "pass" in blocks[0].original
        assert "return 42" in blocks[0].updated

    def test_multiple_blocks(self):
        response = """\
utils.py
<<<<<<< SEARCH
def add(a, b):
    return a + b
=======
def add(a: int, b: int) -> int:
    return a + b
>>>>>>> REPLACE

utils.py
<<<<<<< SEARCH
def sub(a, b):
    return a - b
=======
def sub(a: int, b: int) -> int:
    return a - b
>>>>>>> REPLACE
"""
        coder = EditBlockCoder.__new__(EditBlockCoder)
        coder.chat_files = []
        blocks = coder.parse_edits(response)
        assert len(blocks) == 2
        assert all(b.filename == "utils.py" for b in blocks)

    def test_new_file_empty_search(self):
        response = """\
newfile.py
<<<<<<< SEARCH
=======
print("hello")
>>>>>>> REPLACE
"""
        coder = EditBlockCoder.__new__(EditBlockCoder)
        coder.chat_files = []
        blocks = coder.parse_edits(response)
        assert len(blocks) == 1
        assert blocks[0].is_new_file is True
        assert "hello" in blocks[0].updated

    def test_no_blocks(self):
        response = "Here is my explanation of the code."
        coder = EditBlockCoder.__new__(EditBlockCoder)
        coder.chat_files = []
        blocks = coder.parse_edits(response)
        assert blocks == []


# ─── _do_replace tests ────────────────────────────────────────────────────

class TestDoReplace:
    def test_exact_match(self):
        content = "def foo():\n    pass\n"
        original = "def foo():\n    pass\n"
        updated = "def foo():\n    return 42\n"
        result = EditBlockCoder._do_replace(content, original, updated)
        assert result == "def foo():\n    return 42\n"

    def test_no_match(self):
        content = "def foo():\n    pass\n"
        result = EditBlockCoder._do_replace(content, "def bar():\n    pass\n", "x")
        assert result is None

    def test_replaces_first_occurrence(self):
        content = "x = 1\nx = 1\n"
        result = EditBlockCoder._do_replace(content, "x = 1\n", "x = 2\n")
        assert result == "x = 2\nx = 1\n"


# ─── _fuzzy_replace tests ─────────────────────────────────────────────────

class TestFuzzyReplace:
    def test_stripped_line_match(self):
        content = "def foo():\n    pass\n"
        original = "def foo():\n    pass"  # Missing trailing newline
        updated = "def foo():\n    return 1"
        result = EditBlockCoder._fuzzy_replace(content, original, updated)
        assert result is not None
        assert "return 1" in result

    def test_no_match(self):
        content = "def foo():\n    pass\n"
        result = EditBlockCoder._fuzzy_replace(content, "def bar():\n    x = 1\n", "y")
        assert result is None


# ─── apply_edits integration tests ────────────────────────────────────────

class TestApplyEdits:
    def test_edit_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        target = tmp_path / "hello.py"
        target.write_text("def greet():\n    pass\n")

        response = """\
hello.py
<<<<<<< SEARCH
def greet():
    pass
=======
def greet():
    print("Hello, World!")
>>>>>>> REPLACE
"""
        coder = make_coder(tmp_path)
        edited = coder.apply_edits(response)

        assert len(edited) == 1
        content = target.read_text()
        assert 'print("Hello, World!")' in content

    def test_create_new_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        response = """\
brand_new.py
<<<<<<< SEARCH
=======
# A new file
x = 42
>>>>>>> REPLACE
"""
        coder = make_coder(tmp_path)
        edited = coder.apply_edits(response)

        new_file = tmp_path / "brand_new.py"
        assert new_file.exists()
        assert "x = 42" in new_file.read_text()

    def test_missing_file_warns(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)

        response = """\
does_not_exist.py
<<<<<<< SEARCH
old code
=======
new code
>>>>>>> REPLACE
"""
        coder = make_coder(tmp_path)
        coder.io = None  # No IO, warnings go to stdout
        edited = coder.apply_edits(response)
        assert edited == []


# ─── _try_extract_filename tests ─────────────────────────────────────────

class TestTryExtractFilename:
    def test_simple_python(self):
        assert _try_extract_filename("main.py") == "main.py"

    def test_path(self):
        assert _try_extract_filename("src/utils.py") == "src/utils.py"

    def test_backtick_wrapped(self):
        assert _try_extract_filename("`main.py`") == "main.py"

    def test_no_extension(self):
        assert _try_extract_filename("Makefile") is None

    def test_sentence(self):
        assert _try_extract_filename("This is a sentence.") is None

    def test_empty(self):
        assert _try_extract_filename("") is None
