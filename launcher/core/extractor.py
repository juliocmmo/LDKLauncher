import os
import sys
import zipfile
import shutil
import subprocess
from config.settings import get_temp_dir, get_prism_instances_dir
from config.logger import get_logger

logger = get_logger()


def _obter_7za() -> str | None:
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    caminho = os.path.join(base_path, "7za.exe")
    if os.path.exists(caminho):
        logger.info(f"7za.exe encontrado em: {caminho}")
        return caminho
    logger.warning("7za.exe não encontrado.")
    return None


def extrair_modpack(
    caminho_zip: str,
    caminho_destino: str,
    callback_progresso=None
) -> bool:
    """Extrai modpack standalone (jogos normais)."""
    os.makedirs(caminho_destino, exist_ok=True)

    with open(caminho_zip, "rb") as f:
        cabecalho = f.read(8)

    if cabecalho[:2] == b"PK":
        extensao = ".zip"
    else:
        extensao = ".rar"

    logger.info(f"Iniciando extração: {os.path.basename(caminho_zip)} (formato: {extensao})")

    try:
        if extensao == ".rar":
            sza = _obter_7za()
            if sza is None:
                logger.error("7za.exe não encontrado. Não é possível extrair.")
                return False

            cmd = [sza, "x", caminho_zip, f"-o{caminho_destino}", "-y"]
            logger.info(f"Executando: {' '.join(cmd)}")
            resultado = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if resultado.returncode != 0:
                erro = resultado.stderr.decode("utf-8", errors="ignore")
                logger.error(f"7za.exe falhou com código {resultado.returncode}: {erro}")
                _limpar_diretorio_parcial(caminho_destino)
                return False

            if callback_progresso:
                callback_progresso(1, 1)

        else:
            with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
                arquivos = zip_ref.namelist()
                total = len(arquivos)
                total_bytes = sum(zip_ref.getinfo(a).file_size for a in arquivos)
                bytes_feitos = 0
                for i, arquivo in enumerate(arquivos, start=1):
                    zip_ref.extract(arquivo, caminho_destino)
                    bytes_feitos += zip_ref.getinfo(arquivo).file_size
                    if callback_progresso:
                        callback_progresso(i, total, bytes_feitos, total_bytes)

        logger.info(f"Extração concluída em: {caminho_destino}")
        return True

    except Exception as e:
        logger.error(f"Erro durante extração: {e}", exc_info=True)
        _limpar_diretorio_parcial(caminho_destino)
        return False
    finally:
        _limpar_arquivo_temporario(caminho_zip)


def extrair_prism(caminho_zip: str, prism_dir: str, callback_progresso=None) -> bool:
    """Extrai o Prism Launcher portátil."""
    os.makedirs(prism_dir, exist_ok=True)
    logger.info(f"Extraindo Prism Launcher em: {prism_dir}")

    try:
        with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
            arquivos = zip_ref.namelist()
            total = len(arquivos)
            total_bytes = sum(zip_ref.getinfo(a).file_size for a in arquivos)
            bytes_feitos = 0
            for i, arquivo in enumerate(arquivos, start=1):
                zip_ref.extract(arquivo, prism_dir)
                bytes_feitos += zip_ref.getinfo(arquivo).file_size
                if callback_progresso:
                    callback_progresso(i, total, bytes_feitos, total_bytes)

        logger.info("Prism Launcher extraído com sucesso.")
        return True

    except Exception as e:
        logger.error(f"Erro ao extrair Prism Launcher: {e}", exc_info=True)
        _limpar_diretorio_parcial(prism_dir)
        return False
    finally:
        _limpar_arquivo_temporario(caminho_zip)


def extrair_instancia_minecraft(
    caminho_zip: str,
    instance_name: str,
    callback_progresso=None
) -> bool:
    """
    Extrai uma instância Minecraft para a pasta instances do Prism.

    Detecta automaticamente o formato:
    - Formato Prism: zip contém instance.cfg na raiz → extrai direto na pasta da instância
    - Formato direto: zip contém apenas .minecraft → cria estrutura Prism ao redor
    """
    instances_dir = get_prism_instances_dir()
    destino = os.path.join(instances_dir, instance_name)

    if os.path.exists(destino):
        shutil.rmtree(destino)
        logger.info(f"Instância anterior removida: {destino}")

    os.makedirs(destino, exist_ok=True)

    try:
        with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
            arquivos = zip_ref.namelist()
            total = len(arquivos)
            total_bytes = sum(zip_ref.getinfo(a).file_size for a in arquivos)
            bytes_feitos = 0

            # Detecta formato pelo conteúdo do zip
            nomes_raiz = {a.split("/")[0] for a in arquivos}
            formato_prism = "instance.cfg" in arquivos or "instance.cfg" in nomes_raiz

            if formato_prism:
                logger.info(f"Formato Prism detectado para '{instance_name}'.")
                for i, arquivo in enumerate(arquivos, start=1):
                    zip_ref.extract(arquivo, destino)
                    bytes_feitos += zip_ref.getinfo(arquivo).file_size
                    if callback_progresso:
                        callback_progresso(i, total, bytes_feitos, total_bytes)
            else:
                logger.info(f"Formato .minecraft detectado para '{instance_name}'. Criando estrutura Prism.")
                for i, arquivo in enumerate(arquivos, start=1):
                    zip_ref.extract(arquivo, destino)
                    bytes_feitos += zip_ref.getinfo(arquivo).file_size
                    if callback_progresso:
                        callback_progresso(i, total, bytes_feitos, total_bytes)

                # Cria instance.cfg e mmc-pack.json se não existirem
                _criar_arquivos_prism(destino, instance_name)

        logger.info(f"Instância '{instance_name}' extraída em: {destino}")
        return True

    except Exception as e:
        logger.error(f"Erro ao extrair instância Minecraft: {e}", exc_info=True)
        _limpar_diretorio_parcial(destino)
        return False
    finally:
        _limpar_arquivo_temporario(caminho_zip)


def _criar_arquivos_prism(destino: str, instance_name: str) -> None:
    """Cria instance.cfg e mmc-pack.json para instâncias no formato .minecraft direto."""
    instance_cfg = os.path.join(destino, "instance.cfg")
    mmc_pack = os.path.join(destino, "mmc-pack.json")

    if not os.path.exists(instance_cfg):
        with open(instance_cfg, "w", encoding="utf-8") as f:
            f.write(f"[General]\nname={instance_name}\n")
        logger.info(f"instance.cfg criado para '{instance_name}'.")

    if not os.path.exists(mmc_pack):
        import json
        dados = {
            "components": [
                {"cachedName": "Minecraft", "uid": "net.minecraft"}
            ],
            "formatVersion": 1
        }
        with open(mmc_pack, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2)
        logger.info(f"mmc-pack.json criado para '{instance_name}'.")


def _limpar_arquivo_temporario(caminho: str) -> None:
    if os.path.exists(caminho):
        os.remove(caminho)
        logger.info(f"Arquivo temporário removido: {caminho}")


def _limpar_diretorio_parcial(caminho: str) -> None:
    if os.path.exists(caminho):
        shutil.rmtree(caminho)
        logger.info(f"Diretório parcial removido: {caminho}")