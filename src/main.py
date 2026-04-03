import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.config import ConfigManager
from src.utils.i18n import load_language
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LunaLite")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)

    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    config = ConfigManager()
    load_language(config.get("ui_language", "en"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
