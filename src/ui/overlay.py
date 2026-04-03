from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, pyqtProperty, QTimer
from PyQt6.QtGui import QColor, QFont, QAction, QCursor
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QApplication, QGraphicsOpacityEffect


class OverlayWindow(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._drag_pos = None
        self._text_opacity = 1.0

        self._setup_window()
        self._setup_ui()
        self._apply_config()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(200, 80)

    def _setup_ui(self):
        self._container = QWidget(self)
        self._container.setObjectName("overlayContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._container)

        inner_layout = QVBoxLayout(self._container)
        inner_layout.setContentsMargins(12, 8, 12, 10)
        inner_layout.setSpacing(4)

        self._branding = QLabel("\U0001f319 LunaLite")
        self._branding.setObjectName("branding")
        self._branding.setFixedHeight(16)
        inner_layout.addWidget(self._branding)

        self._text_label = QLabel("")
        self._text_label.setObjectName("translationText")
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        inner_layout.addWidget(self._text_label, 1)

        self._opacity_effect = QGraphicsOpacityEffect(self._text_label)
        self._opacity_effect.setOpacity(1.0)
        self._text_label.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _apply_config(self):
        ov = self._config.get("overlay", {})
        if isinstance(ov, dict):
            x = ov.get("x", 100)
            y = ov.get("y", 100)
            w = ov.get("width", 500)
            h = ov.get("height", 150)
            self.setGeometry(x, y, w, h)

            opacity = ov.get("opacity", 0.85)
            self.setWindowOpacity(opacity)

            font_family = ov.get("font_family", "Segoe UI")
            font_size = ov.get("font_size", 14)
            font_color = ov.get("font_color", "#ffffff")
            bg_color = ov.get("bg_color", "#171717")
            bg_opacity = ov.get("bg_opacity", 0.8)
        else:
            self.setGeometry(100, 100, 500, 150)
            font_family = "Segoe UI"
            font_size = 14
            font_color = "#ffffff"
            bg_color = "#171717"
            bg_opacity = 0.8

        bg_r, bg_g, bg_b = self._hex_to_rgb(bg_color)
        bg_alpha = int(bg_opacity * 255)

        self._container.setStyleSheet(f"""
            #overlayContainer {{
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_alpha});
                border-radius: 10px;
            }}
        """)

        self._text_label.setStyleSheet(f"""
            #translationText {{
                color: {font_color};
                font-family: '{font_family}';
                font-size: {font_size}px;
                background: transparent;
                padding: 4px;
            }}
        """)

        self._branding.setStyleSheet("""
            #branding {
                color: rgba(255, 255, 255, 0.4);
                font-size: 9px;
                background: transparent;
            }
        """)

    def set_font_size(self, size: int):
        font = self._text_label.font()
        font.setPointSize(size)
        self._text_label.setFont(font)
        self._config["overlay"]["font_size"] = size

    def set_font_color(self, color: str):
        self._text_label.setStyleSheet(f"color: {color}; background: transparent;")
        self._config["overlay"]["font_color"] = color

    def set_bg_color(self, color: str, opacity: float = None):
        self._config["overlay"]["bg_color"] = color
        bg_opacity = opacity if opacity is not None else self._config.get("overlay", {}).get("bg_opacity", 0.8)
        bg_r, bg_g, bg_b = self._hex_to_rgb(color)
        bg_alpha = int(bg_opacity * 255)
        self._container.setStyleSheet(f"""
            #overlayContainer {{
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_alpha});
                border-radius: 10px;
            }}
        """)

    def set_opacity(self, opacity: float):
        self.setWindowOpacity(opacity)
        self._config["overlay"]["opacity"] = opacity

    def set_text(self, text: str):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._text_label.setText(text)
        self._fade_anim.start()

    def set_rtl(self, rtl: bool):
        if rtl:
            self._text_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            self._text_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self._text_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    def update_appearance(self, font_family: str, font_size: int, font_color: str,
                          bg_color: str, bg_opacity: float, window_opacity: float):
        bg_r, bg_g, bg_b = self._hex_to_rgb(bg_color)
        bg_alpha = int(bg_opacity * 255)

        self._container.setStyleSheet(f"""
            #overlayContainer {{
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_alpha});
                border-radius: 10px;
            }}
        """)
        self._text_label.setStyleSheet(f"""
            #translationText {{
                color: {font_color};
                font-family: '{font_family}';
                font-size: {font_size}px;
                background: transparent;
                padding: 4px;
            }}
        """)
        self.setWindowOpacity(window_opacity)

    def save_position(self):
        geo = self.geometry()
        self._config["overlay"]["x"] = geo.x()
        self._config["overlay"]["y"] = geo.y()
        self._config["overlay"]["width"] = geo.width()
        self._config["overlay"]["height"] = geo.height()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self.save_position()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0f3460;
            }
        """)

        settings_action = menu.addAction("Settings")
        pause_action = menu.addAction("Toggle Pause")
        menu.addSeparator()
        exit_action = menu.addAction("Exit")

        action = menu.exec(event.globalPos())
        if action == settings_action:
            self._on_settings_requested()
        elif action == pause_action:
            self._on_pause_requested()
        elif action == exit_action:
            QApplication.quit()

    def _on_settings_requested(self):
        pass

    def _on_pause_requested(self):
        pass

    def set_settings_callback(self, callback):
        self._on_settings_requested = callback

    def set_pause_callback(self, callback):
        self._on_pause_requested = callback

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return 23, 23, 23
