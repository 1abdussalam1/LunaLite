from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    QRectF,
    pyqtSignal,
    pyqtProperty,
    QSize,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPainter,
    QPen,
    QBrush,
)
from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QSlider,
    QCheckBox,
    QFrame,
    QColorDialog,
    QDialogButtonBox,
    QApplication,
    QTextEdit,
    QMessageBox,
    QFileDialog,
)

from src.utils.i18n import t, is_rtl, load_language, available_languages, on_language_changed
from src.core.ai_client import AIClient, FetchModelsWorker, TestApiWorker, PROVIDERS
from src.utils.theme import apply_theme


LANGUAGES = [
    ("auto", "Auto Detect"),
    ("ja", "Japanese"),
    ("zh", "Chinese"),
    ("ko", "Korean"),
    ("en", "English"),
    ("ar", "Arabic"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("ru", "Russian"),
    ("pt", "Portuguese"),
]

DARK_BG = "#171717"
DARK_PANEL = "#1e1e1e"
DARK_ACCENT = "#0f3460"
DARK_HIGHLIGHT = "#e94560"
TEXT_COLOR = "#e0e0e0"
TEXT_LIGHT = "#ffffff"

DEFAULT_SYSTEM_PROMPT = (
    "You are a game translator. Translate the following {source_lang} text "
    "to {target_lang}. Return ONLY the translation, nothing else."
)

INPUT_RATE_PER_MILLION = 0.075
OUTPUT_RATE_PER_MILLION = 0.30


class DarkLightToggle(QWidget):
    """Custom animated dark/light mode toggle switch."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._is_dark = True
        self._handle_position = 0.0

        self._anim = QPropertyAnimation(self, b"handlePosition")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_handle_position(self) -> float:
        return self._handle_position

    def set_handle_position(self, value: float):
        self._handle_position = value
        self.update()

    handlePosition = pyqtProperty(float, get_handle_position, set_handle_position)

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def set_dark(self, dark: bool, animate: bool = True):
        self._is_dark = dark
        target = 0.0 if dark else 1.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._handle_position)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._handle_position = target
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dark = not self._is_dark
            target = 0.0 if self._is_dark else 1.0
            self._anim.stop()
            self._anim.setStartValue(self._handle_position)
            self._anim.setEndValue(target)
            self._anim.start()
            self.clicked.emit()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = h / 2.0

        dark_bg = QColor("#20262c")
        light_bg = QColor("#5494de")
        t_val = self._handle_position
        bg_r = dark_bg.red() + (light_bg.red() - dark_bg.red()) * t_val
        bg_g = dark_bg.green() + (light_bg.green() - dark_bg.green()) * t_val
        bg_b = dark_bg.blue() + (light_bg.blue() - dark_bg.blue()) * t_val
        bg_color = QColor(int(bg_r), int(bg_g), int(bg_b))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)

        handle_diameter = h - 4
        handle_x = 2 + self._handle_position * (w - handle_diameter - 4)
        handle_y = 2.0

        painter.setBrush(QBrush(QColor(TEXT_LIGHT)))
        painter.drawEllipse(QRectF(handle_x, handle_y, handle_diameter, handle_diameter))

        icon_font = QFont()
        icon_font.setPixelSize(14)
        painter.setFont(icon_font)

        if self._handle_position < 0.5:
            painter.setPen(QPen(QColor("#20262c")))
            icon_rect = QRectF(handle_x, handle_y, handle_diameter, handle_diameter)
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "\U0001f319")
        else:
            painter.setPen(QPen(QColor("#5494de")))
            icon_rect = QRectF(handle_x, handle_y, handle_diameter, handle_diameter)
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "\u2600\ufe0f")

        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(60, 30)


class SettingsWindow(QDialog):
    """Glossa settings dialog with API, Translation, Appearance, and About tabs."""

    settings_saved = pyqtSignal()
    theme_changed = pyqtSignal(str)

    def __init__(self, config_manager, ai_client, overlay=None, parent=None):
        super().__init__(parent)
        self._config = config_manager
        self._ai = ai_client
        self._overlay = overlay

        self._fetch_worker = None
        self._test_worker = None

        self._font_color = self._config.get("overlay.font_color", "#ffffff")
        self._bg_color = self._config.get("overlay.bg_color", "#171717")

        self._setup_window()
        self._apply_direction()
        self._build_ui()
        self._apply_stylesheet()
        self._load_current_settings()

    def _setup_window(self):
        self.setWindowTitle(t("settings", "Settings") + " - Glossa")
        self.setMinimumSize(600, 500)

    def _apply_direction(self):
        if is_rtl():
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_api_tab(), t("tab_api", "API Settings"))
        self._tabs.addTab(self._create_translation_tab(), t("tab_translation", "Translation"))
        self._tabs.addTab(self._create_appearance_tab(), t("tab_appearance", "Appearance"))
        self._tabs.addTab(self._create_about_tab(), t("tab_about", "About"))
        main_layout.addWidget(self._tabs, 1)

        button_box = QDialogButtonBox()
        self._save_btn = button_box.addButton(t("btn_save", "Save"), QDialogButtonBox.ButtonRole.AcceptRole)
        self._cancel_btn = button_box.addButton(t("btn_cancel", "Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self._on_cancel)
        main_layout.addWidget(button_box)

    # -------------------------------------------------------------------------
    # Tab 1: API Settings
    # -------------------------------------------------------------------------
    def _create_api_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        # Provider dropdown
        self._provider_combo = QComboBox()
        for name in PROVIDERS:
            self._provider_combo.addItem(name)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form.addRow(QLabel(t("provider", "Provider:")), self._provider_combo)

        # Server URL (for GlossaAPI)
        self._server_url_label = QLabel(t("label_server_url", "Server URL:"))
        self._server_url_input = QLineEdit()
        self._server_url_input.setPlaceholderText("http://localhost:8765/v1")
        self._server_url_container = QWidget()
        server_url_layout = QHBoxLayout(self._server_url_container)
        server_url_layout.setContentsMargins(0, 0, 0, 0)
        server_url_layout.addWidget(self._server_url_input)
        form.addRow(self._server_url_label, self._server_url_container)
        self._server_url_label.setVisible(False)
        self._server_url_container.setVisible(False)

        # API key
        api_key_layout = QHBoxLayout()
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText(t("placeholder_api_key", "Enter your API key"))
        api_key_layout.addWidget(self._api_key_input, 1)

        self._toggle_key_btn = QPushButton(t("btn_show", "Show"))
        self._toggle_key_btn.setFixedWidth(60)
        self._toggle_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self._toggle_key_btn)

        form.addRow(QLabel(t("label_api_key", "API Key:")), api_key_layout)

        # Model
        model_layout = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(250)
        self._model_combo.setEditable(True)
        model_layout.addWidget(self._model_combo, 1)

        self._fetch_models_btn = QPushButton(t("btn_fetch_models", "Fetch Models"))
        self._fetch_models_btn.clicked.connect(self._on_fetch_models)
        model_layout.addWidget(self._fetch_models_btn)

        form.addRow(QLabel(t("label_model", "Model:")), model_layout)

        layout.addLayout(form)

        # Test API
        test_layout = QHBoxLayout()
        self._test_api_btn = QPushButton(t("btn_test_api", "Test API Connection"))
        self._test_api_btn.clicked.connect(self._on_test_api)
        test_layout.addWidget(self._test_api_btn)

        self._test_result_label = QLabel("")
        self._test_result_label.setWordWrap(True)
        test_layout.addWidget(self._test_result_label, 1)
        layout.addLayout(test_layout)

        # Provider note (for DeepL etc.)
        self._provider_note_label = QLabel("")
        self._provider_note_label.setWordWrap(True)
        self._provider_note_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-size: 12px;")
        self._provider_note_label.setVisible(False)
        layout.addWidget(self._provider_note_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator)

        # Token usage
        self._token_usage_label = QLabel(t("label_token_usage", "Tokens used this session: 0 input / 0 output"))
        layout.addWidget(self._token_usage_label)

        self._token_cost_label = QLabel(t("label_token_cost", "Estimated cost: $0.00"))
        layout.addWidget(self._token_cost_label)

        self._update_token_display()

        # Second provider for OCR
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator2)

        ocr_provider_label = QLabel(t("second_provider", "Second Provider (OCR):"))
        ocr_provider_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-weight: bold;")
        layout.addWidget(ocr_provider_label)

        ocr_form = QFormLayout()

        self._ocr_provider_combo = QComboBox()
        self._ocr_provider_combo.addItem(t("same_as_main", "Same as Main"), "")
        for name in PROVIDERS:
            self._ocr_provider_combo.addItem(name, name)
        ocr_form.addRow(QLabel(t("provider", "Provider:")), self._ocr_provider_combo)

        self._ocr_api_key_input = QLineEdit()
        self._ocr_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._ocr_api_key_input.setPlaceholderText(t("placeholder_api_key", "Enter your API key"))
        ocr_form.addRow(QLabel(t("label_api_key", "API Key:")), self._ocr_api_key_input)

        layout.addLayout(ocr_form)

        layout.addStretch(1)
        return tab

    def _on_provider_changed(self, provider_name: str):
        config = PROVIDERS.get(provider_name, {})
        placeholder = config.get("key_placeholder", "")
        self._api_key_input.setPlaceholderText(placeholder)

        # Show/hide server URL field for GlossaAPI
        is_glossaapi = provider_name == "GlossaAPI (Local Server)"
        self._server_url_label.setVisible(is_glossaapi)
        self._server_url_container.setVisible(is_glossaapi)

        # Show/hide note
        note = config.get("note", "")
        if note:
            self._provider_note_label.setText(f"{t('provider_note', 'Note')}: {note}")
            self._provider_note_label.setVisible(True)
        else:
            self._provider_note_label.setVisible(False)

        # Hide system prompt & context memory for non-AI providers (DeepL)
        is_deepl = config.get("translate_fn") == "deepl_translate"
        self._system_prompt_container.setVisible(not is_deepl)
        self._context_memory_container.setVisible(not is_deepl)

        # Auto-populate models for static_models providers
        if "static_models" in config and config["static_models"]:
            self._model_combo.clear()
            for m in config["static_models"]:
                self._model_combo.addItem(m, m)
            # Auto-select default model
            default = config.get("default_model", config["static_models"][0])
            idx = self._model_combo.findData(default)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)

    def _toggle_api_key_visibility(self):
        if self._api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_key_btn.setText(t("btn_hide", "Hide"))
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_key_btn.setText(t("btn_show", "Show"))

    def _on_fetch_models(self):
        api_key = self._api_key_input.text().strip()
        if not api_key:
            self._test_result_label.setText(t("error_no_key", "Please enter an API key first."))
            return

        self._ai.api_key = api_key
        self._ai.provider = self._provider_combo.currentText()
        self._fetch_models_btn.setEnabled(False)
        self._fetch_models_btn.setText(t("btn_fetching", "Fetching..."))

        self._fetch_worker = FetchModelsWorker(self._ai)
        self._fetch_worker.finished.connect(self._on_models_fetched)
        self._fetch_worker.error.connect(self._on_models_fetch_error)
        self._fetch_worker.start()

    def _on_models_fetched(self, models: list):
        self._fetch_models_btn.setEnabled(True)
        self._fetch_models_btn.setText(t("btn_fetch_models", "Fetch Models"))

        current_text = self._model_combo.currentText()
        self._model_combo.clear()
        for m in models:
            self._model_combo.addItem(m["name"], m["id"])

        if current_text:
            idx = self._model_combo.findData(current_text)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
            else:
                idx = self._model_combo.findText(current_text, Qt.MatchFlag.MatchContains)
                if idx >= 0:
                    self._model_combo.setCurrentIndex(idx)
                else:
                    self._model_combo.setEditText(current_text)

        self._fetch_worker = None

    def _on_models_fetch_error(self, error_msg: str):
        self._fetch_models_btn.setEnabled(True)
        self._fetch_models_btn.setText(t("btn_fetch_models", "Fetch Models"))
        self._test_result_label.setText(f"\u274c {error_msg}")
        self._fetch_worker = None

    def _on_test_api(self):
        api_key = self._api_key_input.text().strip()
        if not api_key:
            self._test_result_label.setText(t("error_no_key", "Please enter an API key first."))
            return

        self._ai.api_key = api_key
        self._ai.provider = self._provider_combo.currentText()
        model_data = self._model_combo.currentData()
        model_text = self._model_combo.currentText()
        selected_model = model_data if model_data else model_text
        if selected_model:
            self._ai.model = selected_model

        self._test_api_btn.setEnabled(False)
        self._test_api_btn.setText(t("btn_testing", "Testing..."))
        self._test_result_label.setText("")

        self._test_worker = TestApiWorker(self._ai)
        self._test_worker.finished.connect(self._on_test_result)
        self._test_worker.start()

    def _on_test_result(self, success: bool, message: str, elapsed: float):
        self._test_api_btn.setEnabled(True)
        self._test_api_btn.setText(t("btn_test_api", "Test API Connection"))

        if success:
            self._test_result_label.setText(
                f"\u2705 {t('test_working', 'Working')} - {elapsed:.2f}s"
            )
        else:
            if "429" in str(message) or "quota" in str(message).lower():
                msg = "API quota exceeded."
            else:
                msg = str(message)[:200]
            self._test_result_label.setText(f"\u274c {t('test_error', 'Error')}: {msg}")

        self._update_token_display()
        self._test_worker = None

    def _update_token_display(self):
        inp = self._ai.token_usage.total_input
        out = self._ai.token_usage.total_output
        self._token_usage_label.setText(
            t("label_token_usage_fmt", "Tokens used this session: {inp} input / {out} output").format(
                inp=inp, out=out
            )
            if "{inp}" in t("label_token_usage_fmt", "Tokens used this session: {inp} input / {out} output")
            else f"Tokens used this session: {inp} input / {out} output"
        )
        input_cost = (inp / 1_000_000) * INPUT_RATE_PER_MILLION
        output_cost = (out / 1_000_000) * OUTPUT_RATE_PER_MILLION
        total_cost = input_cost + output_cost
        self._token_cost_label.setText(
            t("label_estimated_cost", "Estimated cost: ${cost}").format(cost=f"{total_cost:.6f}")
            if "{cost}" in t("label_estimated_cost", "Estimated cost: ${cost}")
            else f"Estimated cost: ${total_cost:.6f}"
        )

    # -------------------------------------------------------------------------
    # Tab 2: Translation
    # -------------------------------------------------------------------------
    def _create_translation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self._source_lang_combo = QComboBox()
        for code, name in LANGUAGES:
            self._source_lang_combo.addItem(t(f"lang_{code}", name), code)
        form.addRow(QLabel(t("label_source_lang", "Source Language:")), self._source_lang_combo)

        target_languages = [(code, name) for code, name in LANGUAGES if code != "auto"]
        self._target_lang_combo = QComboBox()
        for code, name in target_languages:
            self._target_lang_combo.addItem(t(f"lang_{code}", name), code)
        form.addRow(QLabel(t("label_target_lang", "Target Language:")), self._target_lang_combo)

        layout.addLayout(form)

        # --- Source checkboxes ---
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator1)

        sources_label = QLabel(t("label_translation_mode", "Translation Sources:"))
        sources_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-weight: bold;")
        layout.addWidget(sources_label)

        self._clipboard_checkbox = QCheckBox(t("clipboard_mode", "Clipboard"))
        layout.addWidget(self._clipboard_checkbox)

        self._hook_checkbox = QCheckBox(t("hook_mode", "Hook (Textractor Named Pipe)"))
        layout.addWidget(self._hook_checkbox)

        self._ocr_checkbox = QCheckBox(t("ocr_mode", "OCR (Screen Capture)"))
        layout.addWidget(self._ocr_checkbox)

        # OCR sub-options
        ocr_options = QWidget()
        ocr_layout = QFormLayout(ocr_options)
        ocr_layout.setContentsMargins(20, 0, 0, 0)

        self._ocr_interval_spin = QSpinBox()
        self._ocr_interval_spin.setRange(1, 10)
        self._ocr_interval_spin.setValue(2)
        self._ocr_interval_spin.setSuffix("s")
        ocr_layout.addRow(QLabel(t("ocr_interval", "OCR Interval:")), self._ocr_interval_spin)

        layout.addWidget(ocr_options)

        self._audio_checkbox = QCheckBox(t("audio_mode", "Audio (Loopback)"))
        layout.addWidget(self._audio_checkbox)

        # Audio sub-options
        audio_options = QWidget()
        audio_layout = QFormLayout(audio_options)
        audio_layout.setContentsMargins(20, 0, 0, 0)

        self._audio_device_combo = QComboBox()
        self._audio_device_combo.addItem(t("audio_default", "Default Loopback Device"), -1)
        audio_layout.addRow(QLabel(t("label_audio_device", "Audio Device:")), self._audio_device_combo)

        layout.addWidget(audio_options)
        self._populate_audio_devices()

        # Hook instructions
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator2)

        hook_label = QLabel(t("label_hook_setup", "Hook Setup (Textractor):"))
        hook_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-weight: bold;")
        layout.addWidget(hook_label)

        hook_instructions = QLabel(
            "Hook mode uses Named Pipe to receive text from Textractor.\n"
            "1. Install Textractor from the link below\n"
            "2. Add Extension: NamedPipeOutput.xdll (pipe name: Glossa)\n"
            "3. Open game with Textractor, attach process\n"
            "4. Glossa will auto-receive the text"
        )
        hook_instructions.setWordWrap(True)
        hook_instructions.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 11px; padding: 4px 0;")
        layout.addWidget(hook_instructions)

        self._download_textractor_btn = QPushButton(t("download_textractor", "Download Textractor"))
        self._download_textractor_btn.setStyleSheet(f"background-color: {DARK_ACCENT};")
        self._download_textractor_btn.clicked.connect(self._open_textractor_url)
        layout.addWidget(self._download_textractor_btn)

        # Game executable path
        separator2b = QFrame()
        separator2b.setFrameShape(QFrame.Shape.HLine)
        separator2b.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator2b)

        text_options_label = QLabel(t("label_text_options", "Text Mode Options:"))
        text_options_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-weight: bold;")
        layout.addWidget(text_options_label)

        exe_form = QFormLayout()
        exe_layout = QHBoxLayout()
        self._exe_path_edit = QLineEdit()
        self._exe_path_edit.setPlaceholderText("C:\\Games\\MyGame\\game.exe")
        exe_layout.addWidget(self._exe_path_edit, 1)
        self._exe_browse_btn = QPushButton(t("browse", "Browse..."))
        self._exe_browse_btn.clicked.connect(self._browse_exe)
        exe_layout.addWidget(self._exe_browse_btn)
        exe_form.addRow(QLabel(t("game_executable", "Game Executable:")), exe_layout)
        layout.addLayout(exe_form)

        self._inject_btn = QPushButton(t("inject_hook", "Inject Hook"))
        self._inject_btn.setStyleSheet("background-color: #0f3460;")
        self._inject_btn.clicked.connect(self._on_inject_hook)
        layout.addWidget(self._inject_btn)

        # UI language
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setStyleSheet(f"color: {DARK_ACCENT};")
        layout.addWidget(separator3)

        ui_lang_form = QFormLayout()
        self._ui_lang_combo = QComboBox()
        for lang in available_languages():
            self._ui_lang_combo.addItem(lang["name"], lang["code"])
        ui_lang_form.addRow(QLabel(t("label_ui_language", "UI Language:")), self._ui_lang_combo)
        layout.addLayout(ui_lang_form)

        # System Prompt (container for hide/show with DeepL)
        self._system_prompt_container = QWidget()
        sp_layout = QVBoxLayout(self._system_prompt_container)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(6)

        separator4 = QFrame()
        separator4.setFrameShape(QFrame.Shape.HLine)
        separator4.setStyleSheet(f"color: {DARK_ACCENT};")
        sp_layout.addWidget(separator4)

        prompt_label = QLabel(t("system_prompt", "System Prompt"))
        prompt_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-weight: bold;")
        sp_layout.addWidget(prompt_label)

        self._system_prompt_edit = QTextEdit()
        self._system_prompt_edit.setFixedHeight(100)
        self._system_prompt_edit.setPlaceholderText(t("system_prompt", "System Prompt"))
        sp_layout.addWidget(self._system_prompt_edit)

        prompt_btn_layout = QHBoxLayout()
        self._reset_prompt_btn = QPushButton(t("reset_prompt", "Reset to Default"))
        self._reset_prompt_btn.clicked.connect(self._on_reset_prompt)
        prompt_btn_layout.addWidget(self._reset_prompt_btn)
        prompt_btn_layout.addStretch(1)
        sp_layout.addLayout(prompt_btn_layout)

        prompt_hint = QLabel(t("prompt_hint", "Variables: {source_lang}, {target_lang}, {context}"))
        prompt_hint.setStyleSheet("color: #888888; font-size: 11px;")
        sp_layout.addWidget(prompt_hint)

        layout.addWidget(self._system_prompt_container)

        # Context Memory (container for hide/show with DeepL)
        self._context_memory_container = QWidget()
        cm_layout = QVBoxLayout(self._context_memory_container)
        cm_layout.setContentsMargins(0, 0, 0, 0)
        cm_layout.setSpacing(6)

        separator5 = QFrame()
        separator5.setFrameShape(QFrame.Shape.HLine)
        separator5.setStyleSheet(f"color: {DARK_ACCENT};")
        cm_layout.addWidget(separator5)

        self._context_memory_checkbox = QCheckBox(t("context_memory", "Enable Context Memory"))
        cm_layout.addWidget(self._context_memory_checkbox)

        context_size_layout = QHBoxLayout()
        context_size_label = QLabel(t("context_size", "Context Size"))
        context_size_layout.addWidget(context_size_label)
        self._context_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._context_size_slider.setRange(1, 20)
        self._context_size_slider.setValue(10)
        self._context_size_slider.valueChanged.connect(self._on_context_size_changed)
        context_size_layout.addWidget(self._context_size_slider, 1)
        self._context_size_value_label = QLabel("10")
        self._context_size_value_label.setFixedWidth(24)
        context_size_layout.addWidget(self._context_size_value_label)
        cm_layout.addLayout(context_size_layout)

        self._clear_context_btn = QPushButton(t("clear_context", "Clear Context"))
        self._clear_context_btn.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: #ffffff; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #e74c3c; }"
        )
        self._clear_context_btn.clicked.connect(self._on_clear_context)
        cm_layout.addWidget(self._clear_context_btn)

        layout.addWidget(self._context_memory_container)

        layout.addStretch(1)
        return tab

    def _populate_audio_devices(self):
        try:
            from src.core.audio_capture import get_loopback_devices
            devices = get_loopback_devices()
            for name, index in devices:
                self._audio_device_combo.addItem(name, index)
        except Exception:
            self._audio_device_combo.addItem(t("audio_unavailable", "Audio devices unavailable"), -1)

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("select_game_exe", "Select Game Executable"), "", "Executable (*.exe)"
        )
        if path:
            self._exe_path_edit.setText(path)
            self._config.set("game_exe_path", path)

    def _open_textractor_url(self):
        import webbrowser
        webbrowser.open("https://github.com/Artikash/Textractor/releases")

    def _on_inject_hook(self):
        exe_path = self._exe_path_edit.text().strip()
        if not exe_path:
            QMessageBox.warning(self, t("error", "Error"), t("select_game_exe", "Select Game Executable"))
            return
        try:
            from src.core.text_extractor import inject_hook
            inject_hook(exe_path)
        except Exception as e:
            QMessageBox.warning(self, t("error", "Error"), str(e))

    def _on_reset_prompt(self):
        self._system_prompt_edit.setPlainText(DEFAULT_SYSTEM_PROMPT)

    def _on_context_size_changed(self, value: int):
        self._context_size_value_label.setText(str(value))

    def _on_clear_context(self):
        reply = QMessageBox.question(
            self,
            t("clear_context", "Clear Context"),
            t("clear_context_confirm", "Clear translation context? This will reset the conversation memory."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._ai.clear_context()

    # -------------------------------------------------------------------------
    # Tab 3: Appearance
    # -------------------------------------------------------------------------
    def _create_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        theme_layout = QHBoxLayout()
        theme_label = QLabel(t("label_theme", "Theme:"))
        theme_layout.addWidget(theme_label)

        self._dark_label = QLabel(t("label_dark", "Dark"))
        self._dark_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")
        theme_layout.addWidget(self._dark_label)

        self._theme_toggle = DarkLightToggle()
        self._theme_toggle.clicked.connect(self._on_theme_toggled)
        theme_layout.addWidget(self._theme_toggle)

        self._light_label = QLabel(t("label_light", "Light"))
        self._light_label.setStyleSheet(f"color: {TEXT_LIGHT};")
        theme_layout.addWidget(self._light_label)

        theme_layout.addStretch(1)
        layout.addLayout(theme_layout)

        form = QFormLayout()
        form.setSpacing(8)

        self._font_family_combo = QComboBox()
        families = QFontDatabase.families()
        for family in families:
            self._font_family_combo.addItem(family)
        self._font_family_combo.currentTextChanged.connect(self._update_preview)
        form.addRow(QLabel(t("label_font_family", "Font Family:")), self._font_family_combo)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 72)
        self._font_size_spin.setValue(14)
        self._font_size_spin.valueChanged.connect(self._update_preview)
        form.addRow(QLabel(t("label_font_size", "Font Size:")), self._font_size_spin)

        font_color_layout = QHBoxLayout()
        self._font_color_btn = QPushButton("")
        self._font_color_btn.setFixedSize(40, 25)
        self._font_color_btn.clicked.connect(self._pick_font_color)
        font_color_layout.addWidget(self._font_color_btn)
        self._font_color_label = QLabel(self._font_color)
        font_color_layout.addWidget(self._font_color_label)
        font_color_layout.addStretch(1)
        form.addRow(QLabel(t("label_font_color", "Font Color:")), font_color_layout)

        bg_color_layout = QHBoxLayout()
        self._bg_color_btn = QPushButton("")
        self._bg_color_btn.setFixedSize(40, 25)
        self._bg_color_btn.clicked.connect(self._pick_bg_color)
        bg_color_layout.addWidget(self._bg_color_btn)
        self._bg_color_label = QLabel(self._bg_color)
        bg_color_layout.addWidget(self._bg_color_label)
        bg_color_layout.addStretch(1)
        form.addRow(QLabel(t("label_bg_color", "Background Color:")), bg_color_layout)

        self._bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._bg_opacity_slider.setRange(0, 100)
        self._bg_opacity_slider.setValue(80)
        self._bg_opacity_slider.valueChanged.connect(self._update_preview)
        self._bg_opacity_value_label = QLabel("80%")
        bg_opacity_layout = QHBoxLayout()
        bg_opacity_layout.addWidget(self._bg_opacity_slider, 1)
        bg_opacity_layout.addWidget(self._bg_opacity_value_label)
        form.addRow(QLabel(t("bg_opacity", "Background Opacity:")), bg_opacity_layout)

        self._window_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._window_opacity_slider.setRange(10, 100)
        self._window_opacity_slider.setValue(85)
        self._window_opacity_slider.valueChanged.connect(self._update_preview)
        self._window_opacity_value_label = QLabel("85%")
        window_opacity_layout = QHBoxLayout()
        window_opacity_layout.addWidget(self._window_opacity_slider, 1)
        window_opacity_layout.addWidget(self._window_opacity_value_label)
        form.addRow(QLabel(t("label_window_opacity", "Window Opacity:")), window_opacity_layout)

        layout.addLayout(form)

        preview_label = QLabel(t("label_preview", "Preview:"))
        preview_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")
        layout.addWidget(preview_label)

        self._preview_frame = QFrame()
        self._preview_frame.setMinimumHeight(80)
        self._preview_frame.setFrameShape(QFrame.Shape.NoFrame)
        preview_inner_layout = QVBoxLayout(self._preview_frame)
        preview_inner_layout.setContentsMargins(12, 8, 12, 10)
        preview_inner_layout.setSpacing(4)

        self._preview_branding = QLabel("\U0001f310 Glossa")
        self._preview_branding.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 9px; background: transparent;")
        self._preview_branding.setFixedHeight(16)
        preview_inner_layout.addWidget(self._preview_branding)

        self._preview_text = QLabel(t("preview_sample", "This is a preview of the overlay text."))
        self._preview_text.setWordWrap(True)
        preview_inner_layout.addWidget(self._preview_text, 1)

        layout.addWidget(self._preview_frame)

        self._update_color_buttons()

        layout.addStretch(1)
        return tab

    def _on_theme_toggled(self):
        is_dark = self._theme_toggle.is_dark
        if is_dark:
            self._dark_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")
            self._light_label.setStyleSheet(f"color: {TEXT_LIGHT};")
        else:
            self._dark_label.setStyleSheet(f"color: {TEXT_LIGHT};")
            self._light_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")
        apply_theme(is_dark)
        theme_str = "dark" if is_dark else "light"
        self._config.set("theme", theme_str)
        self.theme_changed.emit(theme_str)

    def _pick_font_color(self):
        color = QColorDialog.getColor(QColor(self._font_color), self, t("title_font_color", "Select Font Color"))
        if color.isValid():
            self._font_color = color.name()
            self._font_color_label.setText(self._font_color)
            self._update_color_buttons()
            self._update_preview()
            if self._overlay:
                self._overlay.set_font_color(self._font_color)

    def _pick_bg_color(self):
        color = QColorDialog.getColor(QColor(self._bg_color), self, t("title_bg_color", "Select Background Color"))
        if color.isValid():
            self._bg_color = color.name()
            self._bg_color_label.setText(self._bg_color)
            self._update_color_buttons()
            self._update_preview()
            if self._overlay:
                self._overlay.set_bg_color(self._bg_color)

    def _update_color_buttons(self):
        self._font_color_btn.setStyleSheet(
            f"background-color: {self._font_color}; border: 1px solid #555; border-radius: 4px;"
        )
        self._bg_color_btn.setStyleSheet(
            f"background-color: {self._bg_color}; border: 1px solid #555; border-radius: 4px;"
        )

    def _update_preview(self):
        font_family = self._font_family_combo.currentText()
        font_size = self._font_size_spin.value()
        bg_opacity_pct = self._bg_opacity_slider.value()
        window_opacity_pct = self._window_opacity_slider.value()

        self._bg_opacity_value_label.setText(f"{bg_opacity_pct}%")
        self._window_opacity_value_label.setText(f"{window_opacity_pct}%")

        bg_alpha = int(bg_opacity_pct / 100.0 * 255)
        bg_qcolor = QColor(self._bg_color)
        bg_r, bg_g, bg_b = bg_qcolor.red(), bg_qcolor.green(), bg_qcolor.blue()

        self._preview_frame.setStyleSheet(
            f"background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_alpha}); "
            f"border-radius: 10px;"
        )

        self._preview_text.setStyleSheet(
            f"color: {self._font_color}; "
            f"font-family: '{font_family}'; "
            f"font-size: {font_size}px; "
            f"background: transparent; "
            f"padding: 4px;"
        )

        if self._overlay:
            overall_opacity = window_opacity_pct / 100.0
            self._overlay.set_font_size(font_size)
            self._overlay.set_opacity(overall_opacity)
            self._overlay.update_appearance(
                font_family, font_size, self._font_color,
                self._bg_color, bg_opacity_pct / 100.0, overall_opacity
            )

    # -------------------------------------------------------------------------
    # Tab 4: About
    # -------------------------------------------------------------------------
    def _create_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Glossa")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {DARK_HIGHLIGHT};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version_label = QLabel(t("label_version", "Version: 1.0.0"))
        version_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 14px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacing(10)

        desc_en = QLabel(t("about_desc", "Glossa is a real-time game translation tool powered by AI."))
        desc_en.setWordWrap(True)
        desc_en.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 13px;")
        desc_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_en)

        desc_ar = QLabel(
            "\u063a\u0644\u0648\u0633\u0627 \u0647\u064a "
            "\u0623\u062f\u0627\u0629 \u062a\u0631\u062c\u0645\u0629 "
            "\u0623\u0644\u0639\u0627\u0628 \u0641\u0648\u0631\u064a\u0629 "
            "\u0645\u062f\u0639\u0648\u0645\u0629 \u0628\u0627\u0644\u0630\u0643\u0627\u0621 "
            "\u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a."
        )
        desc_ar.setWordWrap(True)
        desc_ar.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 13px;")
        desc_ar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_ar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(desc_ar)

        layout.addSpacing(10)

        github_label = QLabel(
            f'<a href="https://github.com/1abdussalam1/LunaLite" style="color: {DARK_HIGHLIGHT};">'
            f'{t("label_github", "GitHub Repository")}</a>'
        )
        github_label.setOpenExternalLinks(True)
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_label.setStyleSheet(f"color: {DARK_HIGHLIGHT}; font-size: 13px;")
        layout.addWidget(github_label)

        layout.addStretch(1)
        return tab

    # -------------------------------------------------------------------------
    # Load / Save
    # -------------------------------------------------------------------------
    def _load_current_settings(self):
        # Provider
        provider = self._config.get("provider", "Google Gemini")
        idx = self._provider_combo.findText(provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)

        self._api_key_input.setText(self._config.get("api_key", ""))

        # GlossaAPI server URL
        glossaapi_url = self._config.get("glossaapi_url", "http://localhost:8765/v1")
        self._server_url_input.setText(glossaapi_url)

        model = self._config.get("model", "gemini-2.0-flash")
        idx = self._model_combo.findData(model)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setEditText(model)

        source = self._config.get("source_lang", "auto")
        idx = self._source_lang_combo.findData(source)
        if idx >= 0:
            self._source_lang_combo.setCurrentIndex(idx)

        target = self._config.get("target_lang", "ar")
        idx = self._target_lang_combo.findData(target)
        if idx >= 0:
            self._target_lang_combo.setCurrentIndex(idx)

        # Source checkboxes
        self._clipboard_checkbox.setChecked(self._config.get("clipboard_enabled", True))
        self._hook_checkbox.setChecked(self._config.get("hook_enabled", False))
        self._ocr_checkbox.setChecked(self._config.get("ocr_enabled", False))
        self._audio_checkbox.setChecked(self._config.get("audio_enabled", False))

        # OCR interval
        self._ocr_interval_spin.setValue(int(self._config.get("ocr_interval", 2)))

        # Audio device
        audio_device = self._config.get("audio_device", -1)
        idx = self._audio_device_combo.findData(audio_device)
        if idx >= 0:
            self._audio_device_combo.setCurrentIndex(idx)

        # OCR provider
        ocr_provider = self._config.get("ocr_provider", "")
        idx = self._ocr_provider_combo.findData(ocr_provider)
        if idx >= 0:
            self._ocr_provider_combo.setCurrentIndex(idx)
        self._ocr_api_key_input.setText(self._config.get("ocr_api_key", ""))

        # UI language
        ui_lang = self._config.get("ui_language", "en")
        idx = self._ui_lang_combo.findData(ui_lang)
        if idx >= 0:
            self._ui_lang_combo.setCurrentIndex(idx)

        # Theme
        theme = self._config.get("theme", "dark")
        self._theme_toggle.set_dark(theme == "dark", animate=False)
        if theme == "dark":
            self._dark_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")
            self._light_label.setStyleSheet(f"color: {TEXT_LIGHT};")
        else:
            self._dark_label.setStyleSheet(f"color: {TEXT_LIGHT};")
            self._light_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")

        # Overlay appearance
        font_family = self._config.get("overlay.font_family", "Segoe UI")
        idx = self._font_family_combo.findText(font_family, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            self._font_family_combo.setCurrentIndex(idx)

        font_size = self._config.get("overlay.font_size", 14)
        self._font_size_spin.setValue(font_size)

        self._font_color = self._config.get("overlay.font_color", "#ffffff")
        self._font_color_label.setText(self._font_color)

        self._bg_color = self._config.get("overlay.bg_color", "#171717")
        self._bg_color_label.setText(self._bg_color)

        bg_opacity = self._config.get("overlay.bg_opacity", 0.8)
        self._bg_opacity_slider.setValue(int(bg_opacity * 100))

        window_opacity = self._config.get("overlay.opacity", 0.85)
        self._window_opacity_slider.setValue(int(window_opacity * 100))

        self._update_color_buttons()
        self._update_preview()

        # Game exe path
        game_exe = self._config.get("game_exe_path", "")
        if game_exe:
            self._exe_path_edit.setText(game_exe)

        # System prompt
        system_prompt = self._config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        self._system_prompt_edit.setPlainText(system_prompt)

        # Context memory
        context_memory = self._config.get("context_memory", True)
        self._context_memory_checkbox.setChecked(context_memory)

        max_context = self._config.get("max_context", 10)
        self._context_size_slider.setValue(max_context)
        self._context_size_value_label.setText(str(max_context))

    def _on_save(self):
        # Provider
        self._config.set("provider", self._provider_combo.currentText())
        self._config.set("api_key", self._api_key_input.text().strip())

        # GlossaAPI server URL
        glossaapi_url = self._server_url_input.text().strip() or "http://localhost:8765/v1"
        self._config.set("glossaapi_url", glossaapi_url)
        if "GlossaAPI (Local Server)" in PROVIDERS:
            PROVIDERS["GlossaAPI (Local Server)"]["api_base"] = glossaapi_url

        model_data = self._model_combo.currentData()
        model_text = self._model_combo.currentText()
        self._config.set("model", model_data if model_data else model_text)

        self._config.set("source_lang", self._source_lang_combo.currentData())
        self._config.set("target_lang", self._target_lang_combo.currentData())

        # Source checkboxes
        self._config.set("clipboard_enabled", self._clipboard_checkbox.isChecked())
        self._config.set("hook_enabled", self._hook_checkbox.isChecked())
        self._config.set("ocr_enabled", self._ocr_checkbox.isChecked())
        self._config.set("audio_enabled", self._audio_checkbox.isChecked())

        # OCR interval
        self._config.set("ocr_interval", self._ocr_interval_spin.value())

        # Audio device
        audio_device_data = self._audio_device_combo.currentData()
        self._config.set("audio_device", audio_device_data if audio_device_data is not None else -1)

        # OCR provider
        ocr_provider = self._ocr_provider_combo.currentData() or ""
        self._config.set("ocr_provider", ocr_provider)
        self._config.set("ocr_api_key", self._ocr_api_key_input.text().strip())

        # Game exe path
        exe_path = self._exe_path_edit.text().strip()
        if exe_path:
            self._config.set("game_exe_path", exe_path)

        # UI language
        selected_ui_lang = self._ui_lang_combo.currentData()
        self._config.set("ui_language", selected_ui_lang)
        load_language(selected_ui_lang)

        # Theme
        theme = "dark" if self._theme_toggle.is_dark else "light"
        self._config.set("theme", theme)

        # Overlay appearance
        self._config.set("overlay.font_family", self._font_family_combo.currentText())
        self._config.set("overlay.font_size", self._font_size_spin.value())
        self._config.set("overlay.font_color", self._font_color)
        self._config.set("overlay.bg_color", self._bg_color)
        self._config.set("overlay.bg_opacity", self._bg_opacity_slider.value() / 100.0)
        self._config.set("overlay.opacity", self._window_opacity_slider.value() / 100.0)

        # System prompt & context memory
        self._config.set("system_prompt", self._system_prompt_edit.toPlainText())
        self._config.set("context_memory", self._context_memory_checkbox.isChecked())
        self._config.set("max_context", self._context_size_slider.value())

        # Apply to AI client
        api_key = self._api_key_input.text().strip()
        if api_key:
            self._ai.api_key = api_key
        self._ai.provider = self._provider_combo.currentText()
        model_val = self._model_combo.currentData() or self._model_combo.currentText()
        if model_val:
            self._ai.model = model_val
        self._ai.system_prompt = self._system_prompt_edit.toPlainText()
        self._ai.context_enabled = self._context_memory_checkbox.isChecked()
        self._ai.set_max_context(self._context_size_slider.value())

        # OCR provider
        if ocr_provider:
            self._ai.set_ocr_provider(ocr_provider, self._ocr_api_key_input.text().strip())
        else:
            self._ai.set_ocr_provider(None, None)

        self.settings_saved.emit()
        self.accept()

    def _on_cancel(self):
        self.reject()

    # -------------------------------------------------------------------------
    # Stylesheet
    # -------------------------------------------------------------------------
    def _apply_stylesheet(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_BG};
                color: {TEXT_COLOR};
            }}

            QTabWidget::pane {{
                border: 1px solid {DARK_ACCENT};
                border-radius: 10px;
                background-color: {DARK_PANEL};
                padding: 8px;
            }}

            QTabBar::tab {{
                background-color: {DARK_BG};
                color: {TEXT_COLOR};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid {DARK_ACCENT};
                border-bottom: none;
            }}

            QTabBar::tab:selected {{
                background-color: {DARK_PANEL};
                color: {TEXT_LIGHT};
                font-weight: bold;
            }}

            QTabBar::tab:hover {{
                background-color: {DARK_ACCENT};
            }}

            QLabel {{
                color: {TEXT_COLOR};
                font-size: 13px;
            }}

            QLineEdit {{
                background-color: {DARK_BG};
                color: {TEXT_LIGHT};
                border: 1px solid {DARK_ACCENT};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}

            QLineEdit:focus {{
                border: 1px solid {DARK_HIGHLIGHT};
            }}

            QComboBox {{
                background-color: {DARK_BG};
                color: {TEXT_LIGHT};
                border: 1px solid {DARK_ACCENT};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}

            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #ffffff;
                width: 0;
                height: 0;
            }}

            QComboBox::down-arrow:on {{
                border-top: none;
                border-bottom: 6px solid #ffffff;
            }}

            QComboBox QAbstractItemView {{
                background-color: {DARK_PANEL};
                color: {TEXT_LIGHT};
                border: 1px solid {DARK_ACCENT};
                selection-background-color: {DARK_ACCENT};
                selection-color: {TEXT_LIGHT};
            }}

            QPushButton {{
                background-color: {DARK_ACCENT};
                color: {TEXT_LIGHT};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {DARK_HIGHLIGHT};
            }}

            QPushButton:pressed {{
                background-color: #c73e54;
            }}

            QPushButton:disabled {{
                background-color: #2a2a3e;
                color: #666;
            }}

            QTextEdit {{
                background-color: {DARK_BG};
                color: {TEXT_LIGHT};
                border: 1px solid {DARK_ACCENT};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}

            QTextEdit:focus {{
                border: 1px solid {DARK_HIGHLIGHT};
            }}

            QSpinBox {{
                background-color: {DARK_BG};
                color: {TEXT_LIGHT};
                border: 1px solid {DARK_ACCENT};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}

            QSlider::groove:horizontal {{
                background: {DARK_BG};
                height: 6px;
                border-radius: 3px;
            }}

            QSlider::handle:horizontal {{
                background: {DARK_HIGHLIGHT};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}

            QSlider::sub-page:horizontal {{
                background: {DARK_ACCENT};
                border-radius: 3px;
            }}

            QCheckBox {{
                color: {TEXT_COLOR};
                font-size: 13px;
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {DARK_ACCENT};
                border-radius: 4px;
                background-color: {DARK_BG};
            }}

            QCheckBox::indicator:checked {{
                background-color: {DARK_HIGHLIGHT};
                border-color: {DARK_HIGHLIGHT};
            }}

            QFrame[frameShape="4"] {{
                color: {DARK_ACCENT};
                max-height: 1px;
            }}

            QDialogButtonBox {{
                button-layout: 0;
            }}
        """)
