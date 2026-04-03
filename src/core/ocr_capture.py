import threading
import time
import io

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class OCRCapture:
    def __init__(self, ai_client, on_text_callback):
        self.ai_client = ai_client
        self.on_text_callback = on_text_callback
        self.running = False
        self.interval = 2.0
        self.region = None
        self.last_text = ""

    def start(self, region=None):
        if not PIL_AVAILABLE:
            print("Pillow is not installed. OCR capture unavailable.")
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
                screenshot = ImageGrab.grab(bbox=self.region)
                img_bytes = io.BytesIO()
                screenshot.save(img_bytes, format="PNG")
                img_bytes = img_bytes.getvalue()

                text = self.ai_client.ocr_screenshot(img_bytes)
                if text and text != self.last_text and len(text.strip()) > 2:
                    self.last_text = text
                    self.on_text_callback(text)
            except Exception as e:
                print(f"OCR error: {e}")
            time.sleep(self.interval)

    def set_interval(self, seconds: float):
        self.interval = max(1.0, min(10.0, seconds))

    def capture_region_selector(self):
        """Return region tuple or None for full screen."""
        return None
