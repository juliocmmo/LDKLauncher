from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QFont

from launcher.ui.theme import *

TEXTOS_BOTAO = {
    "nao_instalado": "Baixar",
    "atualizado":    "Jogar",
    "desatualizado": "Atualizar",
}

CORES_STATUS = {
    "nao_instalado": COR_MUTED,
    "atualizado":    COR_STATUS_OK,
    "desatualizado": COR_STATUS_OUT,
}


class GameCard(QWidget):
    def __init__(self, modpack: dict, parent=None):
        super().__init__(parent)
        self.modpack = modpack
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._construir()
        self._atualizar_visual()

    def _construir(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Área da thumbnail (placeholder por enquanto)
        self._thumb_area = _ThumbnailArea()
        layout.addWidget(self._thumb_area, 1)

        # Painel inferior de informações
        painel = QWidget()
        painel.setStyleSheet(f"background-color: {COR_BG};")
        painel_layout = QVBoxLayout(painel)
        painel_layout.setContentsMargins(20, 12, 20, 16)
        painel_layout.setSpacing(0)

        # Nome + versão
        frame_titulo = QWidget()
        frame_titulo.setStyleSheet("background: transparent;")
        titulo_layout = QVBoxLayout(frame_titulo)
        titulo_layout.setContentsMargins(0, 0, 0, 8)
        titulo_layout.setSpacing(2)

        self._label_nome = QLabel(self.modpack.get("name", ""))
        font_nome = QFont()
        font_nome.setPointSize(FONTE_CARD_NOME[0])
        font_nome.setBold(True)
        self._label_nome.setFont(font_nome)
        self._label_nome.setStyleSheet(f"color: {COR_TEXTO}; background: transparent;")
        titulo_layout.addWidget(self._label_nome)

        self._label_versao = QLabel("")
        font_versao = QFont()
        font_versao.setPointSize(FONTE_VERSAO[0])
        self._label_versao.setFont(font_versao)
        self._label_versao.setStyleSheet(f"color: {COR_MUTED}; background: transparent;")
        titulo_layout.addWidget(self._label_versao)

        painel_layout.addWidget(frame_titulo)

        # Linha separadora
        linha = QFrame()
        linha.setFrameShape(QFrame.HLine)
        linha.setFixedHeight(1)
        linha.setStyleSheet(f"background-color: {COR_BORDA}; border: none;")
        painel_layout.addWidget(linha)

        # Botões
        frame_acoes = QWidget()
        frame_acoes.setStyleSheet("background: transparent;")
        acoes_layout = QHBoxLayout(frame_acoes)
        acoes_layout.setContentsMargins(0, 10, 0, 10)
        acoes_layout.setSpacing(10)

        self.botao = QPushButton("")
        self.botao.setFixedSize(120, BOTAO_ALTURA)
        self.botao.setCursor(Qt.PointingHandCursor)
        self.botao.setStyleSheet(
            f"QPushButton {{ background-color: {COR_AZUL}; color: {COR_TEXTO}; "
            f"border: none; border-radius: 8px; font-size: 15px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {COR_AZUL_CLARO}; }}"
            f"QPushButton:disabled {{ background-color: {COR_BORDA}; color: {COR_MUTED_DARK}; }}"
        )
        self.botao.clicked.connect(self._acao)
        acoes_layout.addWidget(self.botao)

        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.setFixedSize(110, BOTAO_ALTURA)
        self.botao_cancelar.setCursor(Qt.PointingHandCursor)
        self.botao_cancelar.setStyleSheet(
            f"QPushButton {{ background: transparent; color: #e05555; "
            f"border: 1px solid #7a1a1a; border-radius: 8px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #1a0a0a; }}"
        )
        self.botao_cancelar.hide()

        self.botao_fechar_jogo = QPushButton("Fechar jogo")
        self.botao_fechar_jogo.setFixedSize(120, BOTAO_ALTURA)
        self.botao_fechar_jogo.setCursor(Qt.PointingHandCursor)
        self.botao_fechar_jogo.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COR_STATUS_OUT}; "
            f"border: 1px solid #7a4a00; border-radius: 8px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #1a1000; }}"
        )
        self.botao_fechar_jogo.hide()

        acoes_layout.addWidget(self.botao_cancelar)
        acoes_layout.addWidget(self.botao_fechar_jogo)
        acoes_layout.addStretch()

        self.botao_desinstalar = QPushButton("Desinstalar")
        self.botao_desinstalar.setFixedSize(100, BOTAO_ALTURA)
        self.botao_desinstalar.setCursor(Qt.PointingHandCursor)
        self.botao_desinstalar.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COR_MUTED_DARK}; "
            f"border: 1px solid {COR_BORDA}; border-radius: 8px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #1a0a0a; color: #e05555; border-color: #7a1a1a; }}"
        )
        acoes_layout.addWidget(self.botao_desinstalar)
        painel_layout.addWidget(frame_acoes)

        # Metadados
        frame_meta = QWidget()
        frame_meta.setStyleSheet("background: transparent;")
        meta_layout = QHBoxLayout(frame_meta)
        meta_layout.setContentsMargins(0, 0, 0, 10)
        meta_layout.setSpacing(0)

        self._meta_tamanho     = self._meta_item(meta_layout, "Tamanho", self._formatar_tamanho())
        self._meta_versao      = self._meta_item(meta_layout, "Versão", "—")
        self._meta_tipo        = self._meta_item(meta_layout, "Tipo", self.modpack.get("type", "standalone").capitalize())
        self._meta_status      = self._meta_item(meta_layout, "Status", "—")
        self._meta_ultimo_jogo = self._meta_item(meta_layout, "Última vez jogado", "—")
        meta_layout.addStretch()
        painel_layout.addWidget(frame_meta)

        # Descrição
        descricao = self.modpack.get("description", "")
        if descricao:
            self._label_descricao = QLabel(descricao)
            font_desc = QFont()
            font_desc.setPointSize(FONTE_DESCRICAO[0])
            self._label_descricao.setFont(font_desc)
            self._label_descricao.setStyleSheet(f"color: {COR_MUTED}; background: transparent;")
            self._label_descricao.setWordWrap(True)
            painel_layout.addWidget(self._label_descricao)

        layout.addWidget(painel)

    def _meta_item(self, layout: QHBoxLayout, rotulo: str, valor: str):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container.setMinimumWidth(110)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 16, 0)
        vbox.setSpacing(2)

        lbl_rot = QLabel(rotulo)
        font_rot = QFont()
        font_rot.setPointSize(FONTE_META_ROTULO[0])
        lbl_rot.setFont(font_rot)
        lbl_rot.setStyleSheet(f"color: {COR_MUTED_DARK};")
        vbox.addWidget(lbl_rot)

        lbl_val = QLabel(valor)
        font_val = QFont()
        font_val.setPointSize(FONTE_META_VALOR[0])
        lbl_val.setFont(font_val)
        lbl_val.setStyleSheet(f"color: {COR_TEXTO};")
        vbox.addWidget(lbl_val)

        layout.addWidget(container)
        return lbl_val

    def _formatar_tamanho(self) -> str:
        size = self.modpack.get("size_bytes", 0)
        if size >= 1_073_741_824:
            return f"{size / 1_073_741_824:.2f} GB"
        elif size >= 1_048_576:
            return f"{size / 1_048_576:.0f} MB"
        return f"{size} B"

    def _atualizar_visual(self):
        status = self.modpack.get("status", "nao_instalado")
        v_local  = self.modpack.get("version_local", "—")
        v_remote = self.modpack.get("version_remote", self.modpack.get("version", "—"))

        self.botao.setText(TEXTOS_BOTAO.get(status, ""))

        if status == "nao_instalado":
            self._label_versao.setText(f"v{v_remote} disponível")
            self.botao_desinstalar.hide()
        elif status == "atualizado":
            self._label_versao.setText(f"v{v_local} instalado  •  v{v_remote} disponível")
            self.botao_desinstalar.show()
        else:
            self._label_versao.setText(f"v{v_local} instalado  •  v{v_remote} disponível")
            self.botao_desinstalar.show()

        cor_status = CORES_STATUS.get(status, COR_MUTED)
        texto_status = {"nao_instalado": "Não instalado", "atualizado": "✓ Atualizado", "desatualizado": "Desatualizado"}.get(status, "—")
        self._meta_status.setText(texto_status)
        self._meta_status.setStyleSheet(f"color: {cor_status};")
        self._meta_versao.setText(v_local if status != "nao_instalado" else "—")

    def _acao(self):
        status = self.modpack.get("status", "nao_instalado")
        if status == "atualizado":
            self._jogar()
        elif status in ("nao_instalado", "desatualizado"):
            print(f"[TODO] Iniciar download de {self.modpack['name']}")

    def _jogar(self):
        from launcher.core.game_launcher import iniciar_jogo
        from launcher.config.settings import obter_install_dir_jogo
        nome = self.modpack["name"]
        pasta = obter_install_dir_jogo(nome)
        exe = self.modpack.get("executable", "")
        sucesso = iniciar_jogo(pasta, exe)
        if sucesso:
            self.botao_fechar_jogo.show()
        else:
            print(f"[ERRO] Não foi possível iniciar {nome}")


class _ThumbnailArea(QWidget):
    """Área de thumbnail com placeholder e gradiente na base."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(200)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fundo placeholder
        painter.fillRect(self.rect(), QColor(COR_BANNER))

        # Gradiente escuro na base (simula o visual do CTk)
        grad = QLinearGradient(0, self.height() * 0.5, 0, self.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(COR_BG))
        painter.fillRect(self.rect(), grad)

        painter.end()