import os
import sys
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QFileDialog, QFrame, QWidget
)
from PySide6.QtGui import QPixmap

from launcher.ui.theme import (
    COR_BG, COR_SIDEBAR, COR_BORDA, COR_ITEM_ATIVO,
    COR_AZUL, COR_AZUL_CLARO, COR_TEXTO, COR_MUTED, COR_MUTED_DARK
)
from launcher.config.settings import DEFAULT_INSTALL_DIR, salvar_config, carregar_config
from launcher.core.antivirus import esta_excluida, adicionar_exclusao


class SetupWindow(QDialog):
    def __init__(self, parent, callback_concluido):
        super().__init__(parent)

        self.callback_concluido = callback_concluido

        config_atual = carregar_config()
        self.pasta_escolhida = config_atual.get("install_dir", DEFAULT_INSTALL_DIR)
        self._modo_config = bool(config_atual)

        titulo = (
            "LDKLauncher — Configurações"
            if self._modo_config
            else "LDKLauncher — Configuração inicial"
        )
        self.setWindowTitle(titulo)
        self.setFixedSize(560, 460)
        self.setModal(True)

        self._aplicar_icone()
        self._build_ui()
        self._aplicar_estilos()

    def _aplicar_icone(self):
        try:
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            icone = os.path.join(base_path, "assets", "ldkf.ico")
            if os.path.exists(icone):
                self.setWindowIcon(QPixmap(icone))
        except Exception:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barra de título ──────────────────────────────────────────────────
        barra = QWidget()
        barra.setObjectName("barra")
        barra.setFixedHeight(36)
        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(16, 0, 16, 0)

        texto_barra = (
            "LDK LAUNCHER — CONFIGURAÇÕES"
            if self._modo_config
            else "LDK LAUNCHER — CONFIGURAÇÃO INICIAL"
        )
        lbl_barra = QLabel(texto_barra)
        lbl_barra.setObjectName("lblBarra")
        barra_layout.addWidget(lbl_barra)
        root.addWidget(barra)

        # ── Corpo ────────────────────────────────────────────────────────────
        corpo = QWidget()
        corpo_layout = QVBoxLayout(corpo)
        corpo_layout.setContentsMargins(32, 24, 32, 24)
        corpo_layout.setSpacing(0)

        # Título e subtítulo
        if not self._modo_config:
            lbl_titulo = QLabel("Bem-vindo ao LDKLauncher!")
            lbl_titulo.setObjectName("titulo")
            corpo_layout.addWidget(lbl_titulo)
            corpo_layout.addSpacing(4)
            lbl_sub = QLabel("Configure onde os modpacks serão instalados antes de continuar.")
            lbl_sub.setObjectName("subtitulo")
            corpo_layout.addWidget(lbl_sub)
        else:
            lbl_titulo = QLabel("Configurações")
            lbl_titulo.setObjectName("titulo")
            corpo_layout.addWidget(lbl_titulo)
            corpo_layout.addSpacing(4)
            lbl_sub = QLabel("Pasta de instalação e exceções do antivírus.")
            lbl_sub.setObjectName("subtitulo")
            corpo_layout.addWidget(lbl_sub)

        corpo_layout.addSpacing(16)
        corpo_layout.addWidget(self._separador())
        corpo_layout.addSpacing(16)

        # ── Seção pasta ──────────────────────────────────────────────────────
        lbl_sec_pasta = QLabel("PASTA DE INSTALAÇÃO")
        lbl_sec_pasta.setObjectName("secLabel")
        corpo_layout.addWidget(lbl_sec_pasta)
        corpo_layout.addSpacing(6)

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

        corpo_layout.addWidget(frame_pasta)
        corpo_layout.addSpacing(6)

        lbl_hint_pasta = QLabel("Os jogos serão instalados dentro desta pasta, cada um em sua subpasta.")
        lbl_hint_pasta.setObjectName("hint")
        lbl_hint_pasta.setWordWrap(True)
        corpo_layout.addWidget(lbl_hint_pasta)
        corpo_layout.addSpacing(18)

        # ── Seção antivírus ──────────────────────────────────────────────────
        lbl_sec_av = QLabel("ANTIVÍRUS")
        lbl_sec_av.setObjectName("secLabel")
        corpo_layout.addWidget(lbl_sec_av)
        corpo_layout.addSpacing(6)

        frame_av = QWidget()
        frame_av.setObjectName("frameItem")
        frame_av_layout = QHBoxLayout(frame_av)
        frame_av_layout.setContentsMargins(14, 10, 14, 10)

        self._check_av = QCheckBox("Excluir esta pasta da verificação do Windows Defender")
        self._check_av.setObjectName("checkAv")

        # Estado inicial do checkbox
        if self._modo_config:
            self._check_av.setChecked(esta_excluida(self.pasta_escolhida))
        else:
            self._check_av.setChecked(True)

        frame_av_layout.addWidget(self._check_av)
        corpo_layout.addWidget(frame_av)
        corpo_layout.addSpacing(6)

        lbl_hint_av = QLabel("Evita falsos positivos com jogos. Vai pedir permissão de administrador (UAC).")
        lbl_hint_av.setObjectName("hint")
        lbl_hint_av.setWordWrap(True)
        corpo_layout.addWidget(lbl_hint_av)
        corpo_layout.addSpacing(18)

        corpo_layout.addWidget(self._separador())
        corpo_layout.addSpacing(16)

        # ── Botão confirmar ──────────────────────────────────────────────────
        texto_btn = "Salvar configurações" if self._modo_config else "Confirmar e continuar"
        self._btn_confirmar_ref = QPushButton(texto_btn)
        self._btn_confirmar_ref.setObjectName("btnConfirmar")
        self._btn_confirmar_ref.setFixedHeight(40)
        self._btn_confirmar_ref.clicked.connect(self._confirmar)
        corpo_layout.addWidget(self._btn_confirmar_ref)

        corpo_layout.addStretch()
        root.addWidget(corpo, stretch=1)

    def _separador(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separador")
        return sep

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
                font-size: {'18px' if self._modo_config else '22px'};
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
            QPushButton#btnConfirmar {{
                background: {COR_AZUL};
                color: {COR_TEXTO};
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton#btnConfirmar:hover {{
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

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(
            self,
            "Escolha onde instalar os modpacks",
            os.path.dirname(self.pasta_escolhida),
        )
        if pasta:
            self.pasta_escolhida = os.path.join(pasta, "LDKLauncher")
            self._lbl_pasta.setText(self.pasta_escolhida)
            # Reavalia checkbox para a nova pasta
            self._check_av.setChecked(esta_excluida(self.pasta_escolhida))

    def _confirmar(self):
        config = carregar_config()
        config["install_dir"] = self.pasta_escolhida
        salvar_config(config)

        if self._check_av.isChecked() and not esta_excluida(self.pasta_escolhida):
            os.makedirs(self.pasta_escolhida, exist_ok=True)
            self._btn_confirmar_ref.setEnabled(False)
            self._btn_confirmar_ref.setText("Configurando antivírus...")
            from PySide6.QtWidgets import QApplication
            t = threading.Thread(
                target=adicionar_exclusao,
                args=(self.pasta_escolhida,),
                daemon=True,
            )
            t.start()
            while t.is_alive():
                QApplication.processEvents()
                t.join(timeout=0.1)

        self.accept()
        self.callback_concluido()