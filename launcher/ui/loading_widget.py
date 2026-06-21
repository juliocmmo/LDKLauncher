from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from launcher.ui.theme import *


class LoadingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COR_BG};")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        self._label = QLabel("Conectando...")
        font = QFont()
        font.setPointSize(14)
        self._label.setFont(font)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet(f"color: {COR_MUTED}; background: transparent;")
        layout.addWidget(self._label)

        self._barra = QProgressBar()
        self._barra.setFixedSize(220, 4)
        self._barra.setTextVisible(False)
        self._barra.setRange(0, 0)  # indeterminate
        self._barra.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COR_BORDA};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {COR_AZUL_CLARO};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self._barra, alignment=Qt.AlignCenter)

    def set_texto(self, texto: str):
        self._label.setText(texto)