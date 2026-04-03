import base64
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QThread


API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class TokenUsage:
    def __init__(self):
        self.total_input = 0
        self.total_output = 0

    def add(self, input_tokens: int, output_tokens: int):
        self.total_input += input_tokens
        self.total_output += output_tokens

    def reset(self):
        self.total_input = 0
        self.total_output = 0

    @property
    def total(self) -> int:
        return self.total_input + self.total_output


class GeminiClient(QObject):
    translation_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    models_fetched = pyqtSignal(list)
    api_test_result = pyqtSignal(bool, str, float)
    token_count_updated = pyqtSignal(int, int)

    context_changed = pyqtSignal(int, int)  # current_size, max_size

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        super().__init__()
        self._api_key = api_key
        self._model = model
        self.token_usage = TokenUsage()
        self.context_history: list[dict] = []  # list of {"source": str, "translated": str}
        self.max_context: int = 10
        self.context_enabled: bool = True
        self.system_prompt: str = (
            "You are a game translator. Translate the following {source_lang} text "
            "to {target_lang}. Return ONLY the translation, nothing else."
        )

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str):
        self._api_key = value

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    def _api_request(self, endpoint: str, data: Optional[dict] = None, method: str = "GET") -> dict:
        url = f"{API_BASE}/{endpoint}"
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}key={self._api_key}"

        headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=body, headers=headers, method=method if data is None else "POST")

        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(error_body)
                msg = err_json.get("error", {}).get("message", str(e))
            except json.JSONDecodeError:
                msg = str(e)
            raise RuntimeError(f"API Error ({e.code}): {msg}") from e
        except URLError as e:
            raise RuntimeError(f"Connection Error: {e.reason}") from e

    def fetch_models(self) -> list[dict]:
        try:
            result = self._api_request("models")
            models = []
            for m in result.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = m.get("name", "").replace("models/", "")
                    display = m.get("displayName", name)
                    models.append({"id": name, "name": display})
            self.models_fetched.emit(models)
            return models
        except Exception as e:
            self.error_occurred.emit(str(e))
            return []

    def test_connection(self) -> tuple[bool, str, float]:
        try:
            start = time.time()
            result = self._api_request(
                f"models/{self._model}:generateContent",
                {
                    "contents": [{"parts": [{"text": "Hello"}]}],
                    "generationConfig": {"maxOutputTokens": 20},
                },
            )
            elapsed = time.time() - start
            text = self._extract_text(result)
            usage = result.get("usageMetadata", {})
            inp = usage.get("promptTokenCount", 0)
            out = usage.get("candidatesTokenCount", 0)
            self.token_usage.add(inp, out)
            self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
            self.api_test_result.emit(True, f"{text} ({elapsed:.2f}s)", elapsed)
            return True, text, elapsed
        except Exception as e:
            self.api_test_result.emit(False, str(e), 0)
            return False, str(e), 0

    def set_max_context(self, n: int):
        self.max_context = max(1, min(20, n))

    def clear_context(self):
        self.context_history = []
        self.context_changed.emit(0, self.max_context)

    def get_context_size(self) -> int:
        return len(self.context_history)

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "ar") -> str:
        if not text.strip():
            return ""
        source_desc = "the source language" if source_lang == "auto" else source_lang

        # Build system prompt from template
        context_summary = ""
        if self.context_enabled and self.context_history:
            recent = self.context_history[-3:]
            context_summary = " | ".join(
                f"{item['source']} -> {item['translated']}" for item in recent
            )
        prompt = self.system_prompt.format(
            source_lang=source_desc,
            target_lang=target_lang,
            context=context_summary,
        )

        # Build contents array with conversation history
        contents = []
        if self.context_enabled:
            for item in self.context_history[-self.max_context:]:
                contents.append({"role": "user", "parts": [{"text": item["source"]}]})
                contents.append({"role": "model", "parts": [{"text": item["translated"]}]})
        contents.append({"role": "user", "parts": [{"text": text}]})

        try:
            result = self._api_request(
                f"models/{self._model}:generateContent",
                {
                    "systemInstruction": {"parts": [{"text": prompt}]},
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
                },
            )
            translated = self._extract_text(result)
            usage = result.get("usageMetadata", {})
            inp = usage.get("promptTokenCount", 0)
            out = usage.get("candidatesTokenCount", 0)
            self.token_usage.add(inp, out)
            self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)

            # Save to context history
            if self.context_enabled and translated:
                self.context_history.append({"source": text, "translated": translated})
                self.context_changed.emit(len(self.context_history), self.max_context)

            self.translation_ready.emit(translated)
            return translated
        except Exception as e:
            self.error_occurred.emit(str(e))
            return ""

    def translate_audio(self, wav_bytes: bytes, source_lang: str = "auto", target_lang: str = "ar") -> str:
        source_desc = "the detected language" if source_lang == "auto" else source_lang
        system_prompt = (
            f"You are a game translator. Listen to the audio and translate the speech from "
            f"{source_desc} to {target_lang}. Return ONLY the translation, nothing else. "
            f"If there is no speech, return an empty string."
        )
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
        try:
            result = self._api_request(
                f"models/{self._model}:generateContent",
                {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [
                        {
                            "parts": [
                                {"inlineData": {"mimeType": "audio/wav", "data": audio_b64}},
                            ]
                        }
                    ],
                    "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
                },
            )
            translated = self._extract_text(result)
            usage = result.get("usageMetadata", {})
            inp = usage.get("promptTokenCount", 0)
            out = usage.get("candidatesTokenCount", 0)
            self.token_usage.add(inp, out)
            self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
            if translated.strip():
                self.translation_ready.emit(translated)
            return translated
        except Exception as e:
            self.error_occurred.emit(str(e))
            return ""

    def count_tokens(self, text: str) -> int:
        try:
            result = self._api_request(
                f"models/{self._model}:countTokens",
                {"contents": [{"parts": [{"text": text}]}]},
            )
            return result.get("totalTokens", 0)
        except Exception:
            return 0

    def _extract_text(self, result: dict) -> str:
        candidates = result.get("candidates", [])
        if not candidates:
            return ""
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "").strip()


class TranslateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client: GeminiClient, text: str, source_lang: str, target_lang: str):
        super().__init__()
        self._client = client
        self._text = text
        self._source_lang = source_lang
        self._target_lang = target_lang

    def run(self):
        try:
            result = self._client.translate_text(self._text, self._source_lang, self._target_lang)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AudioTranslateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client: GeminiClient, wav_bytes: bytes, source_lang: str, target_lang: str):
        super().__init__()
        self._client = client
        self._wav_bytes = wav_bytes
        self._source_lang = source_lang
        self._target_lang = target_lang

    def run(self):
        try:
            result = self._client.translate_audio(self._wav_bytes, self._source_lang, self._target_lang)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FetchModelsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, client: GeminiClient):
        super().__init__()
        self._client = client

    def run(self):
        try:
            models = self._client.fetch_models()
            self.finished.emit(models)
        except Exception as e:
            self.error.emit(str(e))


class TestApiWorker(QThread):
    finished = pyqtSignal(bool, str, float)

    def __init__(self, client: GeminiClient):
        super().__init__()
        self._client = client

    def run(self):
        ok, msg, elapsed = self._client.test_connection()
        self.finished.emit(ok, msg, elapsed)
