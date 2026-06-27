"""
launcher/ui/notification_popup.py
Notificação estilo Steam: aparece no canto inferior direito da tela,
com ícone do jogo, título, texto e som customizado. Some após 5 segundos.
"""

import sys
import threading
from pathlib import Path

from PySide6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui     import QPixmap, QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication

from launcher.ui.theme import (
    COR_SIDEBAR, COR_BORDA, COR_TEXTO, COR_MUTED, COR_MUTED_DARK,
    COR_AZUL_CLARO, STATUS_VERDE,
)

POPUP_W = 320
POPUP_H = 80
MARGEM  = 16


def _tocar_som():
    """Toca notification.wav com volume reduzido via QSoundEffect."""
    try:
        from PySide6.QtMultimedia import QSoundEffect
        from PySide6.QtCore import QUrl
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
        wav  = base / "assets" / "notification.wav"
        if wav.exists():
            _tocar_som._efeito = QSoundEffect()
            _tocar_som._efeito.setSource(QUrl.fromLocalFile(str(wav)))
            _tocar_som._efeito.setVolume(0.3)  # 0.0 a 1.0 — ajuste aqui
            _tocar_som._efeito.play()
    except Exception:
        pass


class NotificationPopup(QWidget):
    """
    Popup estilo Steam no canto inferior direito da tela.

    Uso:
        popup = NotificationPopup(
            titulo="Download concluído",
            texto="Burglin' Gnomes está pronto para jogar.",
            icone_path="C:/LDKLauncher/thumbs/Burglin' Gnomes.jpg",
            sucesso=True,
        )
        popup.show()
    """

    def __init__(self, titulo: str, texto: str,
                 icone_path: str = "", sucesso: bool = True):
        super().__init__()

        # Janela flutuante sem borda, sempre no topo
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # não aparece na taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(POPUP_W, POPUP_H)

        self._build_ui(titulo, texto, icone_path, sucesso)
        self._posicionar()
        _tocar_som()

        # Animação de entrada: slide de baixo para cima
        tela   = QApplication.primaryScreen().availableGeometry()
        dest_y = tela.bottom() - POPUP_H - MARGEM
        orig_y = tela.bottom()

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(250)
        self._anim.setStartValue(QPoint(self.x(), orig_y))
        self._anim.setEndValue(QPoint(self.x(), dest_y))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        # Some após 5 segundos
        QTimer.singleShot(5000, self._fechar)

    def _build_ui(self, titulo: str, texto: str, icone_path: str, sucesso: bool):
        cor_acento = STATUS_VERDE if sucesso else "#c97a00"

        container = QWidget(self)
        container.setFixedSize(POPUP_W, POPUP_H)
        container.setStyleSheet(f"""
            QWidget {{
                background: {COR_SIDEBAR};
                border: 1px solid {COR_BORDA};
                border-left: 3px solid {cor_acento};
                border-radius: 6px;
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 10, 12, 10)
        layout.setSpacing(10)

        # Ícone do jogo (thumb 60x60)
        lbl_icone = QLabel()
        lbl_icone.setFixedSize(60, 60)
        lbl_icone.setAlignment(Qt.AlignCenter)
        lbl_icone.setStyleSheet("border: none; border-radius: 4px; background: transparent;")
        if icone_path:
            pix = QPixmap(icone_path)
            if not pix.isNull():
                pix = pix.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                # Crop central
                x = (pix.width()  - 60) // 2
                y = (pix.height() - 60) // 2
                pix = pix.copy(x, y, 60, 60)
                lbl_icone.setPixmap(pix)
        layout.addWidget(lbl_icone)

        # Textos
        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        txt_layout.setContentsMargins(0, 0, 0, 0)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_titulo.setStyleSheet(f"color: {COR_TEXTO}; border: none; background: transparent;")
        lbl_titulo.setWordWrap(False)

        lbl_texto = QLabel(texto)
        lbl_texto.setFont(QFont("Segoe UI", 10))
        lbl_texto.setStyleSheet(f"color: {COR_MUTED}; border: none; background: transparent;")
        lbl_texto.setWordWrap(True)

        txt_layout.addWidget(lbl_titulo)
        txt_layout.addWidget(lbl_texto)
        txt_layout.addStretch()
        layout.addLayout(txt_layout)

    def _posicionar(self):
        tela = QApplication.primaryScreen().availableGeometry()
        x = tela.right() - POPUP_W - MARGEM
        y = tela.bottom()  # começa fora da tela (animação sobe)
        self.move(x, y)

    def _fechar(self):
        self.deleteLater()

    def mousePressEvent(self, event):
        """Fecha ao clicar."""
        self._fechar()