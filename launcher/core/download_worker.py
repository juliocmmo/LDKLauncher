"""
launcher/core/download_worker.py
QThread que encapsula o pipeline completo: download → hash → extração.
Adaptado para as funções reais do projeto (extractor.py, version_checker.py).

Etapa 5 — alterações:
  - Corrigido bug: _fase_download chamava baixar_arquivo duas vezes;
    agora passa str(self._zip_destino) como nome_arquivo direto.
  - _fase_extracao: callback lança InterruptedError ao detectar cancel_event,
    interrompendo o loop de extração imediatamente.
  - _limpar_zip renomeada para _limpar_residuos(parcial=False); quando
    parcial=True remove também a pasta parcialmente extraída.
  - run(): InterruptedError capturada separadamente para não tratar como erro.
"""

import threading
import hashlib
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from launcher.core.downloader import baixar_arquivo
from launcher.core.extractor  import extrair_modpack, extrair_instancia_minecraft
from launcher.core.antivirus  import esta_excluida, adicionar_exclusao
from launcher.config.settings import get_temp_dir
from launcher.config.logger   import get_logger

logger = get_logger()


class DownloadWorker(QThread):
    """
    Executa: download → validação SHA-256 → extração.

    Sinais:
      progresso(int pct, str fase, str detalhe)
        fase: "download" | "hash" | "extração"
      concluido(str nome_jogo)
      erro(str nome_jogo, str mensagem)
      cancelado(str nome_jogo)
    """

    progresso = Signal(int, str, str)
    concluido = Signal(str)
    erro      = Signal(str, str)
    cancelado = Signal(str)

    def __init__(self, dados_jogo: dict, parent=None):
        super().__init__(parent)
        self._dados        = dados_jogo
        self._cancel_event = threading.Event()

        # Campos do dicionário real
        self._nome       = dados_jogo["name"]
        self._tipo       = dados_jogo.get("type", "standalone")
        self._url        = dados_jogo.get("file_url", "")
        self._hash_esp   = dados_jogo.get("hash_sha256", "")
        self._inst_name  = dados_jogo.get("instance_name", "")

        from launcher.config.settings import obter_install_dir_jogo, get_temp_dir
        self._install_dir = Path(obter_install_dir_jogo(self._nome))
        self._temp_dir    = Path(get_temp_dir())

        versao = dados_jogo.get("version_remote", "")
        self._zip_nome    = f"{self._nome}_{versao}.zip"
        self._zip_destino = self._temp_dir / self._zip_nome

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def cancelar(self):
        self._cancel_event.set()

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def run(self):
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)

            self._fase_download()
            if self._cancel_event.is_set():
                self._limpar_residuos()
                self.cancelado.emit(self._nome)
                return

            if self._hash_esp:
                ok = self._fase_hash()
                if not ok:
                    return   # erro ou cancelado — já emitido dentro
                if self._cancel_event.is_set():
                    self._limpar_residuos()
                    self.cancelado.emit(self._nome)
                    return

            self._garantir_exclusao_defender()
            self._fase_extracao()
            if self._cancel_event.is_set():
                self._limpar_residuos(parcial=True)
                self.cancelado.emit(self._nome)
                return

            self._limpar_residuos()
            self.concluido.emit(self._nome)

        except InterruptedError:
            # Cancelamento durante extração (callback lançou InterruptedError)
            self._limpar_residuos(parcial=True)
            self.cancelado.emit(self._nome)
        except Exception as exc:
            logger.error(f"[{self._nome}] Erro no worker: {exc}", exc_info=True)
            self._limpar_residuos()
            self.erro.emit(self._nome, str(exc))

    # ------------------------------------------------------------------
    # Fases
    # ------------------------------------------------------------------

    def _garantir_exclusao_defender(self):
        """
        Adiciona a pasta de instalação às exclusões do Windows Defender
        antes da extração. Se já estiver excluída (registro local), não faz nada.
        Falha silenciosa — apenas loga; não bloqueia a instalação.
        """
        pasta = str(self._install_dir)
        if esta_excluida(pasta):
            logger.info(f"[{self._nome}] Pasta já excluída do Defender: {pasta}")
            return
        logger.info(f"[{self._nome}] Adicionando exclusão do Defender antes da extração…")
        ok = adicionar_exclusao(pasta)
        if not ok:
            logger.warning(
                f"[{self._nome}] Não foi possível excluir pasta do Defender. "
                f"O antivírus pode barrar arquivos durante a extração."
            )

    def _fase_download(self):
        import time
        tamanho      = self._dados.get("size_bytes", 0)
        _t_inicio    = [time.monotonic()]
        _baixado_ant = [0]
        _vel_bps     = [0.0]

        def cb(baixado, total):
            if self._cancel_event.is_set():
                return
            pct = int(baixado / total * 100) if total else 0
            baixado_str = f"{baixado / 1024**2:.0f} MB"
            total_str   = f"{total   / 1024**2:.0f} MB"

            agora   = time.monotonic()
            delta_t = agora - _t_inicio[0]
            if delta_t >= 0.5:
                _vel_bps[0]   = (baixado - _baixado_ant[0]) / delta_t
                _t_inicio[0]  = agora
                _baixado_ant[0] = baixado

            restante = (
                (total - baixado) / _vel_bps[0]
                if _vel_bps[0] > 0 and total > baixado else 0.0
            )

            vel_str = _fmt_velocidade(_vel_bps[0]) if _vel_bps[0] > 0 else ""
            eta_str = _fmt_tempo(restante)          if restante   > 0 else ""

            if vel_str and eta_str:
                detalhe = f"{baixado_str} / {total_str}  •  {vel_str}  •  {eta_str}"
            elif vel_str:
                detalhe = f"{baixado_str} / {total_str}  •  {vel_str}"
            else:
                detalhe = f"{baixado_str} / {total_str}"

            self.progresso.emit(pct, "download", detalhe)

        # CORRIGIDO: uma única chamada, passando o caminho completo do destino
        resultado = baixar_arquivo(
            url=self._url,
            nome_arquivo=str(self._zip_destino),
            tamanho_total=tamanho,
            callback_progresso=cb,
            cancel_event=self._cancel_event,
        )

        if resultado is None:
            if self._cancel_event.is_set():
                return   # cancelado pelo usuário — run() vai detectar e emitir cancelado
            raise RuntimeError("Download falhou. Verifique os logs para mais detalhes.")

    def _fase_hash(self) -> bool:
        self.progresso.emit(0, "hash", "Verificando integridade…")

        def cb(pct):
            if self._cancel_event.is_set():
                return
            self.progresso.emit(pct, "hash", "Verificando integridade…")

        hash_real = _calcular_hash(
            self._zip_destino,
            callback=cb,
            cancel_event=self._cancel_event,
        )

        if self._cancel_event.is_set():
            self._limpar_residuos()
            self.cancelado.emit(self._nome)
            return False

        if hash_real != self._hash_esp:
            msg = f"Hash inválido.\nEsperado: {self._hash_esp}\nObtido:   {hash_real}"
            logger.error(f"[{self._nome}] {msg}")
            self._limpar_residuos()
            self.erro.emit(self._nome, msg)
            return False

        return True

    def _fase_extracao(self):
        self.progresso.emit(0, "extração", "Iniciando extração…")

        def cb(feito, total, bytes_feitos=0, total_bytes=0):
            # Lança InterruptedError para interromper o loop de extração imediatamente
            if self._cancel_event.is_set():
                raise InterruptedError("Extração cancelada pelo usuário.")
            pct = int(feito / total * 100) if total else 0
            self.progresso.emit(pct, "extração", f"Arquivo {feito}/{total}")

        if self._tipo == "minecraft":
            ok = extrair_instancia_minecraft(
                caminho_zip=str(self._zip_destino),
                instance_name=self._inst_name or self._nome,
                callback_progresso=cb,
            )
        else:
            ok = extrair_modpack(
                caminho_zip=str(self._zip_destino),
                caminho_destino=str(self._install_dir / self._nome),
                callback_progresso=cb,
            )

        if not ok:
            raise RuntimeError("Extração falhou. Verifique os logs para mais detalhes.")

    # ------------------------------------------------------------------
    # Limpeza
    # ------------------------------------------------------------------

    def _limpar_residuos(self, parcial: bool = False):
        """
        Remove o ZIP temporário.
        Se parcial=True, remove também a pasta de destino parcialmente extraída.
        """
        try:
            if self._zip_destino.exists():
                self._zip_destino.unlink()
                logger.info(f"[{self._nome}] ZIP temporário removido.")
        except Exception as e:
            logger.warning(f"[{self._nome}] Não foi possível remover ZIP: {e}")

        if parcial:
            pasta = self._install_dir / self._nome
            try:
                if pasta.exists():
                    import shutil
                    shutil.rmtree(pasta)
                    logger.info(f"[{self._nome}] Pasta parcial removida: {pasta}")
            except Exception as e:
                logger.warning(f"[{self._nome}] Não foi possível remover pasta parcial: {e}")


