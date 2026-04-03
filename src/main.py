import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.paths import resource_path  # noqa: E402, F401 — re-export for convenience

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.config import ConfigManager
from src.utils.i18n import load_language, i18n
from src.ui.main_window import MainWindow


DARK_THEME = """
    QWidget { background-color: #171717; color: #ffffff; font-family: "Segoe UI"; }
    QMainWindow, QDialog { background-color: #171717; }
    QPushButton {
        background-color: #0f3460; color: white; border-radius: 6px;
        padding: 6px 14px; border: none;
    }
    QPushButton:hover { background-color: #1a4a7a; }
    QPushButton:pressed { background-color: #0a2840; }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #1e1e1e; color: #fff;
        border: 1px solid #333; border-radius: 4px; padding: 6px;
    }
    QComboBox {
        background-color: #1e1e1e; color: #fff;
        border: 1px solid #333; border-radius: 4px; padding: 4px 8px;
    }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox::down-arrow {
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #ffffff;
        width: 0; height: 0;
    }
    QComboBox QAbstractItemView {
        background-color: #1e1e1e; color: #fff;
        selection-background-color: #0f3460;
    }
    QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #333; }
    QTabBar::tab {
        background-color: #171717; color: #aaa;
        padding: 8px 18px; border-radius: 4px 4px 0 0;
    }
    QTabBar::tab:selected { background-color: #0f3460; color: white; }
    QTabBar::tab:hover { background-color: #252525; color: white; }
    QSlider::groove:horizontal { background: #333; height: 4px; border-radius: 2px; }
    QSlider::handle:horizontal {
        background: #0f3460; width: 16px; height: 16px;
        border-radius: 8px; margin: -6px 0;
    }
    QCheckBox { color: #fff; spacing: 8px; }
    QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #555; }
    QCheckBox::indicator:checked { background-color: #0f3460; border-color: #0f3460; }
    QRadioButton { color: #fff; spacing: 8px; }
    QRadioButton::indicator { width: 16px; height: 16px; border-radius: 8px; border: 2px solid #555; }
    QRadioButton::indicator:checked { background-color: #0f3460; border-color: #0f3460; }
    QLabel { color: #ffffff; }
    QGroupBox {
        color: #aaa; border: 1px solid #333; border-radius: 6px;
        margin-top: 12px; padding-top: 10px; font-weight: bold;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #aaa; }
    QScrollBar:vertical { background: #1e1e1e; width: 8px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #444; border-radius: 4px; min-height: 20px; }
    QSplitter::handle { background: #333; }
    QStatusBar { background: #1e1e1e; color: #aaa; }
    QSpinBox {
        background-color: #1e1e1e; color: #fff;
        border: 1px solid #333; border-radius: 4px; padding: 4px;
    }
"""

LIGHT_THEME = """
    QWidget { background-color: #f0f0f0; color: #1a1a1a; font-family: "Segoe UI"; }
    QMainWindow, QDialog { background-color: #f0f0f0; }
    QPushButton {
        background-color: #1565c0; color: white; border-radius: 6px;
        padding: 6px 14px; border: none;
    }
    QPushButton:hover { background-color: #1976d2; }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #ffffff; color: #1a1a1a;
        border: 1px solid #ccc; border-radius: 4px; padding: 6px;
    }
    QComboBox {
        background-color: #ffffff; color: #1a1a1a;
        border: 1px solid #ccc; border-radius: 4px; padding: 4px 8px;
    }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox::down-arrow {
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #1a1a1a;
        width: 0; height: 0;
    }
    QComboBox QAbstractItemView {
        background-color: #fff; color: #1a1a1a;
        selection-background-color: #1565c0; selection-color: white;
    }
    QTabWidget::pane { background-color: #ffffff; border: 1px solid #ccc; }
    QTabBar::tab {
        background-color: #e0e0e0; color: #555;
        padding: 8px 18px; border-radius: 4px 4px 0 0;
    }
    QTabBar::tab:selected { background-color: #1565c0; color: white; }
    QSlider::groove:horizontal { background: #ccc; height: 4px; border-radius: 2px; }
    QSlider::handle:horizontal {
        background: #1565c0; width: 16px; height: 16px;
        border-radius: 8px; margin: -6px 0;
    }
    QCheckBox { color: #1a1a1a; spacing: 8px; }
    QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #aaa; }
    QCheckBox::indicator:checked { background-color: #1565c0; border-color: #1565c0; }
    QLabel { color: #1a1a1a; }
    QGroupBox {
        color: #555; border: 1px solid #ccc; border-radius: 6px;
        margin-top: 12px; padding-top: 10px; font-weight: bold;
    }
    QSpinBox {
        background-color: #ffffff; color: #1a1a1a;
        border: 1px solid #ccc; border-radius: 4px; padding: 4px;
    }
"""


def apply_theme(is_dark: bool):
    app = QApplication.instance()
    if app:
        app.setStyleSheet(DARK_THEME if is_dark else LIGHT_THEME)


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
