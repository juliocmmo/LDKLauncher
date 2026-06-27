"""
launcher/ui/sidebar.py — Etapa 3 (adaptado para os dados reais do projeto)

Diferença do protótipo anterior:
  - item_selecionado(indice) → jogo_selecionado(nome_jogo: str)
  - Filtro Biblioteca / Loja por campo "status"
  - Item colorido durante download
  - Rodapé mini-status
"""

from PySide6.QtCore    import Qt, Signal
from PySide6.QtGui     import QPixmap, QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
)

from launcher.ui.theme import (
    COR_SIDEBAR, COR_BORDA, COR_ITEM_ATIVO, COR_AZUL, COR_AZUL_CLARO,
    COR_TEXTO, COR_MUTED, COR_MUTED_DARK,
    STATUS_VERDE, STATUS_LARANJA,
    FONTE_SIDEBAR_NOME, ICONE_SIDEBAR_TAMANHO, ITEM_SIDEBAR_ALTURA,
)
from launcher.config.logger import get_logger

logger = get_logger()

COR_DOWNLOAD_ATIVO = "#1a3a5c"
COR_DOWNLOAD_TEXTO = COR_AZUL_CLARO


class Sidebar(QWidget):
    """
    Sinal emitido: jogo_selecionado(nome_jogo: str)
    """
    jogo_selecionado = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jogos: list[dict]           = []
        self._nome_ativo: str | None      = None
        self._nome_baixando: str | None   = None
        self._itens: dict[str, _ItemSidebar] = {}
        self._aba_atual = "biblioteca"

        self.setFixedWidth(220)
        self.setStyleSheet(f"background: {COR_SIDEBAR};")
        self._construir_ui()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cabeçalho: ícone LDKF à esquerda + "LDKLauncher"
        cab = QWidget()
        cab.setFixedHeight(56)
        cab.setStyleSheet(f"background: {COR_SIDEBAR}; border-bottom: 1px solid {COR_BORDA};")
        cab_layout = QHBoxLayout(cab)
        cab_layout.setContentsMargins(10, 0, 10, 0)
        cab_layout.setSpacing(8)
        cab_layout.addStretch()

        lbl_icone = QLabel()
        lbl_icone.setFixedSize(32, 32)
        lbl_icone.setAlignment(Qt.AlignCenter)
        _carregar_icone_cab(lbl_icone)
        cab_layout.addWidget(lbl_icone)

        lbl_titulo = QLabel("LDKLauncher")
        lbl_titulo.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_titulo.setStyleSheet(f"color: {COR_AZUL_CLARO};")
        cab_layout.addWidget(lbl_titulo)
        cab_layout.addStretch()

        layout.addWidget(cab)

        # Abas
        self._abas = _BarraAbas()
        self._abas.aba_clicada.connect(self._on_aba)
        layout.addWidget(self._abas)

        # Lista scrollável
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {COR_SIDEBAR}; width: 4px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {COR_BORDA}; border-radius: 2px;
            }}
        """)
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout_lista = QVBoxLayout(self._container)
        self._layout_lista.setContentsMargins(0, 4, 0, 4)
        self._layout_lista.setSpacing(0)
        self._layout_lista.addStretch()
        scroll.setWidget(self._container)
        layout.addWidget(scroll, stretch=1)

        # Rodapé mini-status download (oculto enquanto não há download)
        self._rodape = _RodapeDownload()
        self._rodape.setVisible(False)
        layout.addWidget(self._rodape)

        # Rodapé inline: versão + ↻ + ⚙
        from launcher.config.settings import LAUNCHER_VERSION
        _css_btn_fixo = f"""
            QPushButton {{
                background: transparent; color: {COR_MUTED};
                border: none; font-size: 18px;
            }}
            QPushButton:hover {{
                color: {COR_TEXTO};
                background: {COR_ITEM_ATIVO};
                border-radius: 6px;
            }}
        """
        self._lbl_versao_fixo = QLabel(f"v{LAUNCHER_VERSION}")
        self._lbl_versao_fixo.setFont(QFont("Segoe UI", 10))
        self._lbl_versao_fixo.setStyleSheet(f"color: {COR_MUTED}; background: transparent; padding-left: 16px; padding-bottom: 8px;")

        self._btn_sidebar_refresh = QPushButton("↻")
        self._btn_sidebar_refresh.setFixedSize(34, 34)
        self._btn_sidebar_refresh.setCursor(Qt.PointingHandCursor)
        self._btn_sidebar_refresh.setToolTip("Atualizar lista de jogos")
        self._btn_sidebar_refresh.setStyleSheet(_css_btn_fixo)

        self._btn_sidebar_config = QPushButton("⚙")
        self._btn_sidebar_config.setFixedSize(34, 34)
        self._btn_sidebar_config.setCursor(Qt.PointingHandCursor)
        self._btn_sidebar_config.setToolTip("Configurações")
        self._btn_sidebar_config.setStyleSheet(_css_btn_fixo)
        self._btn_sidebar_config.clicked.connect(self._abrir_config)

        rodape_row = QHBoxLayout()
        rodape_row.setContentsMargins(0, 0, 8, 8)
        rodape_row.setSpacing(2)
        rodape_row.addWidget(self._lbl_versao_fixo)
        rodape_row.addStretch()
        rodape_row.addWidget(self._btn_sidebar_refresh)
        rodape_row.addWidget(self._btn_sidebar_config)
        layout.addLayout(rodape_row)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def popular(self, jogos: list[dict]):
        self._jogos = jogos
        self._reconstruir_lista()

    def selecionar(self, nome: str):
        if nome in self._itens:
            self._destacar(nome)

    def marcar_baixando(self, nome: str):
        self._nome_baixando = nome
        if nome in self._itens:
            self._itens[nome].set_baixando(True)
        nome_display = next((j["name"] for j in self._jogos if j["name"] == nome), nome)
        self._rodape.atualizar(nome_display, 0, "Iniciando…")
        self._rodape.setVisible(True)

    def atualizar_progresso(self, nome: str, pct: int, detalhe: str):
        if self._nome_baixando == nome:
            self._rodape.atualizar(nome, pct, detalhe)

    def desmarcar_baixando(self, nome: str):
        if nome in self._itens:
            self._itens[nome].set_baixando(False)
        if self._nome_baixando == nome:
            self._nome_baixando = None
            self._rodape.setVisible(False)

    def atualizar_status_jogo(self, nome: str, novo_status: str):
        if nome in self._itens:
            self._itens[nome].atualizar_status(novo_status)

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _reconstruir_lista(self):
        for item in self._itens.values():
            self._layout_lista.removeWidget(item)
            item.deleteLater()
        self._itens.clear()

        stretch_idx = self._layout_lista.count() - 1
        filtrados   = self._filtrar()

        for dados in filtrados:
            nome = dados["name"]
            item = _ItemSidebar(dados)
            item.clicado.connect(self._on_item_clicado)
            self._itens[nome] = item
            self._layout_lista.insertWidget(stretch_idx, item)
            stretch_idx += 1

        if self._nome_ativo and self._nome_ativo in self._itens:
            self._destacar(self._nome_ativo)
        elif filtrados:
            primeiro = filtrados[0]["name"]
            self._destacar(primeiro)
            self.jogo_selecionado.emit(primeiro)

    def _filtrar(self) -> list[dict]:
        if self._aba_atual == "biblioteca":
            return [j for j in self._jogos if j.get("status") != "nao_instalado"]
        return [j for j in self._jogos if j.get("status") == "nao_instalado"]

    def _on_aba(self, aba: str):
        self._aba_atual = aba
        self._reconstruir_lista()

    def _on_item_clicado(self, nome: str):
        self._destacar(nome)
        self.jogo_selecionado.emit(nome)

    def _destacar(self, nome: str):
        if self._nome_ativo and self._nome_ativo in self._itens:
            self._itens[self._nome_ativo].set_ativo(False)
        self._nome_ativo = nome
        if nome in self._itens:
            self._itens[nome].set_ativo(True)

    def _abrir_config(self):
        from launcher.ui.setup_window import SetupWindow
        dlg = SetupWindow(parent=self, callback_concluido=lambda: None)
        dlg.exec()


# ---------------------------------------------------------------------------
# Barra de abas
# ---------------------------------------------------------------------------

class _BarraAbas(QWidget):
    aba_clicada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setStyleSheet(f"background: {COR_SIDEBAR}; border-bottom: 1px solid {COR_BORDA};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 0)
        layout.setSpacing(4)
        self._btns = {}
        for aba, rot in [("biblioteca", "Biblioteca"), ("loja", "Disponíveis")]:
            btn = QPushButton(rot)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 11))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, a=aba: self._sel(a))
            self._btns[aba] = btn
            layout.addWidget(btn)
        self._sel("biblioteca")

    def _sel(self, aba: str):
        for k, btn in self._btns.items():
            a = k == aba
            btn.setChecked(a)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'transparent' if not a else COR_ITEM_ATIVO};
                    color: {COR_TEXTO if a else COR_MUTED};
                    border: none; border-radius: 4px; padding: 4px 10px;
                }}
                QPushButton:hover {{ color: {COR_TEXTO}; background: {COR_ITEM_ATIVO}; }}
            """)
        self.aba_clicada.emit(aba)


