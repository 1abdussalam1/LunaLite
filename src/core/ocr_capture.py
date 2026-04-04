import threading
import time
import io
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


class OCRCapture:
    def __init__(self, ai_client, on_text_callback):
        self.ai_client = ai_client
        self.on_text_callback = on_text_callback
        self.running = False
        self.interval = 2.0
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.last_text = ""

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

    def capture_region_selector(self):
        """Return current region or None for full screen."""
        return self.region
