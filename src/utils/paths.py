import sys
import os


def resource_path(relative_path: str) -> str:
    """Get absolute path — works for dev and PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller bundle: resources are in _MEIPASS temp folder
        base_path = sys._MEIPASS
    else:
        # Development: relative to project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)
