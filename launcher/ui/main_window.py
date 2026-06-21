from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

from launcher.ui.theme import *


class _TitleBar(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"background-color: {COR_BG};")
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 4, 0)
        layout.setSpacing(0)
        layout.addStretch()

        btn_min = QPushButton("−")
        btn_min.setFixedSize(32, 32)
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.setStyleSheet(self._btn_css(COR_MUTED, COR_ITEM_ATIVO, COR_TEXTO))
        btn_min.clicked.connect(lambda: self.window().showMinimized())
        layout.addWidget(btn_min)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(32, 32)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(self._btn_css(COR_MUTED, "#8b1a1a", COR_TEXTO))
        btn_close.clicked.connect(self.window().close)
        layout.addWidget(btn_close)

    @staticmethod
    def _btn_css(color: str, hover_bg: str, hover_color: str) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {color}; border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ background-color: {hover_bg}; color: {hover_color}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1280, 720)
        self.setMinimumSize(900, 600)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(COR_BG))
        self.setPalette(palette)

        root = QWidget()
        root.setStyleSheet(f"background-color: {COR_BG};")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_TitleBar(root))

        # Corpo: sidebar + painel direito
        corpo = QWidget()
        corpo_layout = QHBoxLayout(corpo)
        corpo_layout.setContentsMargins(0, 0, 0, 0)
        corpo_layout.setSpacing(0)

        from launcher.ui.sidebar import Sidebar
        self.sidebar = Sidebar()

        modpacks_placeholder = [
            {"name": "Escape the Backroom"},
            {"name": "Lethal Company"},
            {"name": "TEKKID 8"},
            {"name": "Super Battle Golf"},
            {"name": "Among Us"},
            {"name": "Burglin' Gnomes"},
            {"name": "MECCHA CHAMELEON"},
        ]
        self.sidebar.popular(modpacks_placeholder)

        borda = QFrame()
        borda.setFixedWidth(1)
        borda.setStyleSheet(f"background-color: {COR_BORDA};")

        self._painel = QWidget()
        self._painel.setStyleSheet(f"background-color: {COR_BG};")
        painel_layout = QVBoxLayout(self._painel)
        painel_layout.setContentsMargins(0, 0, 0, 0)
        painel_layout.setSpacing(0)

        # Cards placeholder com dados do version.json
        modpacks_dados = [
            {"name": "Escape the Backroom", "status": "nao_instalado", "version": "1.0.3", "type": "standalone", "size_bytes": 27291482145, "description": "Explore os labirintos infinitos dos Backrooms.", "executable": "Backrooms.exe"},
            {"name": "Lethal Company",      "status": "atualizado",    "version": "1.0.2", "version_local": "1.0.2", "version_remote": "1.0.2", "type": "standalone", "size_bytes": 2010575591, "description": "Colete sucata espacial para pagar a dívida da empresa.", "executable": "Lethal Company.exe"},
            {"name": "TEKKID 8",            "status": "nao_instalado", "version": "1.0.2", "type": "minecraft",  "size_bytes": 888041377,  "description": "Modpack de Minecraft do grupo LDKF."},
            {"name": "Super Battle Golf",   "status": "nao_instalado", "version": "1.0.0", "type": "standalone", "size_bytes": 1372022844, "description": "Golf mas com superpoderes e batalha.", "executable": "Super Battle Golf.exe"},
            {"name": "Among Us",            "status": "desatualizado", "version": "1.0.1", "version_local": "1.0.0", "version_remote": "1.0.1", "type": "standalone", "size_bytes": 665214649,  "description": "Completem as tarefas. Não confiem em ninguém.", "executable": "Among Us.exe"},
            {"name": "Burglin' Gnomes",     "status": "nao_instalado", "version": "06.10.2026", "type": "standalone", "size_bytes": 3642629202, "description": "Invada casas humanas com seus amigos.", "executable": "Gnomium.exe"},
            {"name": "MECCHA CHAMELEON",    "status": "nao_instalado", "version": "1.2.2", "type": "standalone", "size_bytes": 4437083596, "description": "Pinte seu corpo e engane os caçadores.", "executable": "PenguinHotel.exe"},
        ]

        from launcher.ui.game_card import GameCard
        self._cards: list[GameCard] = []
        for mp in modpacks_dados:
            card = GameCard(mp)
            card.hide()
            painel_layout.addWidget(card)
            self._cards.append(card)

        if self._cards:
            self._cards[0].show()

        corpo_layout.addWidget(self.sidebar)
        corpo_layout.addWidget(borda)
        corpo_layout.addWidget(self._painel, 1)

        layout.addWidget(corpo, 1)

        # Conecta sidebar aos cards
        self.sidebar.item_selecionado.connect(self._selecionar_card)

    def _selecionar_card(self, indice: int):
        for i, card in enumerate(self._cards):
            if i == indice:
                card.show()
            else:
                card.hide()