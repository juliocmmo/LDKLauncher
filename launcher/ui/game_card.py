"""
launcher/ui/game_card.py  — Etapa 5

Mudanças em relação à Etapa 4:
  - Botão "Desinstalar" adicionado ao lado do botão principal nos estados
    idle_jogar e idle_atualizar.
  - Sinal desinstalado(nome_jogo: str) emitido após desinstalação bem-sucedida,
    para a MainWindow mover o jogo de Biblioteca → Disponíveis na sidebar.
  - _on_desinstalar: remove pasta do jogo, limpa version_local.json,
    atualiza estado do card para nao_instalado.
  - _set_idle e _atualizar_estado atualizados para mostrar/ocultar o botão
    de desinstalar conforme o estado.

Correções pós code-review:
  - #4:  _set_baixando força _barra.setVisible(True)
  - #5:  _pix_original salvo para evitar degradação no resizeEvent
  - #8:  download_erro emitido em _on_erro
  - #9:  _url_download_direto removida (código morto)
  - #10: _formatar_meta removida (código morto)
  - thumbnail proporcional 16:9 (estilo Steam)
  - addStretch no corpo para ancorar conteúdo no topo

Chave de campos do dicionário real:
  name, version_remote, version_local, status, type,
  description, thumbnail_url, thumbnail_offset,
  icon_url, file_url, hash_sha256, size_bytes,
  install_path, executable, instance_name
"""

from pathlib import Path

from PySide6.QtCore    import Qt, QTimer, Signal, QSize
from PySide6.QtGui     import QPixmap, QFont, QColor, QPainter, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QSizePolicy, QFrame,
)

from launcher.ui.theme import (
    COR_BG, COR_BANNER, COR_BORDA, COR_AZUL, COR_AZUL_CLARO,
    COR_TEXTO, COR_MUTED, COR_MUTED_DARK, COR_ITEM_ATIVO,
    STATUS_VERDE, STATUS_LARANJA,
    FONTE_NOME_JOGO, FONTE_META, FONTE_BOTAO, FONTE_DESC,
    BTN_ALTURA,
)
from launcher.core.download_worker import DownloadWorker
from launcher.core.game_launcher   import (
    iniciar_jogo, fechar_jogo, jogo_esta_aberto,
    iniciar_prism, prism_instalado,
)
from launcher.config.settings import obter_install_dir_jogo
from launcher.config.logger import get_logger

logger = get_logger()

THUMB_ALTURA = 320
RAIO_BORDA   = 12


