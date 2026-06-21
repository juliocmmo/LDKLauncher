import os
import hashlib
import json
import base64
import threading
import requests
from launcher.config.settings import get_temp_dir, DOWNLOAD_TIMEOUT
from launcher.config.logger import get_logger

logger = get_logger()


def calcular_hash(caminho_arquivo: str, callback_progresso=None) -> str:
    sha256 = hashlib.sha256()
    try:
        tamanho = os.path.getsize(caminho_arquivo)
        processado = 0
        with open(caminho_arquivo, "rb") as f:
            for bloco in iter(lambda: f.read(33554432), b""):
                sha256.update(bloco)
                processado += len(bloco)
                if callback_progresso and tamanho > 0:
                    callback_progresso(processado, tamanho)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Erro ao calcular hash: {e}")
        return ""


def verificar_espaco_disco(tamanho_necessario: int, caminho: str) -> bool:
    import shutil
    total, usado, livre = shutil.disk_usage(caminho)
    if livre < tamanho_necessario:
        logger.error(f"Espaço insuficiente. Necessário: {tamanho_necessario / 1e9:.2f} GB, Disponível: {livre / 1e9:.2f} GB")
        return False
    return True


def _extrair_id_google_drive(url: str) -> str | None:
    import re
    padrao = r"/file/d/([a-zA-Z0-9_-]+)"
    match = re.search(padrao, url)
    if match:
        return match.group(1)
    padrao2 = r"id=([a-zA-Z0-9_-]+)"
    match2 = re.search(padrao2, url)
    if match2:
        return match2.group(1)
    padrao3 = r"/folders/([a-zA-Z0-9_-]+)"
    match3 = re.search(padrao3, url)
    if match3:
        return match3.group(1)
    return None


def _get_service_account_token() -> str:
    """Obtém access token via Service Account (credencial em memória)."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest

    try:
        from core.credentials import SERVICE_ACCOUNT_B64
    except ImportError:
        raise RuntimeError("Arquivo core/credentials.py não encontrado.")

    credencial_json = json.loads(base64.b64decode(SERVICE_ACCOUNT_B64).decode("utf-8"))

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    credenciais = service_account.Credentials.from_service_account_info(
        credencial_json, scopes=scopes
    )
    credenciais.refresh(GoogleRequest())
    return credenciais.token


def _baixar_google_drive_api(
    file_id: str,
    caminho_destino: str,
    tamanho_total: int,
    callback_progresso=None,
    cancel_event: threading.Event | None = None
) -> str | None:
    """Baixa arquivo do Google Drive autenticado via Service Account."""
    try:
        token = _get_service_account_token()
    except Exception as e:
        logger.error(f"Erro ao obter token do Service Account: {e}")
        return None

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" in content_type:
            logger.error(f"Drive retornou HTML mesmo com autenticação. Content-Type: {content_type}")
            return None

        tamanho_real = int(resp.headers.get("Content-Length", 0)) or tamanho_total
        logger.info(f"Tamanho real: {tamanho_real / 1e6:.1f} MB")

        bytes_baixados = 0
        with open(caminho_destino, "wb") as f:
            for bloco in resp.iter_content(chunk_size=4194304):  # 4MB chunks
                if cancel_event and cancel_event.is_set():
                    logger.info("Download cancelado pelo usuário (Drive API).")
                    _limpar_arquivo_parcial(caminho_destino)
                    return None
                if bloco:
                    f.write(bloco)
                    bytes_baixados += len(bloco)
                    if callback_progresso:
                        callback_progresso(bytes_baixados, tamanho_real)

        logger.info(f"Download concluído via Service Account: {caminho_destino}")
        return caminho_destino

    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP no download via API: {e} | Status: {resp.status_code}")
        _limpar_arquivo_parcial(caminho_destino)
        return None
    except Exception as e:
        logger.error(f"Erro no download via Service Account: {e}", exc_info=True)
        _limpar_arquivo_parcial(caminho_destino)
        return None


def baixar_arquivo(
    url: str,
    nome_arquivo: str,
    tamanho_total: int,
    callback_progresso=None,
    cancel_event: threading.Event | None = None
) -> str | None:
    os.makedirs(get_temp_dir(), exist_ok=True)
    caminho_destino = os.path.join(get_temp_dir(), nome_arquivo)

    logger.info(f"Iniciando download: {nome_arquivo} ({tamanho_total / 1e6:.1f} MB)")

    if not verificar_espaco_disco(tamanho_total, get_temp_dir()):
        return None

    if "drive.google.com" in url:
        file_id = _extrair_id_google_drive(url)
        if file_id is None:
            logger.error("Não foi possível extrair o ID do Google Drive.")
            return None
        logger.info(f"Google Drive detectado. File ID: {file_id}")
        return _baixar_google_drive_api(
            file_id, caminho_destino, tamanho_total, callback_progresso, cancel_event
        )

    try:
        resposta = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
        resposta.raise_for_status()

        bytes_baixados = 0
        with open(caminho_destino, "wb") as f:
            for bloco in resposta.iter_content(chunk_size=8192):
                if cancel_event and cancel_event.is_set():
                    logger.info("Download cancelado pelo usuário.")
                    _limpar_arquivo_parcial(caminho_destino)
                    return None
                if bloco:
                    f.write(bloco)
                    bytes_baixados += len(bloco)
                    if callback_progresso:
                        callback_progresso(bytes_baixados, tamanho_total)

        logger.info(f"Download concluído: {caminho_destino}")
        return caminho_destino

    except requests.exceptions.ConnectionError:
        logger.error("Conexão perdida durante o download.")
        _limpar_arquivo_parcial(caminho_destino)
        return None
    except requests.exceptions.Timeout:
        logger.error("Tempo esgotado durante o download.")
        _limpar_arquivo_parcial(caminho_destino)
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP durante o download: {e}")
        _limpar_arquivo_parcial(caminho_destino)
        return None
    except OSError as e:
        logger.error(f"Erro de permissão ou disco: {e}", exc_info=True)
        _limpar_arquivo_parcial(caminho_destino)
        return None
    except Exception as e:
        logger.error(f"Erro inesperado durante o download: {e}", exc_info=True)
        _limpar_arquivo_parcial(caminho_destino)
        return None


def validar_arquivo(caminho_arquivo: str, hash_esperado: str, callback_progresso=None) -> bool:
    logger.info("Validando integridade do arquivo...")
    hash_real = calcular_hash(caminho_arquivo, callback_progresso)
    if hash_real != hash_esperado:
        logger.error(f"Hash inválido. Esperado: {hash_esperado} | Obtido: {hash_real}")
        _limpar_arquivo_parcial(caminho_arquivo)
        return False
    logger.info("Arquivo válido.")
    return True


def _limpar_arquivo_parcial(caminho: str) -> None:
    if os.path.exists(caminho):
        try:
            os.remove(caminho)
            logger.info(f"Arquivo parcial removido: {caminho}")
        except PermissionError:
            logger.warning(f"Arquivo em uso, será removido depois: {caminho}")