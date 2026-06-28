"""
Gerencia exclusões do Windows Defender.
Como a leitura das exclusões requer admin, o estado é salvo localmente no config.json.
"""
import ctypes
import os
import subprocess
import tempfile
from launcher.config.logger import get_logger

logger = get_logger()


def _carregar_config() -> dict:
    from launcher.config.settings import carregar_config
    return carregar_config()


def _salvar_config(config: dict):
    from launcher.config.settings import salvar_config
    salvar_config(config)


def _is_admin() -> bool:
    """Verifica se o processo atual tem privilégios de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def esta_excluida(pasta: str) -> bool:
    """
    Verifica se uma pasta já foi excluída do Defender.
    Usa o registro local em config.json (leitura do Defender requer admin).
    """
    config = _carregar_config()
    excluidas = config.get("defender_excluidas", [])
    pasta_norm = pasta.replace("/", "\\").rstrip("\\").lower()
    return any(e.replace("/", "\\").rstrip("\\").lower() == pasta_norm for e in excluidas)


def _registrar_excluida(pasta: str):
    """Salva a pasta como excluída no config.json."""
    config = _carregar_config()
    excluidas = config.get("defender_excluidas", [])
    pasta_norm = pasta.replace("/", "\\").rstrip("\\")
    if pasta_norm not in excluidas:
        excluidas.append(pasta_norm)
        config["defender_excluidas"] = excluidas
        _salvar_config(config)
        logger.info(f"Pasta registrada como excluída no config: {pasta_norm}")


def adicionar_exclusao(pasta: str) -> bool:
    """
    Adiciona uma pasta à lista de exclusões do Windows Defender.
    Se já for admin, executa diretamente. Caso contrário, eleva via UAC (Start-Process -Verb RunAs).
    Registra localmente se bem-sucedido para não pedir de novo.
    """
    temp_script = None
    try:
        pasta_escaped = pasta.replace("'", "''")
        ps_command = f"Add-MpPreference -ExclusionPath '{pasta_escaped}'"
        logger.info(f"Solicitando exclusão do Defender para: {pasta}")

        if _is_admin():
            # Já é admin — executa diretamente
            logger.info("Processo já é admin, executando Add-MpPreference diretamente.")
            cmd = [
                "powershell", "-NoProfile", "-WindowStyle", "Hidden",
                "-Command", ps_command,
            ]
            resultado = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            # Sem privilégios — eleva via UAC com Start-Process -Verb RunAs.
            # Usa arquivo .ps1 temporário para evitar problemas de escape em comandos aninhados.
            logger.info("Processo sem admin, elevando via Start-Process -Verb RunAs.")
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".ps1", delete=False, encoding="utf-8"
            ) as f:
                f.write(ps_command)
                temp_script = f.name

            elevate_cmd = (
                f"Start-Process powershell "
                f"-Verb RunAs -Wait "
                f"-ArgumentList '-NoProfile -WindowStyle Hidden -File \"{temp_script}\"'"
            )
            cmd = [
                "powershell", "-NoProfile", "-WindowStyle", "Hidden",
                "-Command", elevate_cmd,
            ]
            resultado = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        if resultado.returncode == 0:
            logger.info(f"Pasta excluída do Defender com sucesso: {pasta}")
            _registrar_excluida(pasta)
            return True
        else:
            logger.warning(
                f"Falha ao excluir pasta do Defender "
                f"(código {resultado.returncode}): {resultado.stderr}"
            )
            return False

    except Exception as e:
        logger.error(f"Erro ao adicionar exclusão no Defender: {e}", exc_info=True)
        return False
    finally:
        if temp_script and os.path.exists(temp_script):
            try:
                os.unlink(temp_script)
            except Exception:
                pass