class GameCard(QWidget):
    """
    Card de um jogo. Estados: idle_instalar / idle_jogar /
    idle_atualizar / baixando / jogando.

    Sinais emitidos para a MainWindow:
      download_iniciado(nome_jogo)
      download_concluido(nome_jogo)
      download_cancelado(nome_jogo)
      download_erro(nome_jogo)
      progresso_download(nome_jogo, pct, fase, detalhe)
      desinstalado(nome_jogo)
    """

    download_iniciado  = Signal(str)
    download_concluido = Signal(str)
    download_cancelado = Signal(str)
    download_erro      = Signal(str)
    progresso_download = Signal(str, int, str, str)
    desinstalado       = Signal(str)
    _thumb_pronta      = Signal(str)   # caminho do cache — uso interno

    def __init__(self, dados: dict, parent=None):
        super().__init__(parent)
        self._dados        = dados
        self._pix_original: QPixmap | None = None
        self._worker: DownloadWorker | None = None
        self._jogando = False
        self._timer_jogo = QTimer(self)
        self._timer_jogo.setInterval(2000)
        self._timer_jogo.timeout.connect(self._checar_processo_jogo)
        self._thumb_pronta.connect(self._aplicar_thumbnail_cache)

        self._construir_ui()
        self._atualizar_estado()

    # ------------------------------------------------------------------
    # Propriedades
    # ------------------------------------------------------------------

    @property
    def nome(self) -> str:
        return self._dados.get("name", "")

    @property
    def status(self) -> str:
        return self._dados.get("status", "nao_instalado")

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _construir_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            GameCard {{
                background: {COR_BG};
                border: 1px solid {COR_BORDA};
                border-radius: {RAIO_BORDA}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Thumbnail proporcional 16:9 estilo Steam
        self._thumb = _ThumbnailLabel()
        layout.addWidget(self._thumb)

        # Corpo
        corpo = QWidget()
        cl = QVBoxLayout(corpo)
        cl.setContentsMargins(20, 14, 20, 16)
        cl.setSpacing(2)

        # Nome
        self._lbl_nome = QLabel(self.nome)
        self._lbl_nome.setFont(QFont(*FONTE_NOME_JOGO))
        self._lbl_nome.setStyleSheet(f"color: {COR_TEXTO};")
        self._lbl_nome.setWordWrap(False)
        self._lbl_nome.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cl.addWidget(self._lbl_nome)

        # Versão + status badge
        linha_v = QHBoxLayout()
        linha_v.setSpacing(8)
        self._lbl_versao = QLabel()
        self._lbl_versao.setFont(QFont(*FONTE_META))
        self._lbl_versao.setStyleSheet(f"color: {COR_MUTED};")
        self._lbl_status_badge = QLabel()
        self._lbl_status_badge.setFont(QFont(*FONTE_META))
        linha_v.addWidget(self._lbl_versao)
        linha_v.addWidget(self._lbl_status_badge)
        linha_v.addStretch()
        cl.addLayout(linha_v)

        cl.addSpacing(8)

        # Descrição
        self._lbl_desc = QLabel(self._dados.get("description", ""))
        self._lbl_desc.setFont(QFont(*FONTE_DESC))
        self._lbl_desc.setStyleSheet(f"color: {COR_MUTED};")
        self._lbl_desc.setWordWrap(True)
        self._lbl_desc.setMaximumHeight(52)
        cl.addWidget(self._lbl_desc)

        cl.addSpacing(10)

        # Área de progresso (oculta por padrão)
        self._area_prog = QWidget()
        pl = QVBoxLayout(self._area_prog)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(4)

        self._lbl_fase = QLabel()
        self._lbl_fase.setFont(QFont(*FONTE_META))
        self._lbl_fase.setStyleSheet(f"color: {COR_MUTED};")

        self._lbl_detalhe = QLabel()
        self._lbl_detalhe.setFont(QFont(*FONTE_META))
        self._lbl_detalhe.setStyleSheet(f"color: {COR_MUTED_DARK};")

        self._barra = QProgressBar()
        self._barra.setRange(0, 100)
        self._barra.setValue(0)
        self._barra.setTextVisible(False)
        self._barra.setFixedHeight(6)
        self._barra.setStyleSheet(f"""
            QProgressBar {{
                background: {COR_BORDA}; border-radius: 3px; border: none;
            }}
            QProgressBar::chunk {{
                background: {COR_AZUL_CLARO}; border-radius: 3px;
            }}
        """)
        pl.addWidget(self._lbl_fase)
        pl.addWidget(self._barra)
        pl.addWidget(self._lbl_detalhe)
        self._area_prog.setVisible(False)
        cl.addWidget(self._area_prog)

        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_principal = QPushButton()
        self._btn_principal.setFont(QFont(*FONTE_BOTAO))
        self._btn_principal.setFixedHeight(BTN_ALTURA)
        self._btn_principal.setCursor(Qt.PointingHandCursor)
        self._btn_principal.clicked.connect(self._on_btn_principal)

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.setFont(QFont(*FONTE_BOTAO))
        self._btn_cancelar.setFixedHeight(BTN_ALTURA)
        self._btn_cancelar.setCursor(Qt.PointingHandCursor)
        self._btn_cancelar.setVisible(False)
        self._btn_cancelar.clicked.connect(self._on_cancelar)
        self._btn_cancelar.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COR_MUTED};
                border: 1px solid {COR_BORDA}; border-radius: 6px; padding: 0 16px;
            }}
            QPushButton:hover {{ color: {COR_TEXTO}; border-color: {COR_MUTED}; }}
        """)

        self._btn_desinstalar = QPushButton("Desinstalar")
        self._btn_desinstalar.setFont(QFont(*FONTE_BOTAO))
        self._btn_desinstalar.setFixedHeight(BTN_ALTURA)
        self._btn_desinstalar.setCursor(Qt.PointingHandCursor)
        self._btn_desinstalar.setVisible(False)
        self._btn_desinstalar.clicked.connect(self._on_desinstalar)
        self._btn_desinstalar.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {COR_MUTED};
                border: 1px solid {COR_BORDA}; border-radius: 6px; padding: 0 16px;
            }}
            QPushButton:hover {{ color: #e07070; border-color: #8b1a1a; }}
        """)

        btn_row.addWidget(self._btn_principal)
        btn_row.addWidget(self._btn_cancelar)
        btn_row.addWidget(self._btn_desinstalar)
        cl.addLayout(btn_row)

        # Container de metadados (divisor + grade)
        self._container_meta = QWidget()
        meta_cl = QVBoxLayout(self._container_meta)
        meta_cl.setContentsMargins(0, 10, 0, 0)
        meta_cl.setSpacing(8)

        divisor = QFrame()
        divisor.setFixedHeight(1)
        divisor.setStyleSheet(f"background: {COR_BORDA};")
        meta_cl.addWidget(divisor)

        self._meta_row = QHBoxLayout()
        self._meta_row.setSpacing(28)
        self._meta_tamanho = _MetaItem("Tamanho", "—")
        self._meta_versao  = _MetaItem("Versão", "—")
        self._meta_jogado  = _MetaItem("Último acesso", "—")
        self._meta_row.addWidget(self._meta_tamanho)
        self._meta_row.addWidget(self._meta_versao)
        self._meta_row.addWidget(self._meta_jogado)
        self._meta_row.addStretch()
        meta_cl.addLayout(self._meta_row)

        cl.addWidget(self._container_meta)
        cl.addStretch(1)  # espaço extra vai para o fim, âncora conteúdo no topo

        layout.addWidget(corpo)

        # Carregar thumbnail agora
        self._carregar_thumbnail()

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def _atualizar_estado(self):
        versao_r = self._dados.get("version_remote", "")
        status   = self.status

        self._lbl_versao.setText(f"v{versao_r}" if versao_r else "")
        self._atualizar_meta()

        if status == "nao_instalado":
            self._set_idle("instalar")
            self._lbl_status_badge.setText("")
            self._container_meta.setVisible(True)
            self._meta_jogado.setVisible(False)
            self._btn_desinstalar.setVisible(False)
        elif status == "desatualizado":
            self._set_idle("atualizar")
            self._lbl_status_badge.setText("● Atualização disponível")
            self._lbl_status_badge.setStyleSheet(f"color: {STATUS_LARANJA};")
            self._container_meta.setVisible(True)
            self._meta_jogado.setVisible(True)
            self._btn_desinstalar.setVisible(True)
            self._btn_desinstalar.setEnabled(True)
        else:  # atualizado
            self._set_idle("jogar")
            self._lbl_status_badge.setText("● Atualizado")
            self._lbl_status_badge.setStyleSheet(f"color: {STATUS_VERDE};")
            self._container_meta.setVisible(True)
            self._meta_jogado.setVisible(True)
            self._btn_desinstalar.setVisible(True)
            self._btn_desinstalar.setEnabled(True)

    def _atualizar_meta(self):
        """Atualiza a grade de metadados abaixo do botão."""
        size = self._dados.get("size_bytes", 0)
        self._meta_tamanho.set_valor(_fmt_tamanho(size) if size else "—")

        status   = self.status
        versao_r = self._dados.get("version_remote", "")
        versao_l = self._dados.get("version_local",  "")
        if status == "nao_instalado":
            self._meta_versao.setVisible(False)
        elif status == "desatualizado" and versao_l and versao_r:
            self._meta_versao.set_valor(f"v{versao_l} → v{versao_r}")
            self._meta_versao.setVisible(True)
        else:
            self._meta_versao.set_valor(f"v{versao_r}" if versao_r else "—")
            self._meta_versao.setVisible(True)

        last_played = self._dados.get("last_played", "")
        self._meta_jogado.set_valor(_fmt_data(last_played) if last_played else "—")

    def _set_idle(self, acao: str):
        self._area_prog.setVisible(False)
        self._btn_cancelar.setVisible(False)
        self._btn_principal.setVisible(True)
        self._btn_principal.setEnabled(True)
        rotulos = {
            "instalar":  "Instalar",
            "atualizar": "Atualizar",
            "jogar":     "Jogar",
            "jogando":   "Fechar Jogo",
        }
        self._btn_principal.setText(rotulos.get(acao, acao))
        cor   = "#7a1a1a" if acao == "jogando" else COR_AZUL
        cor_h = "#a02020" if acao == "jogando" else COR_AZUL_CLARO
        self._btn_principal.setStyleSheet(f"""
            QPushButton {{
                background: {cor}; color: {COR_TEXTO}; border: none;
                border-radius: 6px; padding: 0 16px;
            }}
            QPushButton:hover    {{ background: {cor_h}; }}
            QPushButton:disabled {{ background: {COR_BORDA}; color: {COR_MUTED_DARK}; }}
        """)

    def _set_baixando(self):
        self._area_prog.setVisible(True)
        self._btn_cancelar.setVisible(True)
        self._btn_cancelar.setEnabled(True)
        self._btn_principal.setVisible(False)
        self._btn_desinstalar.setVisible(False)
        self._barra.setVisible(True)
        self._barra.setValue(0)
        self._lbl_fase.setText("Iniciando…")
        self._lbl_detalhe.setText("")
        self._lbl_fase.setStyleSheet(f"color: {COR_MUTED};")

    def _set_jogando(self):
        self._area_prog.setVisible(False)
        self._btn_cancelar.setVisible(False)
        self._btn_desinstalar.setVisible(False)
        self._btn_desinstalar.setEnabled(False)
        self._set_idle("jogando")

    # ------------------------------------------------------------------
    # API pública: atualizar dados após refresh silencioso
    # ------------------------------------------------------------------

    def atualizar_dados(self, dados: dict):
        """Não interrompe worker ativo."""
        if self._worker is not None:
            return
        self._dados = dados
        self._carregar_thumbnail()
        self._atualizar_estado()

    # ------------------------------------------------------------------
    # Thumbnail
    # ------------------------------------------------------------------

    def _carregar_thumbnail(self):
        from launcher.config.settings import CONFIG_DIR

        thumbs_dir = Path(CONFIG_DIR) / "thumbs"
        thumbs_dir.mkdir(parents=True, exist_ok=True)
        cache      = thumbs_dir / f"{self.nome}.jpg"
        cache_meta = thumbs_dir / f"{self.nome}.meta"
        url        = self._dados.get("thumbnail_url", "")

        # Invalida cache se a URL mudou
        if cache.exists() and cache_meta.exists():
            try:
                url_salva = cache_meta.read_text(encoding="utf-8").strip()
                if url_salva != url:
                    cache.unlink()
                    cache_meta.unlink()
            except Exception:
                pass

        if cache.exists():
            self._aplicar_pixmap(QPixmap(str(cache)))
        elif url:
            self._baixar_thumbnail_bg(url, cache, cache_meta)

    def _baixar_thumbnail_bg(self, url: str, cache: Path, cache_meta: Path | None = None):
        import threading
        def _dl():
            try:
                from shared.drive_utils import baixar_asset_drive
                ok = baixar_asset_drive(url, cache)
                if ok:
                    if cache_meta:
                        cache_meta.write_text(url, encoding="utf-8")
                    self._thumb_pronta.emit(str(cache))
            except Exception as e:
                logger.warning(f"[{self.nome}] Thumbnail não carregou: {e}")
        threading.Thread(target=_dl, daemon=True).start()

    def _aplicar_thumbnail_cache(self, caminho: str):
        pix = QPixmap(caminho)
        if not pix.isNull():
            self._aplicar_pixmap(pix)

    def _aplicar_pixmap(self, pix: QPixmap):
        if pix.isNull():
            return
        self._pix_original = pix
        offset_pct = self._dados.get("thumbnail_offset", 0.0)
        w = self._thumb.width() or 400
        h = self._thumb.height() or THUMB_ALTURA
        self._thumb.setPixmap(_aplicar_crop(pix, offset_pct, w, h))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pix_original and not self._pix_original.isNull():
            offset_pct = self._dados.get("thumbnail_offset", 0.0)
            w = self._thumb.width() or 400
            h = self._thumb.height() or THUMB_ALTURA
            self._thumb.setPixmap(
                _aplicar_crop(self._pix_original, offset_pct, w, h)
            )

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _on_btn_principal(self):
        txt = self._btn_principal.text()
        if txt in ("Instalar", "Atualizar", "Tentar novamente"):
            self._iniciar_download()
        elif txt == "Jogar":
            self._iniciar_jogo()
        elif txt == "Fechar Jogo":
            self._fechar_jogo()

    def _iniciar_download(self):
        if self._worker is not None:
            return

        from launcher.ui.install_dialog import InstallDialog
        dlg = InstallDialog(
            parent=self,
            nome_jogo=self.nome,
            install_path=self._dados.get("install_path", self.nome),
            tamanho_str=_fmt_tamanho(self._dados.get("size_bytes", 0)),
        )
        dlg.exec()

        if not dlg.confirmado:
            return

        self._dados["pasta_instalacao"]  = dlg.pasta_escolhida
        self._dados["excluir_antivirus"] = dlg.excluir_antivirus

        self._worker = DownloadWorker(self._dados)
        self._worker.progresso.connect(self._on_progresso)
        self._worker.concluido.connect(self._on_concluido)
        self._worker.erro.connect(self._on_erro)
        self._worker.cancelado.connect(self._on_cancelado)

        self._set_baixando()
        self.download_iniciado.emit(self.nome)
        self._worker.start()
        logger.info(f"[{self.nome}] Download iniciado.")

    def _iniciar_jogo(self):
        tipo = self._dados.get("type", "standalone")
        try:
            if tipo == "minecraft":
                ok = iniciar_prism()
            else:
                nome_modpack = self._dados["name"]
                executavel   = self._dados.get("executable", "")
                ok = iniciar_jogo(nome_modpack, executavel)

            if ok:
                self._jogando = True
                self._set_jogando()
                self._timer_jogo.start()
                self._gravar_last_played()
        except Exception as exc:
            logger.error(f"[{self.nome}] Erro ao iniciar jogo: {exc}")
            self._mostrar_erro(str(exc))

    def _gravar_last_played(self):
        """Salva a data/hora atual como último acesso no version_local.json."""
        from datetime import datetime
        from launcher.core.version_checker import carregar_versao_local, salvar_versao_local
        try:
            local = carregar_versao_local()
            agora = datetime.now().isoformat(timespec="minutes")
            if self.nome not in local:
                local[self.nome] = {}
            local[self.nome]["last_played"] = agora
            salvar_versao_local(local)
            self._dados["last_played"] = agora
            self._atualizar_meta()
            logger.info(f"[{self.nome}] last_played gravado: {agora}")
        except Exception as e:
            logger.warning(f"[{self.nome}] Não foi possível gravar last_played: {e}")

    def _fechar_jogo(self):
        executavel = self._dados.get("executable", "")
        try:
            fechar_jogo(executavel)
        except Exception as exc:
            logger.error(f"[{self.nome}] Erro ao fechar jogo: {exc}")
        self._jogando = False
        self._timer_jogo.stop()
        self._atualizar_estado()

    def _checar_processo_jogo(self):
        """Detecta quando o jogo fecha por conta própria (varredura por nome do exe)."""
        if not self._jogando:
            self._timer_jogo.stop()
            return
        executavel = self._dados.get("executable", "")
        if executavel and not jogo_esta_aberto(executavel):
            self._jogando = False
            self._timer_jogo.stop()
            self._atualizar_estado()

    def _on_cancelar(self):
        if self._worker:
            self._worker.cancelar()
            self._btn_cancelar.setEnabled(False)
            self._lbl_fase.setText("Cancelando…")

    def _on_desinstalar(self):
        from PySide6.QtWidgets import QMessageBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Desinstalar")
        dlg.setText(f"Desinstalar <b>{self.nome}</b>?")
        dlg.setInformativeText("Os arquivos do jogo serão removidos permanentemente.")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.No)
        dlg.button(QMessageBox.Yes).setText("Desinstalar")
        dlg.button(QMessageBox.No).setText("Cancelar")
        dlg.setStyleSheet(f"""
            QMessageBox {{
                background: #07152a;
            }}
            QLabel {{
                color: #e8f4fd;
                font-size: 13px;
            }}
            QPushButton {{
                min-width: 100px; min-height: 32px;
                border-radius: 6px; font-size: 13px;
            }}
            QPushButton[text="Desinstalar"] {{
                background: #8b1a1a; color: #e8f4fd; border: none;
            }}
            QPushButton[text="Desinstalar"]:hover {{ background: #a02020; }}
            QPushButton[text="Cancelar"] {{
                background: transparent; color: #4a7fa8;
                border: 1px solid #0c2a4a;
            }}
            QPushButton[text="Cancelar"]:hover {{ color: #e8f4fd; }}
        """)

        if dlg.exec() != QMessageBox.Yes:
            return

        self._executar_desinstalacao()

    def _executar_desinstalacao(self):
        import shutil
        from launcher.core.version_checker import carregar_versao_local, salvar_versao_local

        pasta = Path(obter_install_dir_jogo(self.nome)) / self.nome
        try:
            if pasta.exists():
                shutil.rmtree(pasta)
                logger.info(f"[{self.nome}] Pasta removida: {pasta}")
            else:
                logger.warning(f"[{self.nome}] Pasta não encontrada: {pasta}")
        except Exception as e:
            logger.error(f"[{self.nome}] Erro ao remover pasta: {e}")
            self._mostrar_erro(f"Não foi possível remover a pasta:\n{e}")
            return

        try:
            local = carregar_versao_local()
            if self.nome in local:
                del local[self.nome]
                salvar_versao_local(local)
                logger.info(f"[{self.nome}] Removido do version_local.json.")
        except Exception as e:
            logger.warning(f"[{self.nome}] Erro ao limpar version_local.json: {e}")

        self._dados["status"]        = "nao_instalado"
        self._dados["version_local"] = None
        self._dados["last_played"]   = ""
        self._atualizar_estado()
        self.desinstalado.emit(self.nome)
        logger.info(f"[{self.nome}] Desinstalado.")

    # ------------------------------------------------------------------
    # Slots do worker
    # ------------------------------------------------------------------

    def _on_progresso(self, pct: int, fase: str, detalhe: str):
        fases_pt = {"download": "Baixando", "hash": "Verificando", "extração": "Extraindo"}
        self._lbl_fase.setText(fases_pt.get(fase, fase))
        self._barra.setValue(pct)
        self._lbl_detalhe.setText(detalhe)
        self.progresso_download.emit(self.nome, pct, fase, detalhe)

    def _on_concluido(self, nome: str):
        self._worker = None
        versao = self._dados.get("version_remote", "")
        self._dados["status"]        = "atualizado"
        self._dados["version_local"] = versao

        try:
            from launcher.core.version_checker import carregar_versao_local, salvar_versao_local
            local = carregar_versao_local()
            if nome not in local:
                local[nome] = {}
            local[nome]["version"] = versao
            if self._dados.get("pasta_instalacao"):
                # Salva apenas o diretório BASE (sem a subpasta do jogo),
                # pois o worker sempre acrescenta self._nome sobre install_dir.
                local[nome]["install_dir"] = str(Path(self._dados["pasta_instalacao"]).parent)
            salvar_versao_local(local)
        except Exception as e:
            logger.warning(f"[{nome}] Não foi possível salvar versão local: {e}")

        self._atualizar_estado()
        self.download_concluido.emit(nome)
        logger.info(f"[{nome}] Concluído.")

    def _on_erro(self, nome: str, msg: str):
        self._worker = None
        self._mostrar_erro(msg)
        self.download_erro.emit(nome)

    def _on_cancelado(self, nome: str):
        self._worker = None
        self._atualizar_estado()
        self.download_cancelado.emit(nome)
        logger.info(f"[{nome}] Cancelado pelo usuário.")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _mostrar_erro(self, msg: str):
        self._area_prog.setVisible(True)
        self._btn_cancelar.setVisible(False)
        self._btn_desinstalar.setVisible(False)
        self._btn_principal.setVisible(True)
        self._btn_principal.setEnabled(True)
        self._btn_principal.setText("Tentar novamente")
        self._lbl_fase.setText("⚠ Erro")
        self._lbl_fase.setStyleSheet("color: #c0392b;")
        self._lbl_detalhe.setText(msg[:120])
        self._barra.setVisible(False)
        self._btn_principal.setStyleSheet(f"""
            QPushButton {{
                background: {COR_AZUL}; color: {COR_TEXTO}; border: none;
                border-radius: 6px; padding: 0 16px;
            }}
            QPushButton:hover {{ background: {COR_AZUL_CLARO}; }}
        """)


