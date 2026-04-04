"""
Glossa Build Script
Run on Windows: python build.py
Output: dist/Glossa/ folder ready to zip and share
"""
import subprocess, sys, os, shutil


def build():
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",              # folder mode (faster startup than onefile)
        "--windowed",            # no console window
        "--name", "Glossa",
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
        # Hidden imports openai (for GLM)
        "--hidden-import", "openai",
        # Other hidden imports
        "--hidden-import", "pyaudiowpatch",
        "--hidden-import", "numpy",
        "--hidden-import", "scipy",
        "--hidden-import", "sqlite3",
        "--hidden-import", "mss",
        "--hidden-import", "mss.tools",
        "--hidden-import", "pytesseract",
        # Entry point
        "src/main.py",
    ]
    subprocess.run(cmd, check=True)
    print("\nBuild complete! Output: dist/Glossa/")
    print("Zip dist/Glossa/ and share!")


if __name__ == "__main__":
    build()
