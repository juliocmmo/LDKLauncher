"""
Gerencia exclusões do Windows Defender.
Como a leitura das exclusões requer admin, o estado é salvo localmente no config.json.
"""
import subprocess
from launcher.config.logger import get_logger

logger = get_logger()


def _carregar_config() -> dict:
    from config.settings import carregar_config
    return carregar_config()


def _salvar_config(config: dict):
    from config.settings import salvar_config
    salvar_config(config)


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
    Requer privilégios de administrador — vai disparar UAC.
    Registra localmente se bem-sucedido para não pedir de novo.
    """
    try:
        pasta_escaped = pasta.replace("'", "''")
        ps_command = (
            f"Start-Process powershell -Verb RunAs -WindowStyle Hidden -Wait "
            f"-ArgumentList '-NoProfile','-Command',"
            f"\"Add-MpPreference -ExclusionPath '{pasta_escaped}'\""
        )
        cmd = ["powershell", "-NoProfile", "-Command", ps_command]
        logger.info(f"Solicitando exclusão do Defender para: {pasta}")
        resultado = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if resultado.returncode == 0:
            logger.info(f"Pasta excluída do Defender com sucesso: {pasta}")
            _registrar_excluida(pasta)
            return True
        else:
            logger.warning(f"Falha ao excluir pasta do Defender (código {resultado.returncode}): {resultado.stderr}")
            return False
    except Exception as e:
        logger.error(f"Erro ao adicionar exclusão no Defender: {e}", exc_info=True)
        return False