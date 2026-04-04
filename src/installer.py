"""
Glossa Auto-Installer
Checks and downloads required components on first run.
"""
import os
import sys
import urllib.request
import zipfile
import subprocess
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


BASE = get_base_dir()

COMPONENTS = {
    "textractor": {
        "name": "Textractor (Hook Engine)",
        "check": lambda: (BASE / "Textractor" / "x64" / "Textractor.exe").exists(),
        "url": "https://github.com/Artikash/Textractor/releases/download/v5.2.0/Textractor-5.2.0-Zip-Version-English-Only.zip",
        "install": "extract_zip",
        "dest": BASE / "Textractor",
    },
}


def needs_install() -> list:
    return [k for k, v in COMPONENTS.items() if not v["check"]()]


def download_with_progress(url: str, dest: Path, progress_cb=None) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Glossa/3.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        progress_cb(int(downloaded * 100 / total))
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False


def install_component(key: str, progress_cb=None) -> bool:
    comp = COMPONENTS[key]
    url = comp["url"]
    method = comp["install"]
    dest = comp["dest"]

    if method == "extract_zip":
        tmp = BASE / f"_tmp_{key}.zip"
        ok = download_with_progress(url, tmp, progress_cb)
        if not ok:
            return False
        try:
            Path(dest).mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(tmp, "r") as z:
                z.extractall(dest)
            tmp.unlink(missing_ok=True)
            return True
        except Exception as e:
            print(f"Extract error: {e}")
            tmp.unlink(missing_ok=True)
            return False

    return False
