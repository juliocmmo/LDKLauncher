import os
import subprocess
import psutil
from config.settings import get_install_dir, get_prism_dir
from config.logger import get_logger

logger = get_logger()


def localizar_executavel(nome_modpack: str, executavel: str) -> str | None:
    pasta_base = os.path.join(get_install_dir(), nome_modpack)

    caminho_exato = os.path.join(pasta_base, executavel)
    if os.path.exists(caminho_exato):
        return caminho_exato

    nome_exe = os.path.basename(executavel)
    for raiz, pastas, arquivos in os.walk(pasta_base):
        if nome_exe in arquivos:
            caminho_encontrado = os.path.join(raiz, nome_exe)
            logger.info(f"Executável encontrado em: {caminho_encontrado}")
            return caminho_encontrado

    logger.error(f"Executável '{nome_exe}' não encontrado em: {pasta_base}")
    return None


def iniciar_jogo(nome_modpack: str, executavel: str) -> bool:
    caminho_exe = localizar_executavel(nome_modpack, executavel)
    if caminho_exe is None:
        return False
    try:
        diretorio_jogo = os.path.dirname(caminho_exe)
        subprocess.Popen(
            [caminho_exe],
            cwd=diretorio_jogo,
            creationflags=subprocess.DETACHED_PROCESS
        )
        logger.info(f"Jogo iniciado: {caminho_exe}")
        return True
    except PermissionError:
        logger.error(f"Sem permissão para executar: {caminho_exe}")
        return False
    except OSError as e:
        logger.error(f"Erro ao iniciar o jogo: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao iniciar o jogo: {e}", exc_info=True)
        return False


def iniciar_prism() -> bool:
    """Abre o Prism Launcher portátil."""
    caminho_exe = os.path.join(get_prism_dir(), "prismlauncher.exe")
    if not os.path.exists(caminho_exe):
        logger.error(f"PrismLauncher.exe não encontrado em: {caminho_exe}")
        return False
    try:
        subprocess.Popen(
            [caminho_exe],
            cwd=get_prism_dir(),
            creationflags=subprocess.DETACHED_PROCESS
        )
        logger.info(f"Prism Launcher iniciado: {caminho_exe}")
        return True
    except Exception as e:
        logger.error(f"Erro ao iniciar Prism Launcher: {e}", exc_info=True)
        return False


def prism_instalado() -> bool:
    """Verifica se o Prism Launcher portátil está instalado."""
    caminho_exe = os.path.join(get_prism_dir(), "prismlauncher.exe")
    return os.path.exists(caminho_exe)


def jogo_esta_aberto(nome_exe: str) -> bool:
    nome_exe = os.path.basename(nome_exe).lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"].lower() == nome_exe:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def fechar_jogo(nome_exe: str) -> bool:
    nome_exe = os.path.basename(nome_exe).lower()
    encerrado = False
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"].lower() == nome_exe:
                proc.kill()
                encerrado = True
                logger.info(f"Processo encerrado: {nome_exe}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if not encerrado:
        logger.warning(f"Processo '{nome_exe}' não encontrado para encerrar.")
    return encerrado