import base64
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QThread


PROVIDERS = {
    "Google Gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta",
        "models_endpoint": "/models",
        "models_filter": lambda m: (
            "generateContent" in m.get("supportedGenerationMethods", [])
            and "gemini" in m.get("name", "").lower()
        ),
        "model_name_field": "name",
        "translate_fn": "gemini_translate",
        "key_placeholder": "AIza...",
        "fallback_models": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    },
    "ZhipuAI (GLM)": {
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "models_endpoint": "/models",
        "translate_fn": "openai_translate",
        "key_placeholder": "your-zhipuai-key",
        "static_models": [
            # --- FREE MODELS ---
            "glm-4.7-flash",       # Free - text, recommended default
            "glm-4.5-flash",       # Free - text, fast
            "glm-4.6v-flashx",     # Free - vision/OCR
            # --- PAID TEXT MODELS ---
            "glm-5",               # $1/1M input
            "glm-5-turbo",         # $1.2/1M input
            "glm-5-code",          # $1.2/1M input
            "glm-4.7",             # $0.6/1M input
            "glm-4.7-flashx",      # $0.07/1M input
            "glm-4.6",             # $0.6/1M input
            "glm-4.5",             # $0.6/1M input
            "glm-4.5-x",           # $2.2/1M input
            "glm-4.5-air",         # $0.2/1M input
            "glm-4.5-airx",        # $1.1/1M input
            "glm-4-32b-0414-128k", # $0.1/1M input
            # --- PAID VISION MODELS ---
            "glm-5v-turbo",        # $1.2/1M - vision
            "glm-4.6v",            # $0.3/1M - vision
            "glm-ocr",             # $0.03/1M - OCR specialized
        ],
        "ocr_model": "glm-4.6v-flashx",
    },
    "DeepL": {
        "api_base": "https://api-free.deepl.com/v2",
        "translate_fn": "deepl_translate",
        "key_placeholder": "your-deepl-api-key:fx",
        "static_models": ["deepl-free"],
        "note": "Free: 500K chars/month. Get key at deepl.com/pro#developer",
    },
    "GlossaAPI (Local Server)": {
        "api_base": "http://37.56.98.89:8765/v1",
        "translate_fn": "glossaapi_translate",
        "key_placeholder": "gls_...",
        "default_model": "gemma4:e4b",
        "static_models": ["gemma4:e4b"],
        "note": "Your local Glossa translation server",
    },
}


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


