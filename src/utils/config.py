import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini-2.0-flash",
    "source_lang": "auto",
    "target_lang": "ar",
    "translation_mode": "text",
    "theme": "dark",
    "ui_language": "en",
    "system_prompt": "You are a game translator. Translate the following {source_lang} text to {target_lang}. Return ONLY the translation, nothing else.",
    "context_memory": True,
    "max_context": 10,
    "overlay": {
        "x": 100,
        "y": 100,
        "width": 500,
        "height": 150,
        "opacity": 0.85,
        "font_family": "Segoe UI",
        "font_size": 14,
        "font_color": "#ffffff",
        "bg_color": "#171717",
        "bg_opacity": 0.8,
    },
}

# User data dir — writable location for config/cache (works in PyInstaller bundle)
# Windows: ~/AppData/Local/LunaLite  |  Linux/macOS: ~/.config/LunaLite
USER_DATA_DIR = Path(
    os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", Path.home() / ".config"))
) / "LunaLite"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = USER_DATA_DIR / "config.json"


class ConfigManager:
    def __init__(self):
        self._config: dict = {}
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._config = self._merge(DEFAULT_CONFIG, saved)
            except (json.JSONDecodeError, OSError):
                self._config = dict(DEFAULT_CONFIG)
        else:
            self._config = dict(DEFAULT_CONFIG)

    def save(self):
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    def set(self, key: str, value: Any):
        keys = key.split(".")
        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    @property
    def data(self) -> dict:
        return self._config

    def _merge(self, default: dict, override: dict) -> dict:
        result = dict(default)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