# ---------------------------------------------------------------------------
# Item da sidebar
# ---------------------------------------------------------------------------

class _ItemSidebar(QWidget):
    clicado      = Signal(str)   # nome_jogo
    _icone_pronto = Signal(str)  # caminho do cache — uso interno

    def __init__(self, dados: dict, parent=None):
        super().__init__(parent)
        self._nome     = dados["name"]
        self._status   = dados.get("status", "nao_instalado")
        self._ativo    = False
        self._baixando = False

        self.setFixedHeight(ITEM_SIDEBAR_ALTURA)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # Ícone
        self._lbl_icone = QLabel()
        w, h = ICONE_SIDEBAR_TAMANHO
        self._lbl_icone.setFixedSize(w, h)
        self._lbl_icone.setAlignment(Qt.AlignCenter)
        self._lbl_icone.setStyleSheet(f"background: {COR_BORDA}; border-radius: 4px;")
        self._icone_pronto.connect(self._aplicar_icone_cache)
        self._carregar_icone(dados.get("icon_url", ""))
        layout.addWidget(self._lbl_icone)
        self._aplicar_sigla_fallback()

        # Texto
        col = QVBoxLayout()
        col.setSpacing(2)
        self._lbl_nome = QLabel(self._nome)
        self._lbl_nome.setFont(QFont(*FONTE_SIDEBAR_NOME))
        self._lbl_nome.setStyleSheet(f"color: {COR_TEXTO};")
        self._lbl_sub = QLabel()
        self._lbl_sub.setFont(QFont("Segoe UI", 10))
        self.atualizar_status(self._status)
        col.addWidget(self._lbl_nome)
        col.addWidget(self._lbl_sub)
        layout.addLayout(col, stretch=1)

        self._refresh_bg()

    def _carregar_icone(self, url: str):
        """Tenta carregar ícone do cache local, invalidando se a URL mudou."""
        if not url:
            return
        from pathlib import Path
        from launcher.config.settings import CONFIG_DIR
        cache = Path(CONFIG_DIR) / "icons" / f"{self._nome}.png"
        meta  = cache.with_suffix(".meta")

        if cache.exists() and meta.exists():
            try:
                if meta.read_text(encoding="utf-8").strip() != url:
                    cache.unlink()
                    meta.unlink()
            except Exception:
                pass

        if cache.exists():
            w, h = ICONE_SIDEBAR_TAMANHO
            pix = QPixmap(str(cache)).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if not pix.isNull():
                self._lbl_icone.setPixmap(pix)
                return
        self._baixar_icone_bg(url, cache)

    def _baixar_icone_bg(self, url: str, cache):
        import threading
        def _dl():
            try:
                from shared.drive_utils import baixar_asset_drive
                ok = baixar_asset_drive(url, cache)
                if ok:
                    # Salva meta para invalidação de cache
                    meta = cache.with_suffix(".meta")
                    meta.write_text(url, encoding="utf-8")
                    self._icone_pronto.emit(str(cache))
            except Exception:
                pass
        threading.Thread(target=_dl, daemon=True).start()

    def _aplicar_icone_cache(self, caminho: str):
        pix = QPixmap(caminho)
        if not pix.isNull():
            w, h = ICONE_SIDEBAR_TAMANHO
            pix = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._lbl_icone.setPixmap(pix)
            self._lbl_icone.setText("")  # remove sigla se ícone carregou

    def _aplicar_sigla_fallback(self):
        """Exibe as iniciais do nome enquanto o ícone não carrega."""
        if self._lbl_icone.pixmap() and not self._lbl_icone.pixmap().isNull():
            return
        palavras = self._nome.split()
        sigla = (palavras[0][0] + palavras[1][0]).upper() if len(palavras) >= 2 else self._nome[:2].upper()
        self._lbl_icone.setText(sigla)
        self._lbl_icone.setStyleSheet(f"""
            background: {COR_BORDA};
            border-radius: 4px;
            color: {COR_MUTED};
            font-size: 14px;
            font-weight: bold;
        """)

    def atualizar_status(self, status: str):
        self._status = status
        if status == "atualizado":
            self._lbl_sub.setText("Instalado")
            self._lbl_sub.setStyleSheet(f"color: {STATUS_VERDE};")
        elif status == "desatualizado":
            self._lbl_sub.setText("Atualização disponível")
            self._lbl_sub.setStyleSheet(f"color: {STATUS_LARANJA};")
        else:
            self._lbl_sub.setText("Não instalado")
            self._lbl_sub.setStyleSheet(f"color: {COR_MUTED_DARK};")

    def set_ativo(self, v: bool):
        self._ativo = v
        self._refresh_bg()

    def set_baixando(self, v: bool):
        self._baixando = v
        if v:
            self._lbl_nome.setStyleSheet(f"color: {COR_DOWNLOAD_TEXTO};")
            self._lbl_sub.setText("Baixando…")
            self._lbl_sub.setStyleSheet(f"color: {COR_DOWNLOAD_TEXTO};")
        else:
            self._lbl_nome.setStyleSheet(f"color: {COR_TEXTO};")
            self.atualizar_status(self._status)
        self._refresh_bg()

    def _refresh_bg(self):
        if self._baixando:
            bg     = COR_DOWNLOAD_ATIVO
            borda  = "transparent"
        elif self._ativo:
            bg     = COR_ITEM_ATIVO
            borda  = COR_AZUL_CLARO
        else:
            bg     = "transparent"
            borda  = "transparent"
        self.setStyleSheet(f"""
            _ItemSidebar {{
                background: {bg};
                border-left: 3px solid {borda};
            }}
            _ItemSidebar:hover {{ background: {COR_ITEM_ATIVO}; }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicado.emit(self._nome)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Rodapé de download
# ---------------------------------------------------------------------------

class _RodapeDownload(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet(f"""
            _RodapeDownload {{
                background: {COR_DOWNLOAD_ATIVO};
                border-top: 1px solid {COR_BORDA};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)
        self._lbl_nome = QLabel()
        self._lbl_nome.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._lbl_nome.setStyleSheet(f"color: {COR_DOWNLOAD_TEXTO}; background: transparent;")
        self._lbl_det = QLabel()
        self._lbl_det.setFont(QFont("Segoe UI", 9))
        self._lbl_det.setStyleSheet(f"color: {COR_MUTED}; background: transparent;")
        layout.addWidget(self._lbl_nome)
        layout.addWidget(self._lbl_det)

    def atualizar(self, nome: str, pct: int, detalhe: str):
        self._lbl_nome.setText(f"⬇  {nome}")
        self._lbl_det.setText(f"{pct}%  {detalhe}" if pct else detalhe)

# ---------------------------------------------------------------------------
# Helper: carrega ícone do cabeçalho da sidebar
# ---------------------------------------------------------------------------

def _carregar_icone_cab(label):
    """Carrega ldkf.ico da pasta assets do launcher."""
    import sys
    from pathlib import Path
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import Qt

    # Tenta localizar em assets/ relativo ao executável ou ao projeto
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    candidatos = [
        base / "assets" / "ldkf.ico",
        base / "assets" / "ldkf.png",
        Path(__file__).parent.parent / "assets" / "ldkf.ico",
    ]
    for caminho in candidatos:
        if caminho.exists():
            pix = QPixmap(str(caminho)).scaled(
                32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            if not pix.isNull():
                label.setPixmap(pix)
                return