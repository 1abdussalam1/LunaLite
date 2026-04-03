"""
LunaLite Build Script
Run on Windows: python build.py
Output: dist/LunaLite/ folder ready to zip and share
"""
import subprocess, sys, os, shutil


def build():
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",              # folder mode (faster startup than onefile)
        "--windowed",            # no console window
        "--name", "LunaLite",
        "--icon", "assets/icon.ico",
        # Include data folders
        "--add-data", "locales;locales",
        "--add-data", "assets;assets",
        # Hidden imports PyQt6
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.sip",
        # Hidden imports google
        "--hidden-import", "google.generativeai",
        "--hidden-import", "google.auth",
        "--hidden-import", "google.auth.transport.requests",
        # Other hidden imports
        "--hidden-import", "pyaudiowpatch",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",
        "--hidden-import", "sqlite3",
        # Entry point
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)
    print("\n\u2705 Build complete! Output: dist/LunaLite/")
    print("Zip dist/LunaLite/ and share!")


if __name__ == "__main__":
    build()
