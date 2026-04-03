import json
from pathlib import Path
from typing import Optional


_LOCALES_DIR = Path(__file__).resolve().parent.parent.parent / "locales"
_current_lang = "en"
_strings: dict[str, str] = {}


def load_language(lang: str):
    global _current_lang, _strings
    filepath = _LOCALES_DIR / f"{lang}.json"
    if not filepath.exists():
        filepath = _LOCALES_DIR / "en.json"
        lang = "en"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            _strings = json.load(f)
        _current_lang = lang
    except (json.JSONDecodeError, OSError):
        _strings = {}
        _current_lang = lang


def t(key: str, default: Optional[str] = None) -> str:
    return _strings.get(key, default or key)


def current_language() -> str:
    return _current_lang


def is_rtl() -> bool:
    return _current_lang == "ar"


def available_languages() -> list[dict[str, str]]:
    return [
        {"code": "en", "name": "English"},
        {"code": "ar", "name": "العربية"},
    ]
