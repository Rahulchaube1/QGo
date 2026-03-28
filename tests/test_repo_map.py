"""Tests for repository mapper."""

from __future__ import annotations

from pathlib import Path
import pytest

from qgo.repo.repo_map import RepoMap


class TestRepoMapSymbolExtraction:
    def test_python_class(self, tmp_path):
        p = tmp_path / "mymodule.py"
        p.write_text("class MyClass:\n    pass\n")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        names = [t["name"] for t in tags]
        assert "MyClass" in names

    def test_python_function(self, tmp_path):
        p = tmp_path / "funcs.py"
        p.write_text("def compute(x):\n    return x * 2\n")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        names = [t["name"] for t in tags]
        assert "compute" in names

    def test_typescript_interface(self, tmp_path):
        p = tmp_path / "types.ts"
        p.write_text("export interface UserProfile {\n    name: string;\n}\n")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        names = [t["name"] for t in tags]
        assert "UserProfile" in names

    def test_go_function(self, tmp_path):
        p = tmp_path / "main.go"
        p.write_text("func HandleRequest(w http.ResponseWriter) {\n}\n")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        names = [t["name"] for t in tags]
        assert "HandleRequest" in names

    def test_no_symbols_in_text_file(self, tmp_path):
        p = tmp_path / "README.md"
        p.write_text("# My Project\nThis is the readme.")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        assert tags == []

    def test_ignores_private_symbols(self, tmp_path):
        p = tmp_path / "private.py"
        p.write_text("def _private_func():\n    pass\n\ndef public_func():\n    pass\n")
        rm = RepoMap(root=tmp_path)
        tags = rm.get_file_symbols(p)
        names = [t["name"] for t in tags]
        assert "public_func" in names
        assert "_private_func" not in names


class TestRepoMapGetAllFiles:
    def test_finds_python_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "notes.txt").write_text("some text")
        rm = RepoMap(root=tmp_path)
        files = rm.get_all_files()
        names = [f.name for f in files]
        assert "a.py" in names
        assert "b.py" in names

    def test_excludes_pycache(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.pyc").write_bytes(b"\x00")
        (tmp_path / "real.py").write_text("x = 1")
        rm = RepoMap(root=tmp_path)
        files = rm.get_all_files()
        names = [f.name for f in files]
        assert "module.pyc" not in names
        assert "real.py" in names


class TestRepoMapGetRepoMap:
    def test_returns_string(self, tmp_path):
        (tmp_path / "main.py").write_text("def main():\n    pass\n")
        rm = RepoMap(root=tmp_path)
        result = rm.get_repo_map()
        assert isinstance(result, str)

    def test_excludes_chat_files(self, tmp_path):
        p = tmp_path / "main.py"
        p.write_text("def main():\n    pass\n")
        rm = RepoMap(root=tmp_path)
        # When main.py IS in chat_files, it should not appear in the map
        result = rm.get_repo_map(chat_files=[str(p)])
        # The map should be empty or not contain main.py symbols
        assert "main.py" not in result or result == ""

    def test_empty_dir(self, tmp_path):
        rm = RepoMap(root=tmp_path)
        result = rm.get_repo_map()
        assert result == ""
