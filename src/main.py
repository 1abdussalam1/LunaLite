import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.paths import resource_path  # noqa: E402, F401 — re-export for convenience

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.config import ConfigManager
from src.utils.i18n import load_language
from src.ui.main_window import MainWindow


def _apply_startup_theme(app, config):
    theme = config.get("theme", "dark")
    if theme == "dark":
        bg, panel, text, accent = "#171717", "#1e1e1e", "#ffffff", "#0f3460"
    else:
        bg, panel, text, accent = "#f5f5f5", "#ffffff", "#1a1a1a", "#1565c0"

    app.setStyleSheet(f"""
        QWidget {{ background-color: {bg}; color: {text}; }}
        QDialog, QMainWindow {{ background-color: {bg}; }}
        QPushButton {{ background-color: {accent}; color: white; border-radius: 6px; padding: 6px 12px; }}
        QLineEdit, QTextEdit, QComboBox {{ background-color: {panel}; color: {text}; border: 1px solid #333; border-radius: 4px; padding: 4px; }}
        QTabWidget::pane {{ background-color: {panel}; border: 1px solid #333; }}
        QTabBar::tab {{ background-color: {bg}; color: {text}; padding: 8px 16px; }}
        QTabBar::tab:selected {{ background-color: {accent}; color: white; }}
        QSlider::groove:horizontal {{ background: #333; height: 4px; border-radius: 2px; }}
        QSlider::handle:horizontal {{ background: {accent}; width: 14px; height: 14px; border-radius: 7px; margin: -5px 0; }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox::down-arrow {{ border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {text}; width: 0; height: 0; }}
        QCheckBox {{ color: {text}; }}
        QLabel {{ color: {text}; }}
        QGroupBox {{ color: {text}; border: 1px solid #444; border-radius: 6px; margin-top: 8px; padding-top: 8px; }}
    """)

    # Set layout direction based on language
    ui_lang = config.get("ui_language", "en")
    if ui_lang == "ar":
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LunaLite")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)

    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    config = ConfigManager()
    load_language(config.get("ui_language", "en"))

    _apply_startup_theme(app, config)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
