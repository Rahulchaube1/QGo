"""File-system watcher for QGo — detects external changes to tracked files."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional


class FileWatcher:
    """Watch a directory for file changes using watchdog.

    Calls *callback(path)* whenever a tracked file is modified externally.
    """

    def __init__(
        self,
        root: str | Path,
        callback: Callable[[Path], None],
        patterns: list[str] | None = None,
    ) -> None:
        self.root = Path(root)
        self.callback = callback
        self.patterns = patterns or ["*.py", "*.js", "*.ts", "*.go", "*.rs",
                                      "*.java", "*.cpp", "*.c", "*.rb", "*.php"]
        self._observer: Optional[object] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Start watching. Returns False if watchdog is not installed."""
        try:
            from watchdog.observers import Observer

            handler = _ChangeHandler(self.callback, self.patterns)
            observer = Observer()
            observer.schedule(handler, str(self.root), recursive=True)
            observer.start()
            self._observer = observer
            return True
        except ImportError:
            return False

    def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            try:
                self._observer.stop()  # type: ignore[attr-defined]
                self._observer.join()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._observer = None


try:
    from watchdog.events import PatternMatchingEventHandler as _Base

    class _ChangeHandler(_Base):
        def __init__(self, callback: Callable[[Path], None], patterns: list[str]) -> None:
            super().__init__(patterns=patterns, ignore_directories=True)
            self._callback = callback

        def on_modified(self, event) -> None:  # type: ignore[override]
            self._callback(Path(event.src_path))

        def on_created(self, event) -> None:  # type: ignore[override]
            self._callback(Path(event.src_path))

except ImportError:
    # watchdog not installed — create a stub that does nothing

    class _ChangeHandler:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            pass