# ---------------------------------------------------------------------------
# Widget de metadado: rótulo acima, valor abaixo (estilo Steam)
# ---------------------------------------------------------------------------

class _MetaItem(QWidget):
    def __init__(self, rotulo: str, valor: str = "—", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._lbl_rot = QLabel(rotulo.upper())
        self._lbl_rot.setFont(QFont("Segoe UI", 9))
        self._lbl_rot.setStyleSheet(f"color: {COR_MUTED_DARK}; letter-spacing: 0.05em;")

        self._lbl_val = QLabel(valor)
        self._lbl_val.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._lbl_val.setStyleSheet(f"color: {COR_MUTED};")

        layout.addWidget(self._lbl_rot)
        layout.addWidget(self._lbl_val)

    def set_valor(self, valor: str):
        self._lbl_val.setText(valor)


# ---------------------------------------------------------------------------
# Thumbnail proporcional 16:9 estilo Steam
# ---------------------------------------------------------------------------

class _ThumbnailLabel(QLabel):
    _RAZAO = 16 / 9  # largura ÷ altura

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background: {COR_BANNER};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return max(180, int(width / self._RAZAO))

    def sizeHint(self) -> QSize:
        w = self.width() or 400
        return QSize(w, self.heightForWidth(w))

    def paintEvent(self, event):
        pix = self.pixmap()
        if not pix or pix.isNull():
            p = QPainter(self)
            p.fillRect(self.rect(), QColor(COR_BANNER))
            p.end()
            return

        p = QPainter(self)
        p.drawPixmap(self.rect(), pix)
        grad = QLinearGradient(0, self.height() * 0.5, 0, self.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(7, 21, 42, 210))
        p.fillRect(self.rect(), grad)
        p.end()


# ---------------------------------------------------------------------------
# Crop de thumbnail
# ---------------------------------------------------------------------------

def _aplicar_crop(pix: QPixmap, offset_pct: float, target_w: int, target_h: int) -> QPixmap:
    if pix.isNull() or target_w <= 0 or target_h <= 0:
        return pix

    pix_s = pix.scaled(target_w, target_h,
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation)

    escala    = max(target_w / pix.width(), target_h / pix.height())
    offset_px = int(offset_pct * pix.height() * escala)
    max_off   = pix_s.height() - target_h
    offset_px = max(0, min(offset_px, max_off))
    x = (pix_s.width() - target_w) // 2
    return pix_s.copy(x, offset_px, target_w, target_h)


def _fmt_tamanho(bytes_: int) -> str:
    if bytes_ >= 1024 ** 3:
        return f"{bytes_ / 1024**3:.2f} GB"
    if bytes_ >= 1024 ** 2:
        return f"{bytes_ / 1024**2:.0f} MB"
    return f"{bytes_ / 1024:.0f} KB"


def _fmt_data(iso: str) -> str:
    """Converte ISO para 'DD/MM/YYYY HH:MM' se tiver hora, ou só 'DD/MM/YYYY'."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso)
        if dt.hour or dt.minute:
            return dt.strftime("%d/%m/%Y %H:%M")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso