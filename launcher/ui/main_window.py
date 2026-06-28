"""
launcher/ui/main_window.py — Etapa 5

Mudanças em relação à Etapa 4:
  - _Sinalizador ganha refresh_silencioso e toast
  - _TitleBar ganha botão ↻ (referência guardada em self._title_bar)
  - QTimer de 5 minutos para auto-refresh silencioso
  - _refresh_bg: busca version.json remoto em background (auto e manual)
  - _on_refresh_manual: chamado pelo botão ↻, emite toast ao concluir
  - _on_refresh_silencioso: atualizado para registrar cards novos
  - _mostrar_toast: notificação discreta no canto inferior direito (3s)

Correções aplicadas pós code-review:
  - #8:  _on_erro emite download_erro (sinal dedicado) em vez de download_cancelado
  - #16: removida verificação redundante de card._worker em _on_refresh_silencioso
  - Botão maximizar/restaurar adicionado à _TitleBar
  - Resize nativo por borda via nativeEvent (WM_NCHITTEST)
"""

import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.ui.game_card import GameCard

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui  import QPalette, QColor

from launcher.ui.theme import *


class _Sinalizador(QObject):
    atualizar_texto    = Signal(str)
    ui_pronta          = Signal(list)
    erro_conexao       = Signal(str)
    refresh_silencioso = Signal(list)
    toast              = Signal(str)
    notificacao        = Signal(str, str, str, bool)  # titulo, texto, icone_path, sucesso


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

        self._btn_max = QPushButton("❐")
        self._btn_max.setFixedSize(32, 32)
        self._btn_max.setCursor(Qt.PointingHandCursor)
        self._btn_max.setStyleSheet(self._btn_css(COR_MUTED, COR_ITEM_ATIVO, COR_TEXTO))
        self._btn_max.clicked.connect(self._toggle_maximizar)
        layout.addWidget(self._btn_max)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(32, 32)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(self._btn_css(COR_MUTED, "#8b1a1a", COR_TEXTO))
        btn_close.clicked.connect(self.window().close)
        layout.addWidget(btn_close)

    def _toggle_maximizar(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
            self._btn_max.setText("❐")
        else:
            win.showMaximized()
            self._btn_max.setText("❒")

    @staticmethod
    def _btn_css(color, hover_bg, hover_color):
        return (
            f"QPushButton {{ background: transparent; color: {color}; border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ background-color: {hover_bg}; color: {hover_color}; }}"
        )

    # Arrastar é controlado pelo Windows via HTCAPTION no nativeEvent.
    # Os métodos de mouse não precisam mais mover a janela manualmente.
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def cursor_sobre_btn_max(self, pos_local) -> bool:
        """Retorna True se pos_local (relativa à title bar) está sobre o botão maximizar."""
        return self._btn_max.geometry().contains(pos_local)


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

        # Guardar referência para conectar o botão ↻ depois da UI estar pronta
        self._title_bar = _TitleBar(root)
        layout.addWidget(self._title_bar)

        corpo = QWidget()
        corpo_layout = QHBoxLayout(corpo)
        corpo_layout.setContentsMargins(0, 0, 0, 0)
        corpo_layout.setSpacing(0)

        from launcher.ui.sidebar import Sidebar
        self._sidebar = Sidebar()
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

        self._cards: dict[str, "GameCard"] = {}
        self._jogos_remotos: list[dict] = []

        self._sig = _Sinalizador()
        self._sig.atualizar_texto.connect(self._loading.set_texto)
        self._sig.ui_pronta.connect(self._popular_ui)
        self._sig.erro_conexao.connect(self._loading.set_texto)
        self._sig.refresh_silencioso.connect(self._on_refresh_silencioso)
        self._sig.toast.connect(self._mostrar_toast)
        self._sig.notificacao.connect(self._mostrar_notificacao)

        # Timer de auto-refresh a cada 5 minutos (inicia somente após UI pronta)
        self._timer_refresh = QTimer(self)
        self._timer_refresh.setInterval(5 * 60 * 1000)
        self._timer_refresh.timeout.connect(self._refresh_bg)
        self._refresh_em_andamento = False

        # NÃO chama _inicializar aqui — quem chama é o main.py

    # ------------------------------------------------------------------
    # Estilos Win32 para Snap Assist
    # ------------------------------------------------------------------

    def _aplicar_estilos_win32(self):
        """
        Remove WS_POPUP (setado pelo Qt com FramelessWindowHint) e aplica
        os flags de janela normal. O Windows Shell só habilita Snap Assist
        para janelas não-popup com WS_THICKFRAME | WS_CAPTION.
        A borda nativa é suprimida visualmente via WM_NCCALCSIZE.
        """
        import sys
        if sys.platform != "win32":
            return
        import ctypes
        GWL_STYLE      = -16
        WS_POPUP       = 0x80000000
        WS_THICKFRAME  = 0x00040000
        WS_CAPTION     = 0x00C00000
        WS_SYSMENU     = 0x00080000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000

        hwnd = int(self.winId())
        estilo = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)

        # Remove WS_POPUP, adiciona flags de janela overlapped normal
        novo = (estilo & 0xFFFFFFFF & ~WS_POPUP) | \
               WS_THICKFRAME | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, novo)

        SWP_NOMOVE       = 0x0002
        SWP_NOSIZE       = 0x0001
        SWP_NOZORDER     = 0x0004
        SWP_FRAMECHANGED = 0x0020
        ctypes.windll.user32.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
        )

    def showEvent(self, event):
        super().showEvent(event)
        # Aplicar após a janela ser exibida garante que o DWM já registrou
        # o HWND e os flags WS_THICKFRAME | WS_CAPTION têm efeito completo.
        self._aplicar_estilos_win32()

    # ------------------------------------------------------------------
    # Resize nativo por borda (Windows — WM_NCHITTEST)
    # ------------------------------------------------------------------

    _RESIZE_MARGIN = 8

    def nativeEvent(self, eventType, message):
        import ctypes
        from ctypes.wintypes import MSG

        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents

            # Remove a borda nativa visualmente, mas mantém WS_THICKFRAME
            # ativo para que Snap Assist e animações funcionem.
            # wParam == 0: consulta simples → retorna 0 (sem borda)
            # wParam == 1: cálculo de Snap/maximizar → deixa o Windows processar
            if msg.message == 0x0083:  # WM_NCCALCSIZE
                return True, 0

            if msg.message in (0x00A0, 0x0085):  # WM_NCMOUSEMOVE, WM_NCPAINT
                return True, 0

            if msg.message == 0x00A1:  # WM_NCLBUTTONDOWN
                if msg.wParam == 9:   # HTMAXBUTTON — intercepta clique, suprime highlight branco
                    self._title_bar._toggle_maximizar()
                    return True, 0

            if msg.message == 0x0084:  # WM_NCHITTEST
                x = ctypes.c_short(msg.lParam & 0xFFFF).value
                y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                geo = self.geometry()
                m   = self._RESIZE_MARGIN

                esq   = x < geo.x() + m
                dir_  = x > geo.x() + geo.width()  - m
                topo  = y < geo.y() + m
                baixo = y > geo.y() + geo.height() - m

                if topo  and esq:  return True, 13  # HTTOPLEFT
                if topo  and dir_: return True, 14  # HTTOPRIGHT
                if baixo and esq:  return True, 16  # HTBOTTOMLEFT
                if baixo and dir_: return True, 17  # HTBOTTOMRIGHT
                if esq:            return True, 10  # HTLEFT
                if dir_:           return True, 11  # HTRIGHT
                if topo:           return True, 12  # HTTOP
                if baixo:          return True, 15  # HTBOTTOM

                # Região da title bar: ativa arrastar nativo + Snap Assist
                barra_h = self._title_bar.height()
                if y < geo.y() + barra_h:
                    from PySide6.QtCore import QPoint
                    cx = x - geo.x()
                    cy = y - geo.y()
                    # Hover sobre botão maximizar → Snap Layouts (Windows 11)
                    if self._title_bar.cursor_sobre_btn_max(QPoint(cx, cy)):
                        return True, 9  # HTMAXBUTTON
                    # Outros botões → Qt processa o clique
                    if self._title_bar.childAt(cx, cy) is not None:
                        return True, 1  # HTCLIENT
                    return True, 2  # HTCAPTION

        return super().nativeEvent(eventType, message)

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

            card.download_iniciado.connect(self._on_download_iniciado)
            card.download_concluido.connect(self._on_download_concluido)
            card.download_cancelado.connect(self._on_download_cancelado)
            card.download_erro.connect(self._on_download_erro)
            card.progresso_download.connect(self._on_progresso_download)
            card.desinstalado.connect(self._on_desinstalado)

        primeiro = next(
            (d["name"] for d in modpacks if d.get("status") != "nao_instalado"),
            modpacks[0]["name"] if modpacks else None
        )
        if primeiro:
            self._selecionar_card(primeiro)

        self._stack.setCurrentIndex(1)

        # Iniciar timer de auto-refresh e conectar botão ↻ do rodapé da sidebar
        self._timer_refresh.start()
        self._sidebar._btn_sidebar_refresh.clicked.connect(self._on_refresh_manual)

        # Verificar update do launcher 15s após UI pronta (não bloqueia o startup)
        QTimer.singleShot(15_000, self._verificar_update_launcher_bg)

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
        for n, card in self._cards.items():
            if n != nome:
                card._btn_principal.setEnabled(False)
                card._btn_desinstalar.setEnabled(False)

    def _on_download_concluido(self, nome: str):
        self._sidebar.desmarcar_baixando(nome)
        self._sidebar.atualizar_status_jogo(nome, "atualizado")
        for card in self._cards.values():
            card._btn_principal.setEnabled(True)
            card._btn_desinstalar.setEnabled(True)
        self._sidebar.popular(self._jogos_remotos)

        from launcher.config.settings import CONFIG_DIR
        icone_png = Path(CONFIG_DIR) / "icons" / f"{nome}.png"
        icone_jpg = Path(CONFIG_DIR) / "thumbs" / f"{nome}.jpg"
        icone = str(icone_png) if icone_png.exists() else str(icone_jpg)
        self._sig.notificacao.emit(
            "Download concluído",
            f"{nome} está pronto para jogar.",
            icone,
            True,
        )

    def _on_download_cancelado(self, nome: str):
        self._sidebar.desmarcar_baixando(nome)
        for card in self._cards.values():
            card._btn_principal.setEnabled(True)
            card._btn_desinstalar.setEnabled(True)

    def _on_download_erro(self, nome: str):
        self._sidebar.desmarcar_baixando(nome)
        for card in self._cards.values():
            card._btn_principal.setEnabled(True)
            card._btn_desinstalar.setEnabled(True)

    def _on_progresso_download(self, nome: str, pct: int, fase: str, detalhe: str):
        self._sidebar.atualizar_progresso(nome, pct, detalhe)

    def _on_desinstalado(self, nome: str):
        """Move o jogo de Biblioteca → Disponíveis e seleciona outro card."""
        for dados in self._jogos_remotos:
            if dados["name"] == nome:
                dados["status"] = "nao_instalado"
                break

        self._sidebar.popular(self._jogos_remotos)

        outro = next(
            (n for n, c in self._cards.items() if n != nome and c.status != "nao_instalado"),
            next((n for n in self._cards if n != nome), None)
        )
        if outro:
            self._selecionar_card(outro)

    # ------------------------------------------------------------------
    # Auto-refresh silencioso (timer de 5 min)
    # ------------------------------------------------------------------

    def _on_refresh_silencioso(self, jogos: list[dict]):
        """Atualiza dados sem interromper downloads em andamento."""
        self._jogos_remotos = jogos
        self._sidebar.popular(jogos)
        for dados in jogos:
            nome = dados["name"]
            if nome in self._cards:
                card = self._cards[nome]
                card.atualizar_dados(dados)
            else:
                from launcher.ui.game_card import GameCard
                card = GameCard(dados)
                card.hide()
                self._painel_layout.addWidget(card)
                self._cards[nome] = card
                card.download_iniciado.connect(self._on_download_iniciado)
                card.download_concluido.connect(self._on_download_concluido)
                card.download_cancelado.connect(self._on_download_cancelado)
                card.download_erro.connect(self._on_download_erro)
                card.progresso_download.connect(self._on_progresso_download)
                card.desinstalado.connect(self._on_desinstalado)
        self._refresh_em_andamento = False

    # ------------------------------------------------------------------
    # Refresh background (compartilhado entre auto e manual)
    # ------------------------------------------------------------------

    def _verificar_update_launcher_bg(self):
        """Verifica em background se há nova versão do launcher e notifica via popup."""
        def _checar():
            try:
                from launcher.core.auto_updater import obter_versao_remota, _versao_tuple
                from launcher.config.settings import LAUNCHER_VERSION
                versao_remota = obter_versao_remota()
                if not versao_remota:
                    return
                if _versao_tuple(versao_remota) > _versao_tuple(LAUNCHER_VERSION.lstrip("v")):
                    self._sig.notificacao.emit(
                        "Atualização disponível",
                        f"Nova versão v{versao_remota} disponível. "
                        f"Reinicie o launcher para atualizar.",
                        "",
                        True,
                    )
            except Exception:
                pass

        threading.Thread(target=_checar, daemon=True).start()

    def _refresh_bg(self):
        """Dispara busca remota em background. Usado pelo timer de 5 min."""
        if self._refresh_em_andamento:
            return
        self._refresh_em_andamento = True

        def _buscar():
            from launcher.core.version_checker import (
                buscar_versao_remota, carregar_versao_local, verificar_status_modpacks
            )
            remoto = buscar_versao_remota()
            if remoto is None:
                self._refresh_em_andamento = False
                return
            local    = carregar_versao_local()
            modpacks = verificar_status_modpacks(remoto, local)
            self._sig.refresh_silencioso.emit(modpacks)

        threading.Thread(target=_buscar, daemon=True).start()

    # ------------------------------------------------------------------
    # Refresh manual (botão ↻)
    # ------------------------------------------------------------------

    def _on_refresh_manual(self):
        """Chamado pelo botão ↻ na title bar. Igual ao auto, mas emite toast."""
        if self._refresh_em_andamento:
            return
        self._refresh_em_andamento = True

        def _buscar():
            from launcher.core.version_checker import (
                buscar_versao_remota, carregar_versao_local, verificar_status_modpacks
            )
            remoto = buscar_versao_remota()
            if remoto is None:
                self._refresh_em_andamento = False
                self._sig.toast.emit("Sem conexão. Não foi possível atualizar.")
                return
            local    = carregar_versao_local()
            modpacks = verificar_status_modpacks(remoto, local)
            self._sig.refresh_silencioso.emit(modpacks)
            self._sig.toast.emit("Lista de jogos atualizada.")

        threading.Thread(target=_buscar, daemon=True).start()

    # ------------------------------------------------------------------
    # Toast
    # ------------------------------------------------------------------

    def _mostrar_toast(self, mensagem: str):
        """Notificação discreta no canto inferior direito. Some após 3 segundos."""
        toast = QLabel(mensagem, self.centralWidget())
        toast.setStyleSheet(f"""
            QLabel {{
                background: {COR_ITEM_ATIVO};
                color: {COR_TEXTO};
                border: 1px solid {COR_BORDA};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }}
        """)
        toast.adjustSize()

        cw = self.centralWidget()
        x  = cw.width()  - toast.width()  - 20
        y  = cw.height() - toast.height() - 20
        toast.move(x, y)
        toast.show()
        toast.raise_()

        QTimer.singleShot(3000, toast.deleteLater)

    def _mostrar_notificacao(self, titulo: str, texto: str, icone_path: str, sucesso: bool):
        """Popup estilo Steam no canto inferior direito da tela."""
        from launcher.ui.notification_popup import NotificationPopup
        popup = NotificationPopup(titulo, texto, icone_path, sucesso)
        popup.show()
        if not hasattr(self, "_popups"):
            self._popups = []
        self._popups.append(popup)
        popup.destroyed.connect(lambda: self._popups.remove(popup) if popup in self._popups else None)