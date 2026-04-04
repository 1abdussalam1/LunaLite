"""
Glossa Overlay Window
- Translation text at top (auto-height, centered)
- OCR region: the full overlay area (invisible border optional)
- Draggable + resizable from bottom-right corner
"""
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QApplication, QMenu

HANDLE_SIZE = 16


class OverlayWindow(QWidget):
    region_changed = pyqtSignal(int, int, int, int)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._drag_pos = None
        self._resizing = False
        self._resize_start = None
        self._resize_geo = None
        self._translation_text = ""
        self._rtl = False
        self._show_border = True  # can be hidden from settings

        self._setup_window()
        self._apply_config()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setMinimumSize(200, 60)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def _apply_config(self):
        ov = self._config.get("overlay", {}) if isinstance(self._config, dict) else {}
        self.setGeometry(
            ov.get("x", 100), ov.get("y", 100),
            ov.get("width", 700), ov.get("height", 120)
        )
        self.setWindowOpacity(ov.get("opacity", 0.95))
        self._show_border = ov.get("show_border", True)

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ov = self._config.get("overlay", {}) if isinstance(self._config, dict) else {}
        w, h = self.width(), self.height()

        bg_color = ov.get("bg_color", "#000000")
        bg_opacity = ov.get("bg_opacity", 0.80)
        r, g, b = self._hex_to_rgb(bg_color)
        alpha = int(bg_opacity * 255)

        font_family = ov.get("font_family", "Segoe UI")
        font_size = ov.get("font_size", 16)
        font_color = ov.get("font_color", "#ffffff")

        font = QFont(font_family, font_size)
        font.setBold(False)
        p.setFont(font)

        # ── Calculate text height ──
        fm = QFontMetrics(font)
        text_rect = QRect(14, 10, w - 28, h - 20)
        flags = (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter |
                 Qt.TextFlag.TextWordWrap)
        if self._rtl:
            flags = (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter |
                     Qt.TextFlag.TextWordWrap)

        bounding = fm.boundingRect(text_rect, flags, self._translation_text)
        text_h = max(bounding.height() + 24, 50) if self._translation_text else 0

        # ── Draw background only if there's text ──
        if self._translation_text and text_h > 0:
            p.setBrush(QBrush(QColor(r, g, b, alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 0, w, text_h, 10, 10)

            # Draw text
            p.setPen(QColor(font_color))
            p.drawText(QRect(14, 0, w - 28, text_h), flags, self._translation_text)

        # ── Draw border (optional) ──
        if self._show_border:
            pen = QPen(QColor(255, 255, 255, 60))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(1)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(0, 0, w - 1, h - 1)

            # Resize handle dots
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 120)))
            for i in range(1, 4):
                d = i * 5
                p.drawEllipse(w - d - 3, h - 4, 3, 3)
                p.drawEllipse(w - 4, h - d - 3, 3, 3)

        p.end()

    # ── Public API ─────────────────────────────────────────────────────────

    def set_text(self, text: str):
        self._translation_text = text
        self.update()

    def set_rtl(self, rtl: bool):
        self._rtl = rtl
        self.update()

    def set_show_border(self, show: bool):
        self._show_border = show
        if isinstance(self._config, dict):
            self._config.setdefault("overlay", {})["show_border"] = show
        self.update()

    def set_font_size(self, size: int):
        if isinstance(self._config, dict):
            self._config.setdefault("overlay", {})["font_size"] = size
        self.update()

    def set_font_color(self, color: str):
        if isinstance(self._config, dict):
            self._config.setdefault("overlay", {})["font_color"] = color
        self.update()

    def set_bg_color(self, color: str, opacity: float = None):
        if isinstance(self._config, dict):
            ov = self._config.setdefault("overlay", {})
            ov["bg_color"] = color
            if opacity is not None:
                ov["bg_opacity"] = opacity
        self.update()

    def set_opacity(self, opacity: float):
        self.setWindowOpacity(opacity)
        if isinstance(self._config, dict):
            self._config.setdefault("overlay", {})["opacity"] = opacity

    def update_appearance(self, font_family, font_size, font_color, bg_color, bg_opacity, window_opacity):
        if isinstance(self._config, dict):
            ov = self._config.setdefault("overlay", {})
            ov.update({
                "font_family": font_family, "font_size": font_size,
                "font_color": font_color, "bg_color": bg_color,
                "bg_opacity": bg_opacity,
            })
        self.setWindowOpacity(window_opacity)
        self.update()

    def get_ocr_region(self):
        """Full overlay area is the OCR region"""
        geo = self.geometry()
        return geo.x(), geo.y(), geo.width(), geo.height()

    def save_position(self):
        geo = self.geometry()
        if isinstance(self._config, dict):
            ov = self._config.setdefault("overlay", {})
            ov.update({"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()})
        x, y, w, h = self.get_ocr_region()
        self.region_changed.emit(x, y, w, h)

    # ── Mouse Events ────────────────────────────────────────────────────────

    def _in_resize_zone(self, pos):
        return pos.x() > self.width() - HANDLE_SIZE and pos.y() > self.height() - HANDLE_SIZE

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._in_resize_zone(event.pos()):
                self._resizing = True
                self._resize_start = event.globalPosition().toPoint()
                self._resize_geo = self.geometry()
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_start:
            delta = event.globalPosition().toPoint() - self._resize_start
            nw = max(200, self._resize_geo.width() + delta.x())
            nh = max(60, self._resize_geo.height() + delta.y())
            self.setGeometry(self._resize_geo.x(), self._resize_geo.y(), nw, nh)
            self.update()
        elif self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        else:
            if self._in_resize_zone(event.pos()):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resizing = False
        self._resize_start = None
        self._resize_geo = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.save_position()
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background:#1e1e1e; color:#fff; border:1px solid #333;
                    border-radius:6px; padding:4px; }
            QMenu::item { padding:6px 18px; border-radius:4px; }
            QMenu::item:selected { background:#0f3460; }
        """)
        border_text = "Hide Border" if self._show_border else "Show Border"
        border_act = menu.addAction(f"👁 {border_text}")
        settings_act = menu.addAction("⚙️ Settings")
        menu.addSeparator()
        exit_act = menu.addAction("✕ Exit")
        action = menu.exec(event.globalPos())
        if action == border_act:
            self.set_show_border(not self._show_border)
        elif action == settings_act:
            self._on_settings_requested()
        elif action == exit_act:
            QApplication.quit()

    def _on_settings_requested(self):
        pass

    def set_settings_callback(self, cb):
        self._on_settings_requested = cb

    def set_pause_callback(self, cb):
        pass

    @staticmethod
    def _hex_to_rgb(hex_color: str):
        h = hex_color.lstrip("#")
        if len(h) == 6:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0, 0, 0
