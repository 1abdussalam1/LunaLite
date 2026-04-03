# LunaLite

Real-time game translation tool powered by Google Gemini AI.

## Features

- **Text Translation**: Captures clipboard text and translates in real-time
- **Audio Translation**: Captures system audio via WASAPI loopback and translates speech
- **Transparent Overlay**: Always-on-top draggable overlay to display translations
- **Multiple Languages**: Japanese, Chinese, Korean, English, Arabic, and more
- **Translation Cache**: SQLite-based cache to avoid repeated API calls
- **Dark/Light Theme**: Customizable appearance with animated theme toggle
- **RTL Support**: Full Arabic RTL layout support
- **Bilingual UI**: English and Arabic interface

## Run in Development

```bash
pip install -r requirements.txt
cd src && python main.py
```

1. Open Settings and enter your Gemini API key
2. Select source and target languages
3. Choose translation mode (Text or Audio)
4. Click the power button to start translating

## Build Standalone EXE (Windows)

No Python installation required for end users.

```bash
pip install -r requirements-build.txt
python scripts/create_icon.py
python build.py
```

Output: `dist/LunaLite/LunaLite.exe`

Zip `dist/LunaLite/` and share!

For reproducible builds using the spec file:

```bash
pyinstaller LunaLite.spec
```

## Requirements

- Python 3.10+
- Windows (for WASAPI audio loopback)
- Google Gemini API key

## License

MIT
