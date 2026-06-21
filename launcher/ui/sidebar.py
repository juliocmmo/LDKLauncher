from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QLabel, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from launcher.ui.theme import *


class SidebarItem(QWidget):
    clicado = Signal(int)

    def __init__(self, indice: int, nome: str, parent=None):
        super().__init__(parent)
        self.indice = indice
        self.nome = nome
        self.ativo = False
        self.setFixedHeight(SIDEBAR_ITEM_H)
        self.setCursor(Qt.PointingHandCursor)
        self._construir()

    def _construir(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._borda_esq = QFrame()
        self._borda_esq.setFixedWidth(3)
        self._borda_esq.setStyleSheet("background-color: transparent;")
        layout.addWidget(self._borda_esq)

        sigla = "".join(p[0] for p in self.nome.split()[:2]).upper()
        self._frame_icone = QFrame()
        self._frame_icone.setFixedSize(34, 34)
        self._frame_icone.setStyleSheet(
            f"background-color: {COR_BANNER}; border-radius: 6px;"
        )
        icone_layout = QVBoxLayout(self._frame_icone)
        icone_layout.setContentsMargins(0, 0, 0, 0)
        self._label_sigla = QLabel(sigla)
        self._label_sigla.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._label_sigla.setFont(font)
        self._label_sigla.setStyleSheet(f"color: {COR_MUTED}; background: transparent;")
        icone_layout.addWidget(self._label_sigla)
        layout.addSpacing(8)
        layout.addWidget(self._frame_icone)
        layout.addSpacing(8)

        self._label_nome = QLabel(self.nome)
        font_nome = QFont()
        font_nome.setPointSize(FONTE_SIDEBAR_NOME[0])
        font_nome.setBold(True)
        self._label_nome.setFont(font_nome)
        self._label_nome.setStyleSheet(f"color: {COR_TEXTO}; background: transparent;")
        self._label_nome.setWordWrap(True)
        layout.addWidget(self._label_nome, 1)

        self._atualizar_estilo()

    def _atualizar_estilo(self):
        bg = COR_ITEM_ATIVO if self.ativo else COR_SIDEBAR
        self.setStyleSheet(f"background-color: {bg};")
        borda_cor = COR_AZUL_CLARO if self.ativo else "transparent"
        self._borda_esq.setStyleSheet(f"background-color: {borda_cor};")

    def set_ativo(self, ativo: bool):
        self.ativo = ativo
        self._atualizar_estilo()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicado.emit(self.indice)
        super().mousePressEvent(event)


class Sidebar(QWidget):
    item_selecionado = Signal(int)
    aba_alterada = Signal(str)
    refresh_solicitado = Signal()
    config_solicitado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self._items: list[SidebarItem] = []
        self._aba_ativa = "biblioteca"
        self._construir()

    def _construir(self):
        self.setStyleSheet(f"background-color: {COR_SIDEBAR};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label_modpacks = QLabel("MODPACKS")
        font_rot = QFont()
        font_rot.setPointSize(9)
        label_modpacks.setFont(font_rot)
        label_modpacks.setStyleSheet(
            f"color: {COR_MUTED_DARK}; padding: 14px 14px 6px 14px; background: transparent;"
        )
        layout.addWidget(label_modpacks)

        frame_abas = QWidget()
        frame_abas.setFixedHeight(36)
        frame_abas.setStyleSheet("background: transparent;")
        abas_layout = QHBoxLayout(frame_abas)
        abas_layout.setContentsMargins(10, 0, 10, 4)
        abas_layout.setSpacing(4)

        self._btn_biblioteca = QPushButton("Biblioteca")
        self._btn_loja = QPushButton("Loja")

        for btn in (self._btn_biblioteca, self._btn_loja):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            font_btn = QFont()
            font_btn.setPointSize(10)
            btn.setFont(font_btn)

        abas_layout.addWidget(self._btn_biblioteca)
        abas_layout.addWidget(self._btn_loja)
        abas_layout.addStretch()
        layout.addWidget(frame_abas)

        self._btn_biblioteca.clicked.connect(lambda: self._trocar_aba("biblioteca"))
        self._btn_loja.clicked.connect(lambda: self._trocar_aba("loja"))

        layout.addWidget(self._linha_h())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 4px; }
            QScrollBar::handle:vertical { background: #0c2a4a; border-radius: 2px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._container_lista = QWidget()
        self._container_lista.setStyleSheet("background: transparent;")
        self._lista_layout = QVBoxLayout(self._container_lista)
        self._lista_layout.setContentsMargins(0, 0, 0, 0)
        self._lista_layout.setSpacing(0)
        self._lista_layout.addStretch()

        self._scroll.setWidget(self._container_lista)
        layout.addWidget(self._scroll, 1)

        layout.addWidget(self._linha_h())

        rodape = QWidget()
        rodape.setFixedHeight(44)
        rodape.setStyleSheet("background: transparent;")
        rodape_layout = QHBoxLayout(rodape)
        rodape_layout.setContentsMargins(10, 8, 10, 8)
        rodape_layout.setSpacing(4)

        self._btn_config = QPushButton("⚙")
        self._btn_refresh = QPushButton("↻")

        for btn in (self._btn_config, self._btn_refresh):
            btn.setFixedSize(32, 28)
            btn.setCursor(Qt.PointingHandCursor)
            font_btn = QFont()
            font_btn.setPointSize(14)
            btn.setFont(font_btn)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {COR_MUTED_DARK}; border: none; }}"
                f"QPushButton:hover {{ background-color: {COR_ITEM_ATIVO}; color: {COR_MUTED}; border-radius: 4px; }}"
            )

        self._btn_config.clicked.connect(self.config_solicitado)
        self._btn_refresh.clicked.connect(self.refresh_solicitado)

        rodape_layout.addWidget(self._btn_config)
        rodape_layout.addWidget(self._btn_refresh)
        rodape_layout.addStretch()
        layout.addWidget(rodape)

        self._atualizar_estilo_abas()

    def _linha_h(self) -> QFrame:
        linha = QFrame()
        linha.setFrameShape(QFrame.HLine)
        linha.setFixedHeight(1)
        linha.setStyleSheet(f"background-color: {COR_BORDA}; border: none;")
        return linha

    def _trocar_aba(self, aba: str):
        self._aba_ativa = aba
        self._atualizar_estilo_abas()
        self.aba_alterada.emit(aba)

    def _atualizar_estilo_abas(self):
        for btn, nome_aba in ((self._btn_biblioteca, "biblioteca"), (self._btn_loja, "loja")):
            if self._aba_ativa == nome_aba:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {COR_AZUL}; color: {COR_TEXTO}; "
                    f"border: none; border-radius: 6px; font-weight: bold; }}"
                    f"QPushButton:hover {{ background-color: {COR_AZUL_CLARO}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {COR_MUTED}; border: none; border-radius: 6px; }}"
                    f"QPushButton:hover {{ background-color: {COR_ITEM_ATIVO}; }}"
                )

    def popular(self, modpacks: list[dict]):
        self._lista_layout.takeAt(self._lista_layout.count() - 1)

        for i, mp in enumerate(modpacks):
            item = SidebarItem(i, mp["name"])
            item.clicado.connect(self._on_item_clicado)
            self._lista_layout.addWidget(item)
            self._items.append(item)

        self._lista_layout.addStretch()

        if self._items:
            self._items[0].set_ativo(True)

    def _on_item_clicado(self, indice: int):
        for item in self._items:
            item.set_ativo(item.indice == indice)
        self.item_selecionado.emit(indice)