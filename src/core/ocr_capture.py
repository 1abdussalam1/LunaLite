"""
OCR Capture using local Tesseract OCR
Captures screen -> Tesseract reads text -> sends to translator

Requirements on Windows:
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- pip install pytesseract
- Download language data: jpn.traineddata, chi_sim.traineddata, kor.traineddata
  Put in Tesseract tessdata folder
"""
import threading
import time
import io
import os
from typing import Optional, Tuple

# Try MSS first (works with DirectX fullscreen games)
# fallback to PIL ImageGrab
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def grab_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
    """
    Capture screen using MSS (works with DirectX/fullscreen games).
    Falls back to PIL ImageGrab if MSS not available.
    Returns PNG bytes.
    """
    if MSS_AVAILABLE:
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"top": y, "left": x, "width": w, "height": h}
            else:
                monitor = sct.monitors[1]  # primary monitor
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    elif PIL_AVAILABLE:
        bbox = None
        if region:
            x, y, w, h = region
            bbox = (x, y, x + w, y + h)
        screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        return buf.getvalue()
    else:
        raise RuntimeError("Neither mss nor Pillow is installed. Cannot capture screen.")


def ocr_with_tesseract(image_bytes: bytes, lang: str = "jpn+chi_sim+kor+eng") -> str:
    """Use local Tesseract to extract text from image."""
    try:
        import pytesseract
        from PIL import Image

        import sys

        # Check bundled Tesseract first (inside Glossa folder)
        if getattr(sys, 'frozen', False):
            # PyInstaller bundle - Tesseract is next to Glossa.exe
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        tesseract_paths = [
            os.path.join(base, "Tesseract-OCR", "tesseract.exe"),  # bundled
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]

        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                # Set tessdata path
                tessdata = os.path.join(os.path.dirname(path), "tessdata")
                os.environ["TESSDATA_PREFIX"] = tessdata
                break

        img = Image.open(io.BytesIO(image_bytes))

        # Convert to grayscale for better OCR
        img = img.convert("L")

        # Upscale small images for better accuracy
        if img.width < 800:
            scale = 2
            img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)

        text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        return text.strip()
    except ImportError:
        return ""
    except Exception as e:
        print(f"Tesseract error: {e}")
        return ""


class OCRCapture:
    def __init__(self, ai_client, on_text_callback):
        self.ai_client = ai_client
        self.on_text_callback = on_text_callback
        self.running = False
        self.interval = 2.0
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.last_text = ""
        self.ocr_lang = "jpn+chi_sim+kor+eng"  # Tesseract language codes

    def start(self, region=None):
        if not MSS_AVAILABLE and not PIL_AVAILABLE:
            print("No screen capture library available. Install mss: pip install mss")
            return
        self.region = region
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    @property
    def is_running(self) -> bool:
        return self.running

    def _loop(self):
        while self.running:
            try:
                img_bytes = grab_screenshot(self.region)

                # Try Tesseract first (local, fast, no API needed)
                text = ocr_with_tesseract(img_bytes, self.ocr_lang)

                # If Tesseract not available or no text, try AI vision
                if not text and hasattr(self, "ai_client") and self.ai_client:
                    text = self.ai_client.ocr_screenshot(img_bytes)

                if text and text.strip() != self.last_text and len(text.strip()) > 2:
                    self.last_text = text.strip()
                    self.on_text_callback(text.strip())
            except Exception as e:
                print(f"OCR capture error: {e}")
            time.sleep(self.interval)

    def set_interval(self, seconds: float):
        self.interval = max(1.0, min(10.0, seconds))

    def set_region(self, region: Optional[Tuple[int, int, int, int]]):
        """Set capture region (x, y, width, height) or None for full screen."""
        self.region = region

    def set_ocr_lang(self, lang: str):
        """Set Tesseract OCR language codes (e.g. 'jpn+eng')."""
        self.ocr_lang = lang

    def capture_region_selector(self):
        """Return current region or None for full screen."""
        return self.region
