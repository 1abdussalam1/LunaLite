import os
import subprocess

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


def inject_hook(exe_path: str) -> bool:
    """Launch the game executable. Hook injection requires external DLL."""
    if not exe_path:
        raise ValueError("No game executable path specified")
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Executable not found: {exe_path}")
    try:
        subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to launch game: {e}") from e


class ClipboardMonitor(QObject):
    text_changed = pyqtSignal(str)

    def __init__(self, interval_ms: int = 500):
        super().__init__()
        self._last_text = ""
        self._running = False
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._check_clipboard)

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        clipboard = QApplication.clipboard()
        if clipboard:
            self._last_text = clipboard.text() or ""
        self._timer.start()

    def stop(self):
        self._running = False
        self._timer.stop()

    def _check_clipboard(self):
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        current = clipboard.text() or ""
        if current and current != self._last_text:
            self._last_text = current
            self.text_changed.emit(current)

    def get_current_text(self) -> str:
        clipboard = QApplication.clipboard()
        if clipboard:
            return clipboard.text() or ""
        return ""
