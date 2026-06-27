"""
shared/drive_utils.py
Utilitário compartilhado para download autenticado de assets do Google Drive
(thumbnails, ícones) via Service Account.
"""

import json
import base64
import threading
import requests
from pathlib import Path

from launcher.config.logger import get_logger

logger = get_logger()

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_token_cache: dict = {"token": None, "expiry": None}
_token_lock = threading.Lock()


def _get_token() -> str:
    """Obtém access token via Service Account, com cache simples."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest
    from datetime import datetime, timezone

    with _token_lock:
        agora = datetime.now(timezone.utc)
        expiry = _token_cache["expiry"]
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if _token_cache["token"] and expiry and agora < expiry:
            return _token_cache["token"]

        try:
            from launcher.core.credentials import SERVICE_ACCOUNT_B64
        except ImportError:
            raise RuntimeError("shared/credentials.py não encontrado.")

        cred_json = json.loads(base64.b64decode(SERVICE_ACCOUNT_B64).decode("utf-8"))
        creds = service_account.Credentials.from_service_account_info(cred_json, scopes=_SCOPES)
        creds.refresh(GoogleRequest())

        _token_cache["token"]  = creds.token
        _token_cache["expiry"] = creds.expiry
        return creds.token


def _extrair_id(url: str) -> str | None:
    import re
    for padrao in [r"/file/d/([a-zA-Z0-9_-]+)", r"id=([a-zA-Z0-9_-]+)"]:
        m = re.search(padrao, url)
        if m:
            return m.group(1)
    return None


def baixar_asset_drive(url: str, destino: Path, cancel_event: threading.Event | None = None) -> bool:
    """
    Baixa um asset (thumbnail, ícone) do Google Drive autenticado.
    Retorna True se bem-sucedido, False caso contrário.
    """
    file_id = _extrair_id(url)
    if not file_id:
        logger.warning(f"URL de asset inválida: {url}")
        return False

    try:
        token = _get_token()
    except Exception as e:
        logger.warning(f"Não foi possível obter token para asset: {e}")
        return False

    api_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(api_url, headers=headers, stream=True, timeout=15)
        resp.raise_for_status()

        if "text/html" in resp.headers.get("Content-Type", ""):
            logger.warning(f"Drive retornou HTML para asset {file_id}")
            return False

        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as f:
            for bloco in resp.iter_content(chunk_size=524288):  # 512 KB
                if cancel_event and cancel_event.is_set():
                    return False
                if bloco:
                    f.write(bloco)

        logger.info(f"Asset baixado: {destino.name}")
        return True

    except Exception as e:
        logger.warning(f"Erro ao baixar asset {file_id}: {e}")
        if destino.exists():
            destino.unlink()
        return False