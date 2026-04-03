import io
import struct
import threading
import wave
from typing import Callable, Optional

import numpy as np

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

from PyQt6.QtCore import QObject, pyqtSignal


TARGET_RATE = 16000
TARGET_CHANNELS = 1
CHUNK_DURATION = 3  # seconds


class AudioCapture(QObject):
    audio_chunk_ready = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    device_list_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pa: Optional[object] = None
        self._stream = None
        self._device_index: Optional[int] = None
        self._on_audio_chunk: Optional[Callable[[bytes], None]] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def set_callback(self, callback: Callable[[bytes], None]):
        self._on_audio_chunk = callback

    def list_loopback_devices(self) -> list[dict]:
        if not PYAUDIO_AVAILABLE:
            self.error_occurred.emit("pyaudiowpatch is not installed. Audio capture requires Windows with WASAPI.")
            return []
        devices = []
        try:
            pa = pyaudio.PyAudio()
            try:
                wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                self.error_occurred.emit("WASAPI not available on this system.")
                pa.terminate()
                return []

            for i in range(pa.get_device_count()):
                dev = pa.get_device_info_by_index(i)
                if dev.get("hostApi") == wasapi_info.get("index"):
                    if dev.get("isLoopbackDevice", False) or dev.get("maxInputChannels", 0) > 0:
                        devices.append({
                            "index": i,
                            "name": dev.get("name", f"Device {i}"),
                            "channels": dev.get("maxInputChannels", 2),
                            "rate": int(dev.get("defaultSampleRate", 44100)),
                            "is_loopback": dev.get("isLoopbackDevice", False),
                        })
            pa.terminate()
        except Exception as e:
            self.error_occurred.emit(f"Error listing audio devices: {e}")
        self.device_list_ready.emit(devices)
        return devices

    def get_default_loopback(self) -> Optional[dict]:
        if not PYAUDIO_AVAILABLE:
            return None
        try:
            pa = pyaudio.PyAudio()
            try:
                wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_output = pa.get_device_info_by_index(wasapi_info.get("defaultOutputDevice", 0))
                for i in range(pa.get_device_count()):
                    dev = pa.get_device_info_by_index(i)
                    if dev.get("isLoopbackDevice", False):
                        if dev.get("name", "").startswith(default_output.get("name", "???")):
                            pa.terminate()
                            return {
                                "index": i,
                                "name": dev.get("name", f"Device {i}"),
                                "channels": dev.get("maxInputChannels", 2),
                                "rate": int(dev.get("defaultSampleRate", 44100)),
                                "is_loopback": True,
                            }
            except OSError:
                pass
            pa.terminate()
        except Exception:
            pass
        return None

    def set_device(self, device_index: int):
        self._device_index = device_index

    def start(self):
        if self._running:
            return
        if not PYAUDIO_AVAILABLE:
            self.error_occurred.emit("pyaudiowpatch is not installed. Audio capture requires Windows.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None

    def _capture_loop(self):
        try:
            self._pa = pyaudio.PyAudio()
            device = None

            if self._device_index is not None:
                device = self._pa.get_device_info_by_index(self._device_index)
            else:
                default = self.get_default_loopback()
                if default:
                    device = self._pa.get_device_info_by_index(default["index"])

            if device is None:
                self.error_occurred.emit("No loopback audio device found.")
                self._pa.terminate()
                self._running = False
                return

            channels = device.get("maxInputChannels", 2)
            rate = int(device.get("defaultSampleRate", 44100))
            chunk_size = int(rate * CHUNK_DURATION)

            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=1024,
            )

            buffer = b""
            bytes_per_chunk = chunk_size * channels * 2  # 16-bit = 2 bytes

            while self._running:
                try:
                    data = self._stream.read(1024, exception_on_overflow=False)
                    buffer += data
                    if len(buffer) >= bytes_per_chunk:
                        chunk = buffer[:bytes_per_chunk]
                        buffer = buffer[bytes_per_chunk:]
                        wav_bytes = self._convert_to_target_format(chunk, channels, rate)
                        self.audio_chunk_ready.emit(wav_bytes)
                        if self._on_audio_chunk:
                            self._on_audio_chunk(wav_bytes)
                except Exception:
                    if not self._running:
                        break

            self._stream.stop_stream()
            self._stream.close()
            self._pa.terminate()
        except Exception as e:
            self.error_occurred.emit(f"Audio capture error: {e}")
            self._running = False

    def _convert_to_target_format(self, raw_data: bytes, source_channels: int, source_rate: int) -> bytes:
        samples = np.frombuffer(raw_data, dtype=np.int16)

        if source_channels > 1:
            samples = samples.reshape(-1, source_channels)
            samples = samples.mean(axis=1).astype(np.int16)

        if source_rate != TARGET_RATE:
            num_samples = int(len(samples) * TARGET_RATE / source_rate)
            indices = np.linspace(0, len(samples) - 1, num_samples).astype(int)
            samples = samples[indices]

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(TARGET_CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(samples.tobytes())

        return buf.getvalue()
