"""Tests for file utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from qgo.utils.file_utils import (
    create_file,
    get_file_language,
    is_text_file,
    make_diff,
    read_file,
    write_file,
)


class TestReadWriteFile:
    def test_write_and_read(self, tmp_path):
        p = tmp_path / "test.txt"
        write_file(p, "hello world")
        assert read_file(p) == "hello world"

    def test_write_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "nested" / "dir" / "file.py"
        write_file(p, "x = 1")
        assert p.exists()
        assert p.read_text() == "x = 1"

    def test_read_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_file(tmp_path / "ghost.txt")

    def test_create_file(self, tmp_path):
        p = tmp_path / "new.py"
        create_file(p, "print('hi')")
        assert p.read_text() == "print('hi')"

    def test_create_file_exists_error(self, tmp_path):
        p = tmp_path / "existing.py"
        p.write_text("original")
        with pytest.raises(FileExistsError):
            create_file(p, "new content")


class TestIsTextFile:
    def test_python_file_is_text(self, tmp_path):
        p = tmp_path / "script.py"
        p.write_text("print('hello')")
        assert is_text_file(p) is True

    def test_png_is_binary(self, tmp_path):
        # PNG files have .png extension which is in binary list
        p = tmp_path / "image.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert is_text_file(p) is False

    def test_file_with_null_bytes_is_binary(self, tmp_path):
        p = tmp_path / "binary.bin"
        p.write_bytes(b"some data\x00more data")
        assert is_text_file(p) is False


class TestGetFileLanguage:
    @pytest.mark.parametrize("filename,expected", [
        ("main.py", "python"),
        ("app.js", "javascript"),
        ("component.tsx", "typescript"),
        ("server.go", "go"),
        ("lib.rs", "rust"),
        ("Main.java", "java"),
        ("unknown.xyz", ""),
    ])
    def test_language_detection(self, filename, expected):
        assert get_file_language(filename) == expected


class TestMakeDiff:
    def test_simple_diff(self):
        original = "line1\nline2\nline3\n"
        updated = "line1\nLINE2\nline3\n"
        diff = make_diff(original, updated, "test.txt")
        assert "-line2" in diff
        assert "+LINE2" in diff

    def test_no_changes(self):
        content = "unchanged\n"
        diff = make_diff(content, content, "file.txt")
        assert diff == ""

    def test_diff_contains_filename(self):
        diff = make_diff("a\n", "b\n", "myfile.py")
        assert "myfile.py" in diff

    def test_new_content(self):
        diff = make_diff("", "hello\nworld\n", "new.py")
        assert "+hello" in diff
        assert "+world" in diff
