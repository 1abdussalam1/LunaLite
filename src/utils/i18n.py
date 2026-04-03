import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.utils.paths import resource_path


class I18N(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = "en"
        self._strings: dict[str, str] = {}

    def load(self, lang: str):
        locales = Path(resource_path("locales"))
        filepath = locales / f"{lang}.json"
        if not filepath.exists():
            filepath = locales / "en.json"
            lang = "en"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self._strings = json.load(f)
            self._lang = lang
        except (json.JSONDecodeError, OSError):
            self._strings = {}
            self._lang = lang

        # Set layout direction for the whole application
        app = QApplication.instance()
        if app:
            if lang == "ar":
                app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            else:
                app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.language_changed.emit(lang)

    def t(self, key: str, **kwargs) -> str:
        s = self._strings.get(key, key)
        return s.format(**kwargs) if kwargs else s

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def is_rtl(self) -> bool:
        return self._lang == "ar"


# Singleton
i18n = I18N()
tr = i18n.t


# --- Compatibility wrappers (used by existing code) ---

def load_language(lang: str):
    i18n.load(lang)


def t(key: str, default: Optional[str] = None) -> str:
    s = i18n._strings.get(key, default or key)
    return s


def current_language() -> str:
    return i18n.lang


def is_rtl() -> bool:
    return i18n.is_rtl


def available_languages() -> list[dict[str, str]]:
    return [
        {"code": "en", "name": "English"},
        {"code": "ar", "name": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629"},
    ]


def on_language_changed(callback):
    i18n.language_changed.connect(callback)
