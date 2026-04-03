import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.utils.paths import resource_path


class _I18nManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()


_manager = _I18nManager()

_current_lang = "en"
_strings: dict[str, str] = {}


def _locales_dir() -> Path:
    return Path(resource_path("locales"))


def load_language(lang: str):
    global _current_lang, _strings
    locales = _locales_dir()
    filepath = locales / f"{lang}.json"
    if not filepath.exists():
        filepath = locales / "en.json"
        lang = "en"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            _strings = json.load(f)
        _current_lang = lang
    except (json.JSONDecodeError, OSError):
        _strings = {}
        _current_lang = lang

    # Set layout direction for the whole application
    app = QApplication.instance()
    if app:
        if lang == "ar":
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    _manager.language_changed.emit()


def t(key: str, default: Optional[str] = None) -> str:
    return _strings.get(key, default or key)


def current_language() -> str:
    return _current_lang


def is_rtl() -> bool:
    return _current_lang == "ar"


def available_languages() -> list[dict[str, str]]:
    return [
        {"code": "en", "name": "English"},
        {"code": "ar", "name": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629"},
    ]


def on_language_changed(callback):
    _manager.language_changed.connect(callback)
