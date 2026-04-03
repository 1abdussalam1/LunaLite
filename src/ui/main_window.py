import math
from typing import Optional

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPointF,
    pyqtSignal, pyqtProperty, QSize,
)
from PyQt6.QtGui import (
    QAction, QColor, QConicalGradient, QFont, QIcon, QPainter,
    QPainterPath, QPen, QPixmap, QRadialGradient, QBrush,
)
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMenu,
    QMessageBox, QPushButton, QSizePolicy, QSystemTrayIcon, QVBoxLayout,
    QWidget, QSpacerItem, QCheckBox,
)

from src.utils.config import ConfigManager
from src.utils.i18n import t, is_rtl, load_language, on_language_changed
from src.utils.cache import TranslationCache
from src.core.ai_client import AIClient, TranslateWorker, AudioTranslateWorker
from src.core.audio_capture import AudioCapture
from src.core.text_extractor import ClipboardMonitor
from src.core.ocr_capture import OCRCapture
from src.ui.overlay import OverlayWindow
from src.ui.settings_window import SettingsWindow


COLOR_BG = "#171717"
COLOR_PANEL = "#1e1e1e"
COLOR_ACCENT = "#0f3460"
COLOR_HIGHLIGHT = "#e94560"


class PowerButton(QWidget):
    """Custom circular power toggle button with animated border ring."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._active = False
        self._ring_angle = 0.0
        self._glow_opacity = 0.0
        self._hover = False

        self.setFixedSize(80, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._ring_timer = QTimer(self)
        self._ring_timer.setInterval(16)
        self._ring_timer.timeout.connect(self._advance_ring)

        self._glow_anim = QPropertyAnimation(self, b"glowOpacity")
        self._glow_anim.setDuration(1200)
        self._glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._glow_anim.setStartValue(0.3)
        self._glow_anim.setEndValue(0.8)
        self._glow_anim.setLoopCount(-1)

        self._transition_anim = QPropertyAnimation(self, b"glowOpacity")
        self._transition_anim.setDuration(300)
        self._transition_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _get_glow_opacity(self) -> float:
        return self._glow_opacity

    def _set_glow_opacity(self, value: float):
        self._glow_opacity = value
        self.update()

    glowOpacity = pyqtProperty(float, _get_glow_opacity, _set_glow_opacity)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool):
        if self._active == value:
            return
        self._active = value
        if self._active:
            self._start_active_animations()
        else:
            self._stop_active_animations()
        self.update()

    def _start_active_animations(self):
        self._ring_timer.start()
        self._transition_anim.stop()
        self._glow_anim.stop()
        self._transition_anim.setStartValue(self._glow_opacity)
        self._transition_anim.setEndValue(0.5)
        self._transition_anim.finished.connect(self._begin_pulse)
        self._transition_anim.start()

    def _begin_pulse(self):
        try:
            self._transition_anim.finished.disconnect(self._begin_pulse)
        except TypeError:
            pass
        if self._active:
            self._glow_anim.setStartValue(0.3)
            self._glow_anim.setEndValue(0.8)
            self._glow_anim.start()

    def _stop_active_animations(self):
        self._ring_timer.stop()
        self._glow_anim.stop()
        try:
            self._transition_anim.finished.disconnect(self._begin_pulse)
        except TypeError:
            pass
        self._transition_anim.setStartValue(self._glow_opacity)
        self._transition_anim.setEndValue(0.0)
        self._transition_anim.start()

    def _advance_ring(self):
        self._ring_angle = (self._ring_angle + 2.0) % 360.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._active = not self._active
            if self._active:
                self._start_active_animations()
            else:
                self._stop_active_animations()
            self.toggled.emit(self._active)
            self.update()
            event.accept()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(w, h) / 2.0 - 4.0

        if self._active and self._glow_opacity > 0.01:
            glow_gradient = QRadialGradient(QPointF(cx, cy), radius + 10)
            glow_color = QColor(COLOR_HIGHLIGHT)
            glow_color.setAlphaF(self._glow_opacity * 0.5)
            glow_gradient.setColorAt(0.5, glow_color)
            glow_color_outer = QColor(COLOR_HIGHLIGHT)
            glow_color_outer.setAlphaF(0.0)
            glow_gradient.setColorAt(1.0, glow_color_outer)
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), radius + 10, radius + 10)

        if self._active:
            ring_gradient = QConicalGradient(QPointF(cx, cy), self._ring_angle)
            ring_gradient.setColorAt(0.0, QColor(COLOR_ACCENT))
            ring_gradient.setColorAt(0.25, QColor(COLOR_HIGHLIGHT))
            ring_gradient.setColorAt(0.5, QColor(COLOR_ACCENT))
            ring_gradient.setColorAt(0.75, QColor(COLOR_HIGHLIGHT))
            ring_gradient.setColorAt(1.0, QColor(COLOR_ACCENT))
            pen = QPen(QBrush(ring_gradient), 3.0)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

        bg_color = QColor(COLOR_PANEL)
        if self._hover and not self._active:
            bg_color = bg_color.lighter(130)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        inner_radius = radius - 3.0 if self._active else radius
        painter.drawEllipse(QPointF(cx, cy), inner_radius, inner_radius)

        icon_color = QColor("#ffffff") if self._active else QColor("#888888")
        if self._hover and not self._active:
            icon_color = QColor("#bbbbbb")
        pen = QPen(icon_color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        icon_radius = inner_radius * 0.35
        arc_rect = QRectF(cx - icon_radius, cy - icon_radius + 2, icon_radius * 2, icon_radius * 2)
        start_angle = 60 * 16
        span_angle = 240 * 16
        painter.drawArc(arc_rect, start_angle, span_angle)

        line_len = icon_radius * 0.8
        painter.drawLine(
            QPointF(cx, cy - icon_radius + 2 - 1),
            QPointF(cx, cy - icon_radius + 2 + line_len),
        )

        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(80, 80)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._force_quit = False
        self._workers: list = []

        # Core components
        self.config = ConfigManager()
        self.ai_client = AIClient(
            provider=self.config.get("provider", "Google Gemini"),
            api_key=self.config.get("api_key", ""),
            model=self.config.get("model", "gemini-2.0-flash"),
        )
        self.ai_client.system_prompt = self.config.get(
            "system_prompt",
            "You are a game translator. Translate the following {source_lang} text to {target_lang}. Return ONLY the translation, nothing else.",
        )
        self.ai_client.context_enabled = self.config.get("context_memory", True)
        self.ai_client.set_max_context(self.config.get("max_context", 10))

        # Set up OCR provider if configured
        ocr_provider = self.config.get("ocr_provider", "")
        if ocr_provider:
            self.ai_client.set_ocr_provider(ocr_provider, self.config.get("ocr_api_key", ""))

        self.cache = TranslationCache()
        self.audio_capture = AudioCapture()
        self.clipboard_monitor = ClipboardMonitor()
        self.ocr_capture = OCRCapture(self.ai_client, self._on_ocr_text)

        # Overlay
        self.overlay = OverlayWindow(self.config.data)

        # Load i18n
        ui_lang = self.config.get("ui_language", "en")
        load_language(ui_lang)

        # Window setup
        self.setWindowTitle("Glossa")
        self.setFixedSize(420, 520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint
        )

        # Build UI
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

        on_language_changed(self.retranslate_ui)

    def _setup_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- Title ---
        self._title_label = QLabel("\U0001f310 Glossa")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #ffffff; background: transparent;")
        main_layout.addWidget(self._title_label)

        main_layout.addSpacerItem(QSpacerItem(1, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Status indicator ---
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            "background-color: #888888; border-radius: 5px; border: none;"
        )
        status_layout.addWidget(self._status_dot)

        self._status_label = QLabel("Idle")
        self._status_label.setStyleSheet("color: #888888; font-size: 13px; background: transparent;")
        status_layout.addWidget(self._status_label)

        main_layout.addWidget(status_container)

        # --- Source checkboxes ---
        source_container = QWidget()
        source_container.setMinimumWidth(300)
        source_layout = QHBoxLayout(source_container)
        source_layout.setContentsMargins(20, 4, 20, 4)
        source_layout.setSpacing(20)
        source_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cb_style = "QCheckBox { color: #aaa; font-size: 12px; background: transparent; spacing: 6px; }"

        self._clipboard_cb = QCheckBox(t("clipboard_mode", "Clipboard"))
        self._clipboard_cb.setChecked(self.config.get("clipboard_enabled", True))
        self._clipboard_cb.setStyleSheet(cb_style)
        self._clipboard_cb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        source_layout.addWidget(self._clipboard_cb)

        self._ocr_cb = QCheckBox(t("ocr_mode", "OCR"))
        self._ocr_cb.setChecked(self.config.get("ocr_enabled", False))
        self._ocr_cb.setStyleSheet(cb_style)
        self._ocr_cb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        source_layout.addWidget(self._ocr_cb)

        self._audio_cb = QCheckBox(t("audio_mode", "Audio"))
        self._audio_cb.setChecked(self.config.get("audio_enabled", False))
        self._audio_cb.setStyleSheet(cb_style)
        self._audio_cb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        source_layout.addWidget(self._audio_cb)

        main_layout.addWidget(source_container)

        main_layout.addSpacerItem(QSpacerItem(1, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Power button ---
        power_container = QWidget()
        power_layout = QHBoxLayout(power_container)
        power_layout.setContentsMargins(0, 0, 0, 0)
        power_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._power_button = PowerButton()
        power_layout.addWidget(self._power_button)
        main_layout.addWidget(power_container)

        main_layout.addSpacerItem(QSpacerItem(1, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Token counter ---
        self._token_label = QLabel("In: 0 / Out: 0")
        self._token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._token_label.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
        main_layout.addWidget(self._token_label)

        # --- Context indicator ---
        context_container = QWidget()
        context_layout = QHBoxLayout(context_container)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(6)
        context_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        max_ctx = self.config.get("max_context", 10)
        self._context_label = QLabel(f"{t('context_indicator', 'Context')}: 0/{max_ctx}")
        self._context_label.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
        context_layout.addWidget(self._context_label)

        self._clear_context_btn = QPushButton("X")
        self._clear_context_btn.setFixedSize(24, 24)
        self._clear_context_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_context_btn.setToolTip(t("clear_context", "Clear Context"))
        self._clear_context_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; font-size: 12px; padding: 0; color: #888;
            }
            QPushButton:hover {
                background-color: rgba(233, 69, 96, 0.3); border-radius: 4px; color: #e94560;
            }
        """)
        context_layout.addWidget(self._clear_context_btn)

        main_layout.addWidget(context_container)

        main_layout.addSpacerItem(QSpacerItem(1, 6, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Settings button ---
        self._settings_btn = QPushButton(f"\u2699 {t('settings', 'Settings')}")
        self._settings_btn.setFixedHeight(38)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT}; color: #ffffff;
                border: none; border-radius: 8px; font-size: 14px; padding: 6px 20px;
            }}
            QPushButton:hover {{ background-color: {COLOR_HIGHLIGHT}; }}
            QPushButton:pressed {{ background-color: #c7374d; }}
        """)
        main_layout.addWidget(self._settings_btn)

        # --- Language toggle ---
        lang_toggle_container = QWidget()
        lang_toggle_layout = QHBoxLayout(lang_toggle_container)
        lang_toggle_layout.setContentsMargins(0, 0, 0, 0)
        lang_toggle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lang_en_btn = QPushButton("EN")
        self._lang_en_btn.setFixedSize(40, 28)
        self._lang_en_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_en_btn.setStyleSheet("background: transparent; color: #aaa; border: none; font-size: 12px;")
        self._lang_en_btn.clicked.connect(lambda: self._switch_ui_lang("en"))
        lang_toggle_layout.addWidget(self._lang_en_btn)

        sep_label = QLabel("|")
        sep_label.setStyleSheet("color: #555; background: transparent;")
        lang_toggle_layout.addWidget(sep_label)

        self._lang_ar_btn = QPushButton("\u0639\u0631\u0628\u064a")
        self._lang_ar_btn.setFixedSize(40, 28)
        self._lang_ar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_ar_btn.setStyleSheet("background: transparent; color: #aaa; border: none; font-size: 12px;")
        self._lang_ar_btn.clicked.connect(lambda: self._switch_ui_lang("ar"))
        lang_toggle_layout.addWidget(self._lang_ar_btn)

        main_layout.addWidget(lang_toggle_container)

        main_layout.addStretch(1)

    def _switch_ui_lang(self, lang: str):
        self.config.set("ui_language", lang)
        load_language(lang)

    def retranslate_ui(self, *args):
        self.setWindowTitle(t("app_name", "Glossa"))
        self._settings_btn.setText(f"\u2699 {t('settings', 'Settings')}")
        self._clear_context_btn.setToolTip(t("clear_context", "Clear Context"))
        max_ctx = self.config.get("max_context", 10)
        ctx_size = self.ai_client.get_context_size()
        self._context_label.setText(f"{t('context_indicator', 'Context')}: {ctx_size}/{max_ctx}")
        self._clipboard_cb.setText(t("clipboard_mode", "Clipboard"))
        self._ocr_cb.setText(t("ocr_mode", "OCR"))
        self._audio_cb.setText(t("audio_mode", "Audio"))
        self._tray_show_action.setText(t("show_window", "Show/Hide Window"))
        self._tray_startstop_action.setText(
            t("stop", "Stop") if self._power_button.active else t("start", "Start")
        )
        if is_rtl():
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def _setup_tray(self):
        tray_pixmap = QPixmap(32, 32)
        tray_pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(tray_pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Draw globe icon
        p.setBrush(QBrush(QColor("#4a90d9")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QPen(QColor("#ffffff"), 1))
        p.drawEllipse(8, 2, 16, 28)
        p.drawLine(2, 16, 30, 16)
        p.end()

        tray_icon = QIcon(tray_pixmap)

        self._tray = QSystemTrayIcon(tray_icon, self)
        self._tray.setToolTip("Glossa")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLOR_PANEL}; color: #ffffff;
                border: 1px solid {COLOR_ACCENT}; border-radius: 6px; padding: 4px;
            }}
            QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {COLOR_ACCENT}; }}
            QMenu::separator {{ height: 1px; background: {COLOR_ACCENT}; margin: 4px 8px; }}
        """)

        self._tray_show_action = QAction("Show/Hide Window", self)
        self._tray_show_action.triggered.connect(self._toggle_window_visibility)
        tray_menu.addAction(self._tray_show_action)

        self._tray_startstop_action = QAction("Start", self)
        self._tray_startstop_action.triggered.connect(self._tray_toggle_running)
        tray_menu.addAction(self._tray_startstop_action)

        tray_settings_action = QAction("Settings", self)
        tray_settings_action.triggered.connect(self._open_settings)
        tray_menu.addAction(tray_settings_action)

        tray_menu.addSeparator()

        tray_exit_action = QAction("Exit", self)
        tray_exit_action.triggered.connect(self._exit_app)
        tray_menu.addAction(tray_exit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _connect_signals(self):
        self._power_button.toggled.connect(self._on_power_toggled)
        self.ai_client.token_count_updated.connect(self._update_token_label)
        self.ai_client.error_occurred.connect(self._on_error)
        self.ai_client.context_changed.connect(self._update_context_label)
        self._settings_btn.clicked.connect(self._open_settings)
        self._clear_context_btn.clicked.connect(self._on_clear_context)

    def _set_status(self, state: str):
        if state == "running":
            self._status_dot.setStyleSheet("background-color: #00cc66; border-radius: 5px; border: none;")
            self._status_label.setText(t("running", "Running"))
            self._status_label.setStyleSheet("color: #00cc66; font-size: 13px; background: transparent;")
        elif state == "paused":
            self._status_dot.setStyleSheet("background-color: #f0c040; border-radius: 5px; border: none;")
            self._status_label.setText(t("paused", "Paused"))
            self._status_label.setStyleSheet("color: #f0c040; font-size: 13px; background: transparent;")
        else:
            self._status_dot.setStyleSheet("background-color: #888888; border-radius: 5px; border: none;")
            self._status_label.setText(t("idle", "Idle"))
            self._status_label.setStyleSheet("color: #888888; font-size: 13px; background: transparent;")

    def _on_power_toggled(self, active: bool):
        if active:
            self._start_translation()
        else:
            self._stop_translation()

    def _start_translation(self):
        # Start enabled sources
        if self._clipboard_cb.isChecked():
            self.clipboard_monitor.text_changed.connect(self._on_text_captured)
            self.clipboard_monitor.start()
            self.config.set("clipboard_enabled", True)

        if self._audio_cb.isChecked():
            self.audio_capture.audio_chunk_ready.connect(self._on_audio_captured)
            self.audio_capture.start()
            self.config.set("audio_enabled", True)

        if self._ocr_cb.isChecked():
            interval = self.config.get("ocr_interval", 2.0)
            self.ocr_capture.set_interval(interval)
            self.ocr_capture.start()
            self.config.set("ocr_enabled", True)

        self.overlay.show()
        self._set_status("running")
        self._tray_startstop_action.setText(t("stop", "Stop"))

    def _stop_translation(self):
        if self.clipboard_monitor.is_running:
            self.clipboard_monitor.stop()
            try:
                self.clipboard_monitor.text_changed.disconnect(self._on_text_captured)
            except TypeError:
                pass

        if self.audio_capture.is_running:
            self.audio_capture.stop()
            try:
                self.audio_capture.audio_chunk_ready.disconnect(self._on_audio_captured)
            except TypeError:
                pass

        if self.ocr_capture.is_running:
            self.ocr_capture.stop()

        self.overlay.hide()
        self._set_status("idle")
        self._tray_startstop_action.setText(t("start", "Start"))

    def _on_text_captured(self, text: str):
        if not text.strip():
            return

        source_lang = self.config.get("source_lang", "auto")
        target_lang = self.config.get("target_lang", "ar")

        cached = self.cache.get(text, source_lang, target_lang)
        if cached:
            self.overlay.set_text(cached)
            self.overlay.set_rtl(is_rtl())
            return

        worker = TranslateWorker(self.ai_client, text, source_lang, target_lang)
        worker.finished.connect(
            lambda result, t=text, sl=source_lang, tl=target_lang: self._on_text_translated(result, t, sl, tl)
        )
        worker.error.connect(self._on_error)
        self._workers.append(worker)
        worker.finished.connect(lambda _w=worker: self._cleanup_worker(_w))
        worker.error.connect(lambda _e, _w=worker: self._cleanup_worker(_w))
        worker.start()

    def _on_text_translated(self, result: str, source_text: str, source_lang: str, target_lang: str):
        if result:
            self.cache.put(source_text, source_lang, target_lang, result)
            self.overlay.set_text(result)
            self.overlay.set_rtl(is_rtl())

    def _on_audio_captured(self, wav_bytes: bytes):
        source_lang = self.config.get("source_lang", "auto")
        target_lang = self.config.get("target_lang", "ar")

        worker = AudioTranslateWorker(self.ai_client, wav_bytes, source_lang, target_lang)
        worker.finished.connect(self._on_audio_translated)
        worker.error.connect(self._on_error)
        self._workers.append(worker)
        worker.finished.connect(lambda _w=worker: self._cleanup_worker(_w))
        worker.error.connect(lambda _e, _w=worker: self._cleanup_worker(_w))
        worker.start()

    def _on_audio_translated(self, result: str):
        if result.strip():
            self.overlay.set_text(result)
            self.overlay.set_rtl(is_rtl())

    def _on_ocr_text(self, text: str):
        """Called from OCR capture thread when text is detected."""
        self._on_text_captured(text)

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    def _update_context_label(self, current: int, max_size: int):
        self._context_label.setText(f"{t('context_indicator', 'Context')}: {current}/{max_size}")

    def _on_clear_context(self):
        self.ai_client.clear_context()

    def _update_token_label(self, input_tokens: int, output_tokens: int):
        self._token_label.setText(f"In: {input_tokens} / Out: {output_tokens}")

    def _on_error(self, message: str):
        if "429" in str(message) or "quota" in str(message).lower():
            display_msg = "API quota exceeded."
        else:
            display_msg = str(message)[:200]
        self._status_label.setText(f"Error: {display_msg[:60]}")
        self._status_label.setStyleSheet("color: #e94560; font-size: 13px; background: transparent;")
        self._status_dot.setStyleSheet("background-color: #e94560; border-radius: 5px; border: none;")

    def _open_settings(self):
        dialog = SettingsWindow(self.config, self.ai_client, overlay=self.overlay, parent=self)
        if dialog.exec():
            self.config.load()
            self.ai_client.provider = self.config.get("provider", "Google Gemini")
            self.ai_client.api_key = self.config.get("api_key", "")
            self.ai_client.model = self.config.get("model", "gemini-2.0-flash")
            self.ai_client.system_prompt = self.config.get(
                "system_prompt",
                "You are a game translator. Translate the following {source_lang} text to {target_lang}. Return ONLY the translation, nothing else.",
            )
            self.ai_client.context_enabled = self.config.get("context_memory", True)
            self.ai_client.set_max_context(self.config.get("max_context", 10))
            self._update_context_label(self.ai_client.get_context_size(), self.ai_client.max_context)

            # Update OCR provider
            ocr_provider = self.config.get("ocr_provider", "")
            if ocr_provider:
                self.ai_client.set_ocr_provider(ocr_provider, self.config.get("ocr_api_key", ""))

            ui_lang = self.config.get("ui_language", "en")
            load_language(ui_lang)

            # Sync checkboxes
            self._clipboard_cb.setChecked(self.config.get("clipboard_enabled", True))
            self._ocr_cb.setChecked(self.config.get("ocr_enabled", False))
            self._audio_cb.setChecked(self.config.get("audio_enabled", False))

    def _toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _tray_toggle_running(self):
        new_state = not self._power_button.active
        self._power_button.active = new_state
        if new_state:
            self._start_translation()
        else:
            self._stop_translation()
        self._power_button.toggled.emit(new_state)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window_visibility()

    def closeEvent(self, event):
        if self._force_quit:
            self._stop_translation()
            self.cache.close()
            self._tray.hide()
            event.accept()
        else:
            event.ignore()
            self.hide()

    def _exit_app(self):
        self._force_quit = True
        self.close()
        QApplication.quit()
