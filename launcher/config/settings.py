import os
import json

# ─── Informações do Launcher ───────────────────────────────────────────────────
LAUNCHER_NAME    = "LDKLauncher"
LAUNCHER_VERSION = "1.2.3"

# ─── Pasta fixa para configurações do launcher ─────────────────────────────────
CONFIG_DIR  = os.path.join(os.environ["LOCALAPPDATA"], LAUNCHER_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ─── Pasta padrão sugerida para instalação ────────────────────────────────────
DEFAULT_INSTALL_DIR = r"C:\LDKLauncher"

# ─── Funções de configuração ──────────────────────────────────────────────────

def carregar_config() -> dict:
    """Carrega as configurações salvas ou retorna os padrões."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def salvar_config(config: dict) -> None:
    """Salva as configurações no arquivo de configuração."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def obter_install_dir() -> str:
    """Retorna a pasta de instalação configurada pelo usuário."""
    config = carregar_config()
    return config.get("install_dir", DEFAULT_INSTALL_DIR)

def obter_install_dir_jogo(nome_jogo: str) -> str:
    """Retorna o diretório BASE de instalação de um jogo específico
    (sem a subpasta do jogo), ou a pasta padrão se não houver customização."""
    from launcher.core.version_checker import carregar_versao_local
    local = carregar_versao_local()
    custom = local.get(nome_jogo, {}).get("install_dir")
    if not custom:
        return obter_install_dir()
    # Corrige entradas antigas que guardavam o caminho completo incluindo
    # a subpasta do jogo (ex: C:\LDKLauncher\GameName em vez de C:\LDKLauncher).
    if os.path.basename(custom) == nome_jogo:
        return os.path.dirname(custom)
    return custom

def primeira_execucao() -> bool:
    """Retorna True se o launcher nunca foi configurado."""
    return not os.path.exists(CONFIG_FILE)

# ─── Caminhos dinâmicos ───────────────────────────────────────────────────────
def get_install_dir() -> str:
    return obter_install_dir()

def get_local_version_file() -> str:
    return os.path.join(CONFIG_DIR, "version_local.json")

def get_temp_dir() -> str:
    return os.path.join(obter_install_dir(), "temp")

def get_prism_dir() -> str:
    return os.path.join(obter_install_dir(), "PrismLauncher")

def get_prism_instances_dir() -> str:
    return os.path.join(get_prism_dir(), "instances")

# ─── Compatibilidade com o código existente ───────────────────────────────────
INSTALL_DIR        = obter_install_dir()
LOCAL_VERSION_FILE = get_local_version_file()
TEMP_DIR           = get_temp_dir()

# ─── URL do manifesto remoto ───────────────────────────────────────────────────
REMOTE_VERSION_URL = (
    "https://raw.githubusercontent.com/juliocmmo/modpack-launcher-config"
    "/refs/heads/main/version.json"
)

# ─── Timeouts de rede (segundos) ──────────────────────────────────────────────
CONNECTION_TIMEOUT = 10
DOWNLOAD_TIMEOUT   = 300