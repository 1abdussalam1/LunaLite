"""
Glossa Overlay Window
- Top section: shows translation (semi-transparent background)
- Bottom section: transparent (see-through) - OCR reads this area
- Draggable + resizable
- When moved/resized, OCR region updates automatically
"""
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor
from PyQt6.QtWidgets import QWidget, QApplication, QMenu, QSizeGrip, QVBoxLayout, QLabel


HANDLE_SIZE = 12  # resize handle in bottom-right corner
TRANSLATION_HEIGHT = 60  # height of translation area at top


class OverlayWindow(QWidget):
    # Emitted when position/size changes → OCR should update region
    region_changed = pyqtSignal(int, int, int, int)  # x, y, w, h

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._drag_pos = None
        self._resizing = False
        self._resize_start = None
        self._resize_geo = None
        self._translation_text = ""
        self._rtl = False

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
        self.setMinimumSize(200, 100)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def _apply_config(self):
        ov = self._config.get("overlay", {}) if isinstance(self._config, dict) else {}
        x = ov.get("x", 100)
        y = ov.get("y", 100)
        w = ov.get("width", 500)
        h = ov.get("height", 200)
        self.setGeometry(x, y, w, h)
        self.setWindowOpacity(ov.get("opacity", 0.95))

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        ov = self._config.get("overlay", {}) if isinstance(self._config, dict) else {}

        # ── Translation area (top) ──
        bg_color = ov.get("bg_color", "#000000")
        bg_opacity = ov.get("bg_opacity", 0.85)
        r, g, b = self._hex_to_rgb(bg_color)
        alpha = int(bg_opacity * 255)

        trans_h = min(TRANSLATION_HEIGHT, h // 2)
        p.setBrush(QBrush(QColor(r, g, b, alpha)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, trans_h, 8, 8)
        # Fill bottom part of translation area (remove rounded bottom corners)
        if trans_h < h:
            p.drawRect(0, trans_h - 8, w, 8)

        # Draw translation text
        font_color = ov.get("font_color", "#ffffff")
        font_size = ov.get("font_size", 14)
        font_family = ov.get("font_family", "Segoe UI")
        fc = QColor(font_color)
        p.setPen(fc)
        font = QFont(font_family, font_size)
        p.setFont(font)

        text_flags = Qt.AlignmentFlag.AlignVCenter
        if self._rtl:
            text_flags |= Qt.AlignmentFlag.AlignRight
        else:
            text_flags |= Qt.AlignmentFlag.AlignLeft

        text_rect = QRect(10, 0, w - 20, trans_h)
        p.drawText(text_rect, text_flags | Qt.TextFlag.TextWordWrap, self._translation_text)

        # ── OCR area (bottom) — transparent with dashed border ──
        ocr_rect = QRect(0, trans_h, w, h - trans_h)
        p.setBrush(QBrush(QColor(0, 0, 0, 15)))  # barely visible
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(ocr_rect)

        # Dashed border around OCR area
        pen = QPen(QColor(255, 255, 255, 80))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawRect(ocr_rect.adjusted(0, 0, -1, -1))

        # Resize handle (bottom-right)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 100)))
        for i in range(3):
            offset = i * 4
            p.drawLine(
                w - HANDLE_SIZE + offset, h - 2,
                w - 2, h - HANDLE_SIZE + offset
            )

        # Small label in OCR area
        p.setPen(QColor(255, 255, 255, 60))
        small_font = QFont("Segoe UI", 8)
        p.setFont(small_font)
        p.drawText(QRect(4, trans_h + 2, w - 8, 16),
                   Qt.AlignmentFlag.AlignLeft, "🌐 OCR Region")

        p.end()

    # ── Public API ─────────────────────────────────────────────────────────

    def set_text(self, text: str):
        self._translation_text = text
        self.update()

    def set_rtl(self, rtl: bool):
        self._rtl = rtl
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
            self._config.setdefault("overlay", {})["bg_color"] = color
            if opacity is not None:
                self._config["overlay"]["bg_opacity"] = opacity
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
        """Return (x, y, w, h) of the OCR area (bottom part of overlay)"""
        geo = self.geometry()
        trans_h = min(TRANSLATION_HEIGHT, geo.height() // 2)
        return (
            geo.x(),
            geo.y() + trans_h,
            geo.width(),
            geo.height() - trans_h
        )

    def save_position(self):
        geo = self.geometry()
        if isinstance(self._config, dict):
            ov = self._config.setdefault("overlay", {})
            ov.update({"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height()})
        # Notify OCR to update region
        x, y, w, h = self.get_ocr_region()
        self.region_changed.emit(x, y, w, h)

    # ── Mouse Events ────────────────────────────────────────────────────────

    def _in_resize_zone(self, pos):
        return (pos.x() > self.width() - HANDLE_SIZE * 2 and
                pos.y() > self.height() - HANDLE_SIZE * 2)

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
            new_w = max(200, self._resize_geo.width() + delta.x())
            new_h = max(100, self._resize_geo.height() + delta.y())
            self.setGeometry(self._resize_geo.x(), self._resize_geo.y(), new_w, new_h)
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
            QMenu { background: #1e1e1e; color: #fff; border: 1px solid #333;
                    border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 18px; border-radius: 4px; }
            QMenu::item:selected { background: #0f3460; }
        """)
        settings_act = menu.addAction("⚙️ Settings")
        menu.addSeparator()
        exit_act = menu.addAction("✕ Exit")
        action = menu.exec(event.globalPos())
        if action == settings_act:
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
