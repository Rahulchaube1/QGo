"""Git repository integration for QGo."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class GitRepo:
    """Wrapper around git operations for QGo.

    Handles auto-commits, diffs, undo, and branch management.
    """

    def __init__(self, path: str | Path = ".") -> None:
        self._root = self.find_git_root(Path(path))
        if self._root is None:
            self._root = Path(path).resolve()
        self._git_root = self._root

    # ─── Repository info ──────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    @staticmethod
    def is_git_repo(path: str | Path = ".") -> bool:
        """Return True if *path* is inside a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(path),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def find_git_root(path: Path) -> Optional[Path]:
        """Walk up from *path* to find the git root directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(path.resolve()),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except FileNotFoundError:
            pass
        return None

    def get_current_branch(self) -> str:
        """Return the current branch name."""
        result = self._run(["git", "branch", "--show-current"])
        return result.strip() or "HEAD"

    def get_commit_hash(self, short: bool = True) -> str:
        """Return the current HEAD commit hash."""
        cmd = ["git", "rev-parse", "--short" if short else None, "HEAD"]
        cmd = [c for c in cmd if c]
        result = self._run(cmd)
        return result.strip()

    # ─── File management ──────────────────────────────────────────────

    def get_tracked_files(self) -> list[Path]:
        """Return all files tracked by git."""
        result = self._run(["git", "ls-files"])
        return [
            self._root / f.strip()
            for f in result.splitlines()
            if f.strip()
        ]

    def get_dirty_files(self) -> list[Path]:
        """Return files with uncommitted changes (modified or untracked)."""
        result = self._run(["git", "status", "--porcelain"])
        files: list[Path] = []
        for line in result.splitlines():
            if len(line) >= 3:
                filepath = line[3:].strip()
                # Handle renames: "old -> new"
                if " -> " in filepath:
                    filepath = filepath.split(" -> ")[-1]
                files.append(self._root / filepath)
        return files

    def is_dirty(self, path: str | Path) -> bool:
        """Return True if the given file has uncommitted changes."""
        rel = Path(path)
        try:
            rel = rel.relative_to(self._root)
        except ValueError:
            pass
        result = self._run(["git", "status", "--porcelain", str(rel)])
        return bool(result.strip())

    # ─── Committing ───────────────────────────────────────────────────

    def add(self, files: list[str | Path] | None = None) -> None:
        """Stage files for commit. If files is None, stages everything."""
        if files:
            paths = [str(f) for f in files]
            self._run(["git", "add", "--"] + paths)
        else:
            self._run(["git", "add", "-A"])

    def commit(
        self,
        message: str,
        files: list[str | Path] | None = None,
        author: str | None = None,
    ) -> str:
        """Stage and commit files. Returns the new commit hash."""
        self.add(files)
        cmd = ["git", "commit", "-m", message]
        if author:
            cmd += ["--author", author]
        result = self._run(cmd)
        # Extract commit hash from output like "[main abc1234] message"
        for line in result.splitlines():
            if line.startswith("["):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1].rstrip("]")
        return self.get_commit_hash()

    def auto_commit(
        self,
        files: list[str | Path],
        message: str | None = None,
        attribution: str = "QGo",
    ) -> str | None:
        """Auto-commit a list of files changed by the AI.

        Returns the commit hash, or None if there was nothing to commit.
        """
        # Check if any files are actually changed
        changed = [f for f in files if self.is_dirty(f)]
        if not changed:
            return None
        if message is None:
            filenames = ", ".join(Path(f).name for f in changed[:3])
            if len(changed) > 3:
                filenames += f" (+{len(changed)-3} more)"
            message = f"{attribution}: Edit {filenames}"
        return self.commit(message, files=changed)

    # ─── History / undo ───────────────────────────────────────────────

    def undo_last_commit(self) -> str:
        """Soft-reset HEAD~1, keeping changes in the working tree."""
        result = self._run(["git", "reset", "HEAD~1", "--mixed"])
        return result.strip()

    def get_diff(
        self,
        files: list[str | Path] | None = None,
        staged: bool = False,
        commit: str | None = None,
    ) -> str:
        """Return a unified diff."""
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if commit:
            cmd.extend([f"{commit}^", commit])
        if files:
            cmd += ["--"] + [str(f) for f in files]
        return self._run(cmd)

    def get_commit_history(self, n: int = 10) -> list[dict]:
        """Return a list of recent commits as dicts."""
        result = self._run([
            "git", "log", f"-{n}",
            "--pretty=format:%H|%h|%s|%an|%ad",
            "--date=short",
        ])
        history = []
        for line in result.splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                history.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "subject": parts[2],
                    "author": parts[3],
                    "date": parts[4],
                })
        return history

    # ─── Branch management ────────────────────────────────────────────

    def create_branch(self, name: str, checkout: bool = True) -> None:
        """Create a new branch, optionally checking it out."""
        self._run(["git", "branch", name])
        if checkout:
            self._run(["git", "checkout", name])

    def list_branches(self) -> list[str]:
        """Return all local branch names."""
        result = self._run(["git", "branch", "--format=%(refname:short)"])
        return [b.strip() for b in result.splitlines() if b.strip()]

    # ─── Private ──────────────────────────────────────────────────────

    def _run(self, cmd: list[str]) -> str:
        """Run a git command in the repo root, return stdout."""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self._root),
                capture_output=True,
                text=True,
            )
            return result.stdout
        except FileNotFoundError:
            return ""
        except Exception:
            return ""
