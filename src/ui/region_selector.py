"""
Screen Region Selector
User drags mouse to select area to OCR
"""
from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen


class RegionSelector(QWidget):
    """
    Fullscreen semi-transparent overlay.
    User drags to select region, emits region_selected(x, y, w, h)
    """
    region_selected = pyqtSignal(int, int, int, int)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)

    def showEvent(self, e):
        # Cover all screens
        screen = QApplication.primaryScreen()
        geo = screen.virtualGeometry()
        self.setGeometry(geo)
        super().showEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        # Semi-transparent dark overlay
        p.fillRect(self.rect(), QColor(0, 0, 0, 100))
        # Instructions text
        p.setPen(QColor(255, 255, 255, 220))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                   "Drag to select OCR region\nPress Escape to cancel")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._start = e.pos()
            self._selecting = True
            self._rubber_band.setGeometry(QRect(self._start, QSize()))
            self._rubber_band.show()

    def mouseMoveEvent(self, e):
        if self._selecting:
            self._end = e.pos()
            self._rubber_band.setGeometry(
                QRect(self._start, self._end).normalized()
            )

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            self._rubber_band.hide()
            rect = QRect(self._start, e.pos()).normalized()
            self.close()
            if rect.width() > 10 and rect.height() > 10:
                self.region_selected.emit(rect.x(), rect.y(), rect.width(), rect.height())
            else:
                self.cancelled.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
            self.cancelled.emit()