# ------------------------------------------------------------------
# Hash SHA-256 com progresso e cancelamento
# (não existe no version_checker atual — implementada aqui no worker)
# ------------------------------------------------------------------

def _calcular_hash(caminho: Path, callback=None, cancel_event=None) -> str | None:
    tamanho = caminho.stat().st_size
    sha256  = hashlib.sha256()
    lido    = 0
    BLOCO   = 1024 * 1024  # 1 MB

    with open(caminho, "rb") as f:
        while True:
            if cancel_event and cancel_event.is_set():
                return None
            chunk = f.read(BLOCO)
            if not chunk:
                break
            sha256.update(chunk)
            lido += len(chunk)
            if callback and tamanho:
                callback(int(lido / tamanho * 100))

    return sha256.hexdigest()


# ------------------------------------------------------------------
# Helpers de formatação
# ------------------------------------------------------------------

def _fmt_velocidade(bps: float) -> str:
    if bps <= 0:
        return "-- B/s"
    if bps < 1024:
        return f"{bps:.0f} B/s"
    if bps < 1024 ** 2:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / 1024**2:.1f} MB/s"


def _fmt_tempo(segundos: float) -> str:
    if segundos < 0 or segundos > 86400:
        return "--:--"
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m"
    return f"{m:02d}:{s:02d}"