"""Diálogo de instalação no estilo Steam — permite escolher pasta antes de baixar."""
import os
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QFileDialog, QFrame, QWidget
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from launcher.ui.theme import (
    COR_BG, COR_SIDEBAR, COR_BORDA, COR_ITEM_ATIVO,
    COR_AZUL, COR_AZUL_CLARO, COR_TEXTO, COR_MUTED, COR_MUTED_DARK
)
from launcher.config.settings import obter_install_dir
from launcher.core.antivirus import esta_excluida


class InstallDialog(QDialog):
    def __init__(self, parent, nome_jogo: str, install_path: str, tamanho_str: str = ""):
        super().__init__(parent)

        self.nome_jogo        = nome_jogo
        self.install_path     = install_path
        self.tamanho_str      = tamanho_str
        self.pasta_base       = obter_install_dir()
        self.pasta_escolhida  = os.path.join(self.pasta_base, install_path)
        self.confirmado       = False
        self.excluir_antivirus = False

        self.setWindowTitle(f"Instalar {nome_jogo}")
        self.setModal(True)
        self.setFixedWidth(560)

        self._aplicar_icone()
        self._build_ui()
        self._aplicar_estilos()
        self._atualizar_av()  # define altura e visibilidade da seção AV

        # Centraliza na tela
        screen = self.screen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def _aplicar_icone(self):
        try:
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            icone = os.path.join(base_path, "assets", "ldkf.ico")
            if os.path.exists(icone):
                self.setWindowIcon(QPixmap(icone))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra de título ──────────────────────────────────────────────
        barra = QWidget()
        barra.setObjectName("barra")
        barra.setFixedHeight(36)
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(16, 0, 16, 0)
        lbl_barra = QLabel("LDK LAUNCHER — INSTALAR")
        lbl_barra.setObjectName("lblBarra")
        barra_layout.addWidget(lbl_barra)
        root.addWidget(barra)

        # ── Corpo ────────────────────────────────────────────────────────
        corpo = QWidget()
        self._corpo_layout = QVBoxLayout(corpo)
        self._corpo_layout.setContentsMargins(32, 24, 32, 24)
        self._corpo_layout.setSpacing(0)

        # Título
        lbl_titulo = QLabel(f"Instalar {self.nome_jogo}")
        lbl_titulo.setObjectName("titulo")
        self._corpo_layout.addWidget(lbl_titulo)
        self._corpo_layout.addSpacing(4)

        # Subtítulo (tamanho ou texto padrão)
        info = self.tamanho_str if self.tamanho_str else "Configure a instalação abaixo."
        lbl_info = QLabel(info)
        lbl_info.setObjectName("subtitulo")
        self._corpo_layout.addWidget(lbl_info)
        self._corpo_layout.addSpacing(16)

        self._corpo_layout.addWidget(self._sep())
        self._corpo_layout.addSpacing(16)

        # ── Pasta ────────────────────────────────────────────────────────
        lbl_sec_pasta = QLabel("PASTA DE INSTALAÇÃO")
        lbl_sec_pasta.setObjectName("secLabel")
        self._corpo_layout.addWidget(lbl_sec_pasta)
        self._corpo_layout.addSpacing(6)

        frame_pasta = QWidget()
        frame_pasta.setObjectName("frameItem")
        frame_pasta_layout = QHBoxLayout(frame_pasta)
        frame_pasta_layout.setContentsMargins(14, 10, 10, 10)
        frame_pasta_layout.setSpacing(8)

        self._lbl_pasta = QLabel(self.pasta_escolhida)
        self._lbl_pasta.setObjectName("lblPasta")
        self._lbl_pasta.setWordWrap(True)
        frame_pasta_layout.addWidget(self._lbl_pasta, stretch=1)

        btn_alterar = QPushButton("Alterar")
        btn_alterar.setObjectName("btnAlterar")
        btn_alterar.setFixedSize(80, 30)
        btn_alterar.clicked.connect(self._escolher_pasta)
        frame_pasta_layout.addWidget(btn_alterar)

        self._corpo_layout.addWidget(frame_pasta)
        self._corpo_layout.addSpacing(6)

        lbl_hint = QLabel(f"O jogo será instalado em uma subpasta '{self.install_path}'.")
        lbl_hint.setObjectName("hint")
        lbl_hint.setWordWrap(True)
        self._corpo_layout.addWidget(lbl_hint)
        self._corpo_layout.addSpacing(16)

        # ── Seção antivírus (criada oculta) ──────────────────────────────
        self._lbl_sec_av = QLabel("ANTIVÍRUS")
        self._lbl_sec_av.setObjectName("secLabel")

        self._frame_av = QWidget()
        self._frame_av.setObjectName("frameItem")
        frame_av_layout = QHBoxLayout(self._frame_av)
        frame_av_layout.setContentsMargins(14, 10, 14, 10)

        self._check_av = QCheckBox("Excluir esta pasta da verificação do Windows Defender")
        self._check_av.setObjectName("checkAv")
        self._check_av.setChecked(True)
        frame_av_layout.addWidget(self._check_av)

        self._lbl_dica_av = QLabel("Recomendado para jogos. Vai pedir permissão de administrador (UAC).")
        self._lbl_dica_av.setObjectName("hint")
        self._lbl_dica_av.setWordWrap(True)

        self._sep_av = self._sep()

        # Adiciona ao layout mas oculta — _atualizar_av controla visibilidade
        self._corpo_layout.addWidget(self._lbl_sec_av)
        self._corpo_layout.addSpacing(6)
        self._corpo_layout.addWidget(self._frame_av)
        self._corpo_layout.addSpacing(6)
        self._corpo_layout.addWidget(self._lbl_dica_av)
        self._corpo_layout.addSpacing(16)
        self._corpo_layout.addWidget(self._sep_av)
        self._corpo_layout.addSpacing(16)

        # ── Botões ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnCancelar")
        btn_cancelar.setFixedHeight(38)
        btn_cancelar.clicked.connect(self._cancelar)

        self._btn_instalar = QPushButton("Instalar")
        self._btn_instalar.setObjectName("btnInstalar")
        self._btn_instalar.setFixedHeight(38)
        self._btn_instalar.clicked.connect(self._confirmar)

        btn_row.addWidget(btn_cancelar)
        btn_row.addWidget(self._btn_instalar)
        self._corpo_layout.addLayout(btn_row)

        root.addWidget(corpo, stretch=1)

    def _sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separador")
        return sep

    # ------------------------------------------------------------------
    # Visibilidade da seção AV + resize
    # ------------------------------------------------------------------

    def _pasta_e_padrao(self) -> bool:
        return os.path.normpath(self.pasta_escolhida).lower().startswith(
            os.path.normpath(self.pasta_base).lower()
        )

    def _precisa_antivirus(self) -> bool:
        # Se for subpasta da pasta padrão, verifica a pasta BASE (não a subpasta do jogo)
        # para não pedir UAC toda vez que instalar um jogo novo na pasta padrão.
        pasta_a_checar = self.pasta_base if self._pasta_e_padrao() else self.pasta_escolhida
        return not esta_excluida(pasta_a_checar)

    def _atualizar_av(self):
        mostrar = self._precisa_antivirus()
        self._lbl_sec_av.setVisible(mostrar)
        self._frame_av.setVisible(mostrar)
        self._lbl_dica_av.setVisible(mostrar)
        self._sep_av.setVisible(mostrar)
        self._check_av.setChecked(mostrar)  # marcado só quando necessário
        # Ajusta altura da janela
        self.setFixedHeight(520 if mostrar else 390)

    # ------------------------------------------------------------------
    # Estilos
    # ------------------------------------------------------------------

    def _aplicar_estilos(self):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        check_svg = os.path.join(base_path, "assets", "check.svg").replace("\\", "/")
        self.setStyleSheet(f"""
            QDialog {{
                background: {COR_BG};
            }}
            QWidget#barra {{
                background: {COR_SIDEBAR};
            }}
            QLabel#lblBarra {{
                color: {COR_MUTED_DARK};
                font-size: 11px;
                font-weight: bold;
            }}
            QLabel#titulo {{
                color: {COR_TEXTO};
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel#subtitulo {{
                color: {COR_MUTED};
                font-size: 12px;
            }}
            QLabel#secLabel {{
                color: {COR_MUTED_DARK};
                font-size: 10px;
            }}
            QLabel#lblPasta {{
                color: {COR_TEXTO};
                font-size: 12px;
            }}
            QLabel#hint {{
                color: {COR_MUTED_DARK};
                font-size: 11px;
            }}
            QWidget#frameItem {{
                background: {COR_ITEM_ATIVO};
                border-radius: 8px;
            }}
            QFrame#separador {{
                color: {COR_BORDA};
            }}
            QPushButton#btnAlterar {{
                background: {COR_AZUL};
                color: {COR_TEXTO};
                font-size: 12px;
                border-radius: 6px;
                border: none;
            }}
            QPushButton#btnAlterar:hover {{
                background: {COR_AZUL_CLARO};
            }}
            QPushButton#btnCancelar {{
                background: transparent;
                color: {COR_MUTED};
                font-size: 13px;
                border-radius: 8px;
                border: 1px solid {COR_BORDA};
            }}
            QPushButton#btnCancelar:hover {{
                background: {COR_ITEM_ATIVO};
                color: {COR_TEXTO};
                border-color: {COR_MUTED};
            }}
            QPushButton#btnInstalar {{
                background: {COR_AZUL};
                color: {COR_TEXTO};
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton#btnInstalar:hover {{
                background: {COR_AZUL_CLARO};
            }}
            QCheckBox#checkAv {{
                color: {COR_TEXTO};
                font-size: 12px;
                spacing: 8px;
            }}
            QCheckBox#checkAv::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {COR_MUTED_DARK};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox#checkAv::indicator:checked {{
                background: {COR_AZUL};
                border-color: {COR_AZUL};
                image: url("{check_svg}");
            }}
            QCheckBox#checkAv::indicator:hover {{
                border-color: {COR_AZUL_CLARO};
            }}
        """)

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(
            self,
            f"Escolha onde instalar {self.nome_jogo}",
            os.path.dirname(self.pasta_escolhida),
        )
        if pasta:
            self.pasta_escolhida = os.path.join(pasta, self.install_path)
            self._lbl_pasta.setText(self.pasta_escolhida)
            self._atualizar_av()

    def _confirmar(self):
        self.confirmado        = True
        self.excluir_antivirus = self._check_av.isChecked()
        self.accept()

    def _cancelar(self):
        self.confirmado = False
        self.reject()