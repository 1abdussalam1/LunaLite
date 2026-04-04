"""
Text Hook via Named Pipe
Works with Textractor (https://github.com/Artikash/Textractor)
User needs: Textractor + NamedPipeOutput.xdll plugin

The plugin sends text to \\.\pipe\Glossa
"""
import threading
import time
import sys
from typing import Callable, Optional


class TextHookPipe:
    """
    Named Pipe server that receives text from Textractor or similar tools.
    On non-Windows, falls back to a dummy implementation.
    """
    PIPE_NAME = r"\\.\pipe\Glossa"

    def __init__(self, on_text_callback: Callable[[str], None]):
        self.on_text_callback = on_text_callback
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.is_windows = sys.platform == "win32"

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    @property
    def is_running(self) -> bool:
        return self.running

    def _run(self):
        if not self.is_windows:
            # Non-Windows: just wait (useful for dev/testing)
            print("[TextHook] Named Pipe only works on Windows")
            return

        try:
            import ctypes
            import ctypes.wintypes as wintypes

            kernel32 = ctypes.windll.kernel32

            PIPE_ACCESS_INBOUND = 0x00000001
            PIPE_TYPE_MESSAGE = 0x00000004
            PIPE_READMODE_MESSAGE = 0x00000002
            PIPE_WAIT = 0x00000000
            PIPE_UNLIMITED_INSTANCES = 255
            INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
            NMPWAIT_USE_DEFAULT_WAIT = 0x00000000

            while self.running:
                # Create named pipe
                pipe = kernel32.CreateNamedPipeW(
                    self.PIPE_NAME,
                    PIPE_ACCESS_INBOUND,
                    PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                    PIPE_UNLIMITED_INSTANCES,
                    65536,
                    65536,
                    NMPWAIT_USE_DEFAULT_WAIT,
                    None
                )

                if pipe == INVALID_HANDLE_VALUE:
                    time.sleep(1)
                    continue

                # Wait for client connection
                connected = kernel32.ConnectNamedPipe(pipe, None)
                if not connected and kernel32.GetLastError() != 535:  # ERROR_PIPE_CONNECTED
                    kernel32.CloseHandle(pipe)
                    continue

                # Read data loop
                while self.running:
                    buf = ctypes.create_string_buffer(65536)
                    bytes_read = wintypes.DWORD(0)
                    success = kernel32.ReadFile(
                        pipe,
                        buf,
                        65535,
                        ctypes.byref(bytes_read),
                        None
                    )

                    if not success or bytes_read.value == 0:
                        break

                    try:
                        text = buf.raw[:bytes_read.value].decode("utf-16-le", errors="ignore").strip()
                        if text and len(text) > 1:
                            self.on_text_callback(text)
                    except Exception:
                        pass

                kernel32.DisconnectNamedPipe(pipe)
                kernel32.CloseHandle(pipe)

        except Exception as e:
            print(f"[TextHook] Error: {e}")