class AIClient(QObject):
    translation_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    models_fetched = pyqtSignal(list)
    api_test_result = pyqtSignal(bool, str, float)
    token_count_updated = pyqtSignal(int, int)
    context_changed = pyqtSignal(int, int)

    def __init__(self, provider: str = "Google Gemini", api_key: str = "", model: str = "gemini-2.0-flash"):
        super().__init__()
        self._provider = provider
        self._api_key = api_key
        self._model = model
        self.token_usage = TokenUsage()
        self.context_history: list[dict] = []
        self.max_context: int = 10
        self.context_enabled: bool = True
        self.system_prompt: str = (
            "You are a game translator. Translate the following {source_lang} text "
            "to {target_lang}. Return ONLY the translation, nothing else."
        )

        # Second provider for OCR
        self._ocr_provider: Optional[str] = None
        self._ocr_api_key: Optional[str] = None

    @property
    def provider(self) -> str:
        return self._provider

    @provider.setter
    def provider(self, value: str):
        self._provider = value

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

    def _provider_config(self) -> dict:
        return PROVIDERS.get(self._provider, PROVIDERS["Google Gemini"])

    # --- Gemini REST API ---

    def _gemini_request(self, endpoint: str, data: Optional[dict] = None) -> dict:
        config = self._provider_config()
        api_base = config["api_base"]
        url = f"{api_base}/{endpoint}"
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}key={self._api_key}"

        headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=body, headers=headers, method="POST" if data else "GET")

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

    def _gemini_extract_text(self, result: dict) -> str:
        candidates = result.get("candidates", [])
        if not candidates:
            return ""
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "").strip()

    # --- OpenAI-compatible API (GLM) ---

    def _get_openai_client(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        from openai import OpenAI
        key = api_key or self._api_key
        url = base_url or self._provider_config()["api_base"]
        return OpenAI(api_key=key, base_url=url)

    # --- Translation methods ---

    def gemini_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""
        source_desc = "the source language" if source_lang == "auto" else source_lang

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

        contents = []
        if self.context_enabled:
            for item in self.context_history[-self.max_context:]:
                contents.append({"role": "user", "parts": [{"text": item["source"]}]})
                contents.append({"role": "model", "parts": [{"text": item["translated"]}]})
        contents.append({"role": "user", "parts": [{"text": text}]})

        result = self._gemini_request(
            f"models/{self._model}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": contents,
                "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.1},
            },
        )
        translated = self._gemini_extract_text(result)
        usage = result.get("usageMetadata", {})
        inp = usage.get("promptTokenCount", 0)
        out = usage.get("candidatesTokenCount", 0)
        self.token_usage.add(inp, out)
        self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)

        if self.context_enabled and translated:
            self.context_history.append({"source": text, "translated": translated})
            self.context_changed.emit(len(self.context_history), self.max_context)

        return translated

    def openai_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""
        source_desc = "the source language" if source_lang == "auto" else source_lang

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

        messages = [{"role": "system", "content": prompt}]
        if self.context_enabled:
            for item in self.context_history[-self.max_context:]:
                messages.append({"role": "user", "content": item["source"]})
                messages.append({"role": "assistant", "content": item["translated"]})
        messages.append({"role": "user", "content": text})

        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=1000,
            stream=False,
        )
        translated = response.choices[0].message.content.strip()

        if response.usage:
            inp = response.usage.prompt_tokens
            out = response.usage.completion_tokens
            self.token_usage.add(inp, out)
            self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)

        if self.context_enabled and translated:
            self.context_history.append({"source": text, "translated": translated})
            self.context_changed.emit(len(self.context_history), self.max_context)

        return translated

    def deepl_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""

        lang_map = {
            "auto": None, "en": "EN", "ar": "AR", "ja": "JA",
            "zh": "ZH", "ko": "KO", "fr": "FR", "de": "DE",
            "es": "ES", "ru": "RU", "it": "IT", "pt": "PT-BR",
            "nl": "NL", "pl": "PL", "tr": "TR",
        }
        src = lang_map.get(source_lang.lower())
        tgt = lang_map.get(target_lang.lower(), target_lang.upper())

        import urllib.parse
        params = {"text": text, "target_lang": tgt, "auth_key": self._api_key}
        if src:
            params["source_lang"] = src

        body = urllib.parse.urlencode(params).encode("utf-8")
        req = Request(
            "https://api-free.deepl.com/v2/translate",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                translated = result["translations"][0]["text"]
                chars = len(text)
                self.token_usage.add(chars, len(translated))
                self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
                if self.context_enabled and translated:
                    self.context_history.append({"source": text, "translated": translated})
                    self.context_changed.emit(len(self.context_history), self.max_context)
                self.translation_ready.emit(translated)
                return translated
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepL Error ({e.code}): {body[:200]}") from e
        except URLError as e:
            raise RuntimeError(f"DeepL Connection Error: {e.reason}") from e

    def glossaapi_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text.strip():
            return ""

        config = self._provider_config()
        api_base = config["api_base"]

        payload = json.dumps({
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model": self._model or "gemma4:e4b",
            "context": [
                {"source": h["source"], "translated": h["translated"]}
                for h in self.context_history[-5:]
            ] if self.context_enabled else [],
        }).encode()

        req = Request(
            f"{api_base}/translate",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self._api_key,
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                translated = result.get("translated", "")
                tokens_in = result.get("tokens_used", 0) // 2
                tokens_out = result.get("tokens_used", 0) // 2
                self.token_usage.add(tokens_in, tokens_out)
                self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
                if self.context_enabled and translated:
                    self.context_history.append({"source": text, "translated": translated})
                    self.context_changed.emit(len(self.context_history), self.max_context)
                self.translation_ready.emit(translated)
                return translated
        except HTTPError as e:
            raise RuntimeError(f"GlossaAPI Error ({e.code}): {e.read().decode()[:200]}") from e
        except URLError as e:
            raise RuntimeError(f"GlossaAPI Connection Error: {e.reason}") from e

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "ar") -> str:
        config = self._provider_config()
        fn_name = config.get("translate_fn", "gemini_translate")
        try:
            translate_fn = getattr(self, fn_name)
            translated = translate_fn(text, source_lang, target_lang)
            if translated:
                self.translation_ready.emit(translated)
            return translated
        except Exception as e:
            self.error_occurred.emit(str(e))
            return ""

    def translate_audio(self, wav_bytes: bytes, source_lang: str = "auto", target_lang: str = "ar") -> str:
        source_desc = "the detected language" if source_lang == "auto" else source_lang
        audio_prompt = (
            f"You are a game translator. Listen to the audio and translate the speech from "
            f"{source_desc} to {target_lang}. Return ONLY the translation, nothing else. "
            f"If there is no speech, return an empty string."
        )
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

        config = self._provider_config()
        fn_name = config.get("translate_fn", "gemini_translate")

        try:
            if fn_name == "gemini_translate":
                result = self._gemini_request(
                    f"models/{self._model}:generateContent",
                    {
                        "systemInstruction": {"parts": [{"text": audio_prompt}]},
                        "contents": [{
                            "parts": [
                                {"inlineData": {"mimeType": "audio/wav", "data": audio_b64}},
                            ]
                        }],
                        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
                    },
                )
                translated = self._gemini_extract_text(result)
                usage = result.get("usageMetadata", {})
                inp = usage.get("promptTokenCount", 0)
                out = usage.get("candidatesTokenCount", 0)
                self.token_usage.add(inp, out)
                self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
            else:
                # GLM does not support audio natively, return empty
                translated = ""

            if translated.strip():
                self.translation_ready.emit(translated)
            return translated
        except Exception as e:
            self.error_occurred.emit(str(e))
            return ""

    # --- OCR ---

    def ocr_screenshot(self, image_bytes: bytes) -> str:
        """Use GLM-4V-Flash to extract text from screenshot."""
        b64 = base64.b64encode(image_bytes).decode()

        # Determine which provider/key to use for OCR
        ocr_key = self._ocr_api_key or self._api_key
        ocr_provider = self._ocr_provider or self._provider

        if ocr_provider == "ZhipuAI (GLM)":
            client = self._get_openai_client(
                api_key=ocr_key,
                base_url="https://open.bigmodel.cn/api/paas/v4",
            )
            response = client.chat.completions.create(
                model="glm-4.6v-flashx",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text", "text": "Extract ALL text from this image. Return ONLY the raw text, nothing else."},
                    ]
                }],
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        elif ocr_provider == "Google Gemini":
            # Use Gemini vision
            result = self._gemini_request(
                f"models/{self._model}:generateContent",
                {
                    "contents": [{
                        "parts": [
                            {"inlineData": {"mimeType": "image/png", "data": b64}},
                            {"text": "Extract ALL text from this image. Return ONLY the raw text, nothing else."},
                        ]
                    }],
                    "generationConfig": {"maxOutputTokens": 500, "temperature": 0.1},
                },
            )
            return self._gemini_extract_text(result)
        return ""

    def set_ocr_provider(self, provider: Optional[str], api_key: Optional[str] = None):
        self._ocr_provider = provider
        self._ocr_api_key = api_key

    # --- Model fetching ---

    def fetch_models(self) -> list[dict]:
        config = self._provider_config()
        try:
            if self._provider == "GlossaAPI (Local Server)":
                api_base = config["api_base"]
                req = Request(
                    f"{api_base}/models",
                    headers={"X-API-Key": self._api_key},
                )
                with urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    models = [{"id": m["id"], "name": m["name"]} for m in data.get("models", [])]
                    self.models_fetched.emit(models)
                    return models

            if "static_models" in config:
                models = [{"id": m, "name": m} for m in config["static_models"]]
                self.models_fetched.emit(models)
                return models

            result = self._gemini_request("models")
            models = []
            filter_fn = config.get("models_filter")
            for m in result.get("models", []):
                if filter_fn and not filter_fn(m):
                    continue
                name = m.get("name", "").replace("models/", "")
                display = m.get("displayName", name)
                models.append({"id": name, "name": display})
            # Sort newest first (higher version numbers first)
            models.sort(key=lambda m: m["id"], reverse=True)
            self.models_fetched.emit(models)
            return models
        except Exception as e:
            # Use fallback models if API fetch fails
            fallback = config.get("fallback_models", [])
            if fallback:
                models = [{"id": m, "name": m} for m in fallback]
                self.models_fetched.emit(models)
                return models
            self.error_occurred.emit(str(e))
            return []

    # --- Test connection ---

    def test_connection(self) -> tuple[bool, str, float]:
        config = self._provider_config()
        fn_name = config.get("translate_fn", "gemini_translate")
        try:
            start = time.time()
            if fn_name == "glossaapi_translate":
                result = self.glossaapi_translate("Hello", "en", "ar")
                elapsed = time.time() - start
                text = result or "OK"
                self.api_test_result.emit(True, f"{text} ({elapsed:.2f}s)", elapsed)
                return True, text, elapsed
            elif fn_name == "gemini_translate":
                result = self._gemini_request(
                    f"models/{self._model}:generateContent",
                    {
                        "contents": [{"parts": [{"text": "Hello"}]}],
                        "generationConfig": {"maxOutputTokens": 20},
                    },
                )
                elapsed = time.time() - start
                text = self._gemini_extract_text(result)
                usage = result.get("usageMetadata", {})
                inp = usage.get("promptTokenCount", 0)
                out = usage.get("candidatesTokenCount", 0)
                self.token_usage.add(inp, out)
                self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)
            elif fn_name == "deepl_translate":
                result = self.deepl_translate("Hello", "en", target_lang="ar")
                elapsed = time.time() - start
                text = result
            else:
                client = self._get_openai_client()
                response = client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=20,
                    stream=False,
                )
                elapsed = time.time() - start
                text = response.choices[0].message.content.strip()
                if response.usage:
                    self.token_usage.add(response.usage.prompt_tokens, response.usage.completion_tokens)
                    self.token_count_updated.emit(self.token_usage.total_input, self.token_usage.total_output)

            self.api_test_result.emit(True, f"{text} ({elapsed:.2f}s)", elapsed)
            return True, text, elapsed
        except Exception as e:
            self.api_test_result.emit(False, str(e), 0)
            return False, str(e), 0

    # --- Token counting ---

    def count_tokens(self, text: str) -> int:
        config = self._provider_config()
        fn_name = config.get("translate_fn", "gemini_translate")
        if fn_name == "gemini_translate":
            try:
                result = self._gemini_request(
                    f"models/{self._model}:countTokens",
                    {"contents": [{"parts": [{"text": text}]}]},
                )
                return result.get("totalTokens", 0)
            except Exception:
                return 0
        return 0

    # --- Context ---

    def set_max_context(self, n: int):
        self.max_context = max(1, min(20, n))

    def clear_context(self):
        self.context_history = []
        self.context_changed.emit(0, self.max_context)

    def get_context_size(self) -> int:
        return len(self.context_history)


# --- Worker threads ---

class TranslateWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client: AIClient, text: str, source_lang: str, target_lang: str):
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

    def __init__(self, client: AIClient, wav_bytes: bytes, source_lang: str, target_lang: str):
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

    def __init__(self, client: AIClient):
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

    def __init__(self, client: AIClient):
        super().__init__()
        self._client = client

    def run(self):
        ok, msg, elapsed = self._client.test_connection()
        self.finished.emit(ok, msg, elapsed)
