import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar

from ui.theme import (
    COR_BG, COR_BORDA, COR_AZUL_CLARO, COR_TEXTO, COR_MUTED
)


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 200)

        # Centraliza na tela
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        self._build_ui()
        self.show()
        QApplication.processEvents()

    def _build_ui(self):
        # Container principal (desenha borda+fundo no paintEvent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)   # espaço para a borda de 2px
        layout.setSpacing(0)

        inner = QWidget()
        inner.setObjectName("splashInner")
        inner.setStyleSheet(f"""
            QWidget#splashInner {{
                background: {COR_BG};
                border-radius: 10px;
            }}
        """)
        layout.addWidget(inner)

        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(16, 28, 16, 0)
        vbox.setSpacing(0)

        # Logo
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(base_path, "assets", "ldkf.ico")
        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignCenter)
        pix = QPixmap(logo_path)
        if not pix.isNull():
            lbl_logo.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_logo.setText("LDK")
            lbl_logo.setStyleSheet(f"color: {COR_AZUL_CLARO}; font-size: 28px; font-weight: bold;")
        vbox.addWidget(lbl_logo)

        vbox.addSpacing(6)

        # Nome
        lbl_nome = QLabel("LDK LAUNCHER")
        lbl_nome.setAlignment(Qt.AlignCenter)
        lbl_nome.setStyleSheet(f"color: {COR_TEXTO}; font-size: 13px; font-weight: bold;")
        vbox.addWidget(lbl_nome)

        vbox.addSpacing(16)

        # Status
        self._lbl_status = QLabel("Iniciando...")
        self._lbl_status.setAlignment(Qt.AlignCenter)
        self._lbl_status.setStyleSheet(f"color: {COR_MUTED}; font-size: 11px;")
        vbox.addWidget(self._lbl_status)

        vbox.addStretch()

        # Barra indeterminate na base
        self._barra = QProgressBar()
        self._barra.setRange(0, 0)          # modo indeterminate
        self._barra.setFixedHeight(3)
        self._barra.setTextVisible(False)
        self._barra.setStyleSheet(f"""
            QProgressBar {{
                background: {COR_BORDA};
                border: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
            QProgressBar::chunk {{
                background: {COR_AZUL_CLARO};
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
        """)
        vbox.addWidget(self._barra)

    def paintEvent(self, event):
        """Desenha o fundo com borda arredondada."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        painter.fillPath(path, QColor(COR_BORDA))   # borda
        painter.end()

    # ── API pública (mesma da versão CTk) ────────────────────────────────────

    def set_status(self, texto: str):
        self._lbl_status.setText(texto)
        QApplication.processEvents()

    def fechar(self):
        self.close()