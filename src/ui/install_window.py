"""
Auto-installer progress window shown on first run
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class InstallWorker(QThread):
    progress = pyqtSignal(str, int)
    component_done = pyqtSignal(str, bool)
    all_done = pyqtSignal()

    def __init__(self, components: list):
        super().__init__()
        self.components = components

    def run(self):
        from src.installer import COMPONENTS, install_component
        for key in self.components:
            comp = COMPONENTS[key]
            name = comp["name"]
            self.progress.emit(name, 0)

            def cb(pct, n=name):
                self.progress.emit(n, pct)

            ok = install_component(key, cb)
            self.component_done.emit(name, ok)
        self.all_done.emit()


class InstallWindow(QWidget):
    install_complete = pyqtSignal()

    def __init__(self, components: list):
        super().__init__()
        self.setWindowTitle("Glossa - Setting up...")
        self.setFixedSize(480, 300)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("""
            QWidget { background: #171717; color: white; font-family: 'Segoe UI'; }
            QProgressBar { background: #2e2e2e; border-radius: 5px; height: 8px; border: none; }
            QProgressBar::chunk { background: #0f3460; border-radius: 5px; }
            QPushButton { background: #0f3460; color: white; border: none;
                          padding: 10px 24px; border-radius: 6px; font-size: 13px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        title = QLabel("🌐 Glossa")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self._sub = QLabel("Setting up required components...")
        self._sub.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self._sub)

        self._lbl = QLabel("Preparing...")
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

        self._log = QLabel("")
        self._log.setStyleSheet("color: #aaa; font-size: 11px;")
        self._log.setWordWrap(True)
        layout.addWidget(self._log)

        layout.addStretch()

        self._btn = QPushButton("Continue →")
        self._btn.hide()
        self._btn.clicked.connect(self.install_complete.emit)
        self._btn.clicked.connect(self.close)
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._worker = InstallWorker(components)
        self._worker.progress.connect(self._on_progress)
        self._worker.component_done.connect(self._on_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_progress(self, name, pct):
        self._lbl.setText(f"Installing: {name}")
        self._bar.setValue(pct)

    def _on_done(self, name, ok):
        icon = "OK" if ok else "FAIL"
        self._log.setText(f"{self._log.text()}\n[{icon}] {name}".strip())

    def _on_all_done(self):
        self._sub.setText("Setup complete! Ready to launch.")
        self._bar.setValue(100)
        self._lbl.setText("Done!")
        self._btn.show()
