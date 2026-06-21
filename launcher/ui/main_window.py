import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPalette, QColor

from launcher.ui.theme import *


class _Sinalizador(QObject):
    """Objeto auxiliar para emitir signals de uma thread de fundo."""
    atualizar_texto  = Signal(str)
    ui_pronta        = Signal(list)
    erro_conexao     = Signal(str)


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
    def _btn_css(color, hover_bg, hover_color):
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

        corpo = QWidget()
        corpo_layout = QHBoxLayout(corpo)
        corpo_layout.setContentsMargins(0, 0, 0, 0)
        corpo_layout.setSpacing(0)

        from launcher.ui.sidebar import Sidebar
        self.sidebar = Sidebar()
        self.sidebar.item_selecionado.connect(self._selecionar_card)

        borda = QFrame()
        borda.setFixedWidth(1)
        borda.setStyleSheet(f"background-color: {COR_BORDA};")

        self._stack = QStackedWidget()

        from launcher.ui.loading_widget import LoadingWidget
        self._loading = LoadingWidget()
        self._stack.addWidget(self._loading)   # índice 0

        self._painel = QWidget()
        self._painel.setStyleSheet(f"background-color: {COR_BG};")
        self._painel_layout = QVBoxLayout(self._painel)
        self._painel_layout.setContentsMargins(0, 0, 0, 0)
        self._painel_layout.setSpacing(0)
        self._stack.addWidget(self._painel)    # índice 1

        corpo_layout.addWidget(self.sidebar)
        corpo_layout.addWidget(borda)
        corpo_layout.addWidget(self._stack, 1)

        layout.addWidget(corpo, 1)

        self._cards = []

        # Sinalizador para comunicação entre thread e UI
        self._sig = _Sinalizador()
        self._sig.atualizar_texto.connect(self._loading.set_texto)
        self._sig.ui_pronta.connect(self._popular_ui)
        self._sig.erro_conexao.connect(self._loading.set_texto)

        threading.Thread(target=self._inicializar, daemon=True).start()

    def _inicializar(self):
        from launcher.core.version_checker import (
            buscar_versao_remota, carregar_versao_local, verificar_status_modpacks
        )

        self._sig.atualizar_texto.emit("Buscando atualizações...")

        remoto = buscar_versao_remota()
        local  = carregar_versao_local()

        if remoto is None:
            self._sig.erro_conexao.emit("Sem conexão. Verifique sua internet.")
            return

        modpacks = verificar_status_modpacks(remoto, local)
        self._sig.ui_pronta.emit(modpacks)

    def _popular_ui(self, modpacks: list):
        from launcher.ui.game_card import GameCard

        self.sidebar.popular(modpacks)

        for mp in modpacks:
            card = GameCard(mp)
            card.hide()
            self._painel_layout.addWidget(card)
            self._cards.append(card)

        if self._cards:
            self._cards[0].show()

        self._stack.setCurrentIndex(1)

    def _selecionar_card(self, indice: int):
        for i, card in enumerate(self._cards):
            if i == indice:
                card.show()
            else:
                card.hide()