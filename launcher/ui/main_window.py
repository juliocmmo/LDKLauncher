"""
launcher/ui/main_window.py — Etapa 3 (reescrita completa compatível com os dados reais)

Mudanças em relação à versão anterior:
  - Sidebar emite jogo_selecionado(nome: str), não item_selecionado(indice: int)
  - _cards é dict[str, GameCard] (chave = nome), não list
  - Conecta sinais de download do GameCard ↔ Sidebar
  - Suporte a auto-refresh (slot _on_refresh_silencioso)
"""

import threading

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui  import QPalette, QColor

from launcher.ui.theme import *


class _Sinalizador(QObject):
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
        self._sidebar = Sidebar()
        # NOVO: sinal emite nome do jogo (str), não índice (int)
        self._sidebar.jogo_selecionado.connect(self._selecionar_card)

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

        corpo_layout.addWidget(self._sidebar)
        corpo_layout.addWidget(borda)
        corpo_layout.addWidget(self._stack, 1)
        layout.addWidget(corpo, 1)

        # NOVO: _cards é dict[nome → GameCard]
        self._cards: dict[str, "GameCard"] = {}
        self._jogos_remotos: list[dict] = []

        self._sig = _Sinalizador()
        self._sig.atualizar_texto.connect(self._loading.set_texto)
        self._sig.ui_pronta.connect(self._popular_ui)
        self._sig.erro_conexao.connect(self._loading.set_texto)

        threading.Thread(target=self._inicializar, daemon=True).start()

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

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

        self._jogos_remotos = modpacks
        self._sidebar.popular(modpacks)

        for dados in modpacks:
            nome = dados["name"]
            card = GameCard(dados)
            card.hide()
            self._painel_layout.addWidget(card)
            self._cards[nome] = card

            # Conectar sinais de download
            card.download_iniciado.connect(self._on_download_iniciado)
            card.download_concluido.connect(self._on_download_concluido)
            card.download_cancelado.connect(self._on_download_cancelado)
            card.progresso_download.connect(self._on_progresso_download)

        # Mostrar o primeiro card (ou o primeiro da aba biblioteca)
        primeiro = next(
            (d["name"] for d in modpacks if d.get("status") != "nao_instalado"),
            modpacks[0]["name"] if modpacks else None
        )
        if primeiro:
            self._selecionar_card(primeiro)

        self._stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _selecionar_card(self, nome: str):
        for n, card in self._cards.items():
            card.setVisible(n == nome)
        self._sidebar.selecionar(nome)

    # ------------------------------------------------------------------
    # Coordenação download ↔ sidebar
    # ------------------------------------------------------------------

    def _on_download_iniciado(self, nome: str):
        self._sidebar.marcar_baixando(nome)
        # Desabilitar botão principal dos outros cards
        for n, card in self._cards.items():
            if n != nome:
                card._btn_principal.setEnabled(False)

    def _on_download_concluido(self, nome: str):
        self._sidebar.desmarcar_baixando(nome)
        self._sidebar.atualizar_status_jogo(nome, "atualizado")
        for card in self._cards.values():
            card._btn_principal.setEnabled(True)
        # Repopular sidebar (jogo sai da Loja e vai para Biblioteca)
        self._sidebar.popular(self._jogos_remotos)

    def _on_download_cancelado(self, nome: str):
        self._sidebar.desmarcar_baixando(nome)
        for card in self._cards.values():
            card._btn_principal.setEnabled(True)

    def _on_progresso_download(self, nome: str, pct: int, fase: str, detalhe: str):
        self._sidebar.atualizar_progresso(nome, pct, detalhe)

    # ------------------------------------------------------------------
    # Auto-refresh (chamado pelo timer de 5 min, quando implementado)
    # ------------------------------------------------------------------

    def _on_refresh_silencioso(self, jogos: list[dict]):
        """Atualiza dados sem interromper downloads em andamento."""
        self._jogos_remotos = jogos
        self._sidebar.popular(jogos)
        for dados in jogos:
            nome = dados["name"]
            if nome in self._cards:
                card = self._cards[nome]
                if card._worker is None:
                    card.atualizar_dados(dados)