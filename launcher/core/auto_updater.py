import os
import sys
import zipfile
import shutil
import requests
import subprocess
from launcher.config.settings import LAUNCHER_VERSION, CONNECTION_TIMEOUT
from launcher.config.logger import get_logger

logger = get_logger()

GITHUB_API_URL      = "https://api.github.com/repos/juliocmmo/LDKLauncher/releases/latest"
GITHUB_DOWNLOAD_URL = "https://github.com/juliocmmo/LDKLauncher/releases/latest/download/LDKLauncher.zip"


def _versao_tuple(versao: str) -> tuple:
    try:
        return tuple(int(x) for x in versao.strip().split("."))
    except Exception:
        return (0,)


def verificar_atualizacao_launcher() -> bool:
    if not getattr(sys, 'frozen', False):
        logger.info("Executando em modo dev — auto-update ignorado.")
        return False
    try:
        logger.info("Verificando atualizações do launcher via GitHub API...")
        resposta = requests.get(GITHUB_API_URL, timeout=CONNECTION_TIMEOUT)
        resposta.raise_for_status()

        dados      = resposta.json()
        tag_remota = dados.get("tag_name", "").lstrip("v")
        tag_local  = LAUNCHER_VERSION.lstrip("v")

        logger.info(f"Versão local: {tag_local} | Versão remota: {tag_remota}")

        if tag_remota and _versao_tuple(tag_remota) > _versao_tuple(tag_local):
            logger.info(f"Nova versão disponível: {tag_remota}")
            return True

        logger.info("Launcher já está na versão mais recente.")
        return False

    except requests.exceptions.ConnectionError:
        logger.warning("Sem conexão — verificação de update ignorada.")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Timeout ao verificar update do launcher.")
        return False
    except Exception as e:
        logger.warning(f"Erro ao verificar update do launcher: {e}")
        return False


def baixar_e_aplicar_update(callback_status=None) -> bool:
    def _status(texto: str):
        if callback_status:
            callback_status(texto)

    try:
        app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        temp_dir = os.path.join(app_data, "LDKLauncher", "update_tmp")
        os.makedirs(temp_dir, exist_ok=True)

        zip_path = os.path.join(temp_dir, "LDKLauncher_new.zip")

        logger.info(f"Baixando novo launcher de: {GITHUB_DOWNLOAD_URL}")
        resposta = requests.get(GITHUB_DOWNLOAD_URL, stream=True, timeout=300)
        resposta.raise_for_status()

        tamanho_total = int(resposta.headers.get("content-length", 0))
        baixados = 0
        with open(zip_path, "wb") as f:
            for bloco in resposta.iter_content(chunk_size=4194304):
                if bloco:
                    f.write(bloco)
                    baixados += len(bloco)
                    if tamanho_total > 0:
                        mb_baixados = baixados / 1024 / 1024
                        mb_total    = tamanho_total / 1024 / 1024
                        _status(f"Baixando atualização... {mb_baixados:.0f} / {mb_total:.0f} MB")

        logger.info(f"Zip baixado em: {zip_path}")
        _status("Aplicando atualização...")

        # Valida integridade do zip
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                resultado = z.testzip()
                if resultado is not None:
                    raise zipfile.BadZipFile(f"Arquivo corrompido: {resultado}")
        except (zipfile.BadZipFile, EOFError) as e:
            logger.error(f"Zip corrompido ou incompleto: {e}. Abortando update.")
            return False

        # Extrai o zip
        extract_dir = os.path.join(temp_dir, "extracted")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)

        logger.info(f"Zip extraído em: {extract_dir}")

        nova_pasta = os.path.join(extract_dir, "LDKLauncher")
        if not os.path.isdir(nova_pasta):
            nova_pasta = extract_dir

        launcher_exe = sys.executable
        launcher_dir = os.path.dirname(launcher_exe)
        exe_nome     = os.path.basename(launcher_exe)
        assets_dir   = os.path.join(launcher_dir, "assets")

        bat_path = os.path.join(temp_dir, "ldk_update.bat")

        bat_conteudo = (
            "@echo off\r\n"
            f'set "LAUNCHER_EXE={launcher_exe}"\r\n'
            f'set "LAUNCHER_DIR={launcher_dir}"\r\n'
            f'set "NOVA_PASTA={nova_pasta}"\r\n'
            f'set "TEMP_DIR={temp_dir}"\r\n'
            f'set "ASSETS_DIR={assets_dir}"\r\n'
            "timeout /t 2 /nobreak > nul\r\n"
            f'taskkill /f /im "{exe_nome}" > nul 2>&1\r\n'
            "timeout /t 3 /nobreak > nul\r\n"
            # Copia tudo exceto a pasta assets (thumbnails/ícones do usuário)
            'robocopy "%NOVA_PASTA%" "%LAUNCHER_DIR%" /E /IS /IT /IM /XD "%ASSETS_DIR%" /NJH /NJS /NFL /NDL /W:1 /R:3 > nul\r\n'
            "timeout /t 3 /nobreak > nul\r\n"
            'start "" "%LAUNCHER_EXE%"\r\n'
            "timeout /t 2 /nobreak > nul\r\n"
            'rmdir /s /q "%TEMP_DIR%" > nul 2>&1\r\n'
            'del "%~f0"\r\n'
        )

        with open(bat_path, "w", encoding="utf-8-sig") as f:
            f.write(bat_conteudo)

        logger.info("Script de atualização criado. Aplicando update...")

        subprocess.Popen(
            [bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao baixar update do launcher: {e}", exc_info=True)
        return False