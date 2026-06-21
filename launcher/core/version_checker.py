import json
import os
import requests
from launcher.config.settings import REMOTE_VERSION_URL, LOCAL_VERSION_FILE, CONNECTION_TIMEOUT
from launcher.config.logger import get_logger

logger = get_logger()


def buscar_versao_remota() -> dict | None:
    import time
    logger.info("Buscando version.json remoto...")
    try:
        url = f"{REMOTE_VERSION_URL}?t={int(time.time())}"
        resposta = requests.get(
            url,
            timeout=CONNECTION_TIMEOUT,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}
        )
        resposta.raise_for_status()
        dados = resposta.json()
        logger.info(f"version.json obtido com {len(dados.get('modpacks', []))} modpack(s)")
        return dados
    except requests.exceptions.ConnectionError:
        logger.error("Sem conexão com a internet.")
        return None
    except requests.exceptions.Timeout:
        logger.error("Tempo de conexão esgotado.")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erro HTTP ao buscar versão remota: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar versão remota: {e}", exc_info=True)
        return None


def carregar_versao_local() -> dict:
    if not os.path.exists(LOCAL_VERSION_FILE):
        logger.info("version_local.json não encontrado — nenhum modpack instalado ainda.")
        return {}
    try:
        with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        logger.info(f"version_local.json carregado com {len(dados)} entrada(s)")
        return dados
    except Exception as e:
        logger.error(f"Erro ao ler versão local: {e}", exc_info=True)
        return {}


def salvar_versao_local(dados: dict) -> None:
    os.makedirs(os.path.dirname(LOCAL_VERSION_FILE), exist_ok=True)
    try:
        with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        logger.info("version_local.json salvo com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao salvar versão local: {e}", exc_info=True)


def obter_info_prism(remoto: dict) -> dict | None:
    """Retorna as informações do Prism Launcher do campo shared, se existir."""
    return remoto.get("shared", {}).get("prism_launcher", None)


def verificar_status_modpacks(remoto: dict, local: dict) -> list:
    resultado = []

    for modpack in remoto.get("modpacks", []):
        nome          = modpack["name"]
        versao_remota = modpack["version"]
        versao_local  = local.get(nome, {}).get("version", None)
        tipo          = modpack.get("type", "standalone")

        if versao_local is None:
            status = "nao_instalado"
        elif versao_local != versao_remota:
            status = "desatualizado"
        else:
            status = "atualizado"

        logger.info(f"{nome}: local={versao_local} | remoto={versao_remota} | status={status} | tipo={tipo}")

        resultado.append({
            "name":           nome,
            "version_remote": versao_remota,
            "version_local":  versao_local,
            "status":         status,
            "type":           tipo,
            "description":    modpack.get("description", ""),
            "thumbnail_url":    modpack.get("thumbnail_url", ""),
            "thumbnail_offset": modpack.get("thumbnail_offset", 0),
            "icon_url":         modpack.get("icon_url", ""),
            "file_url":       modpack.get("file_url", ""),
            "hash_sha256":    modpack.get("hash_sha256", ""),
            "size_bytes":     modpack.get("size_bytes", 0),
            "install_path":   modpack.get("install_path", ""),
            "executable":     modpack.get("executable", ""),
            "instance_name":  modpack.get("instance_name", ""),
            "last_played": local.get(nome, {}).get("last_played", ""),
        })

    return resultado