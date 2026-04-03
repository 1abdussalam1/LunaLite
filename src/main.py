import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.paths import resource_path  # noqa: E402, F401 — re-export for convenience

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.config import ConfigManager
from src.utils.i18n import load_language, i18n
from src.utils.theme import apply_theme
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Glossa")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)

    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    config = ConfigManager()
    load_language(config.get("ui_language", "en"))

    # Apply startup theme
    theme = config.get("theme", "dark")
    apply_theme(theme == "dark")

    # Set layout direction based on language
    ui_lang = config.get("ui_language", "en")
    if ui_lang == "ar":
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    # Connect language changes to layout direction
    def on_language_changed(lang):
        if lang == "ar":
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    i18n.language_changed.connect(on_language_changed)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
