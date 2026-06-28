import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _get_log_dir() -> str:
    """Retorna a pasta de logs — %LOCALAPPDATA%\LDKLauncher\logs em produção, raiz do projeto em dev."""
    if getattr(sys, 'frozen', False):
        # Modo compilado: sempre em %LOCALAPPDATA%\LDKLauncher\logs
        # Garante permissão de escrita independente de onde o exe está instalado
        # (Program Files, localappdata, etc.)
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(local_app_data, "LDKLauncher", "logs")
    else:
        # Modo dev: pasta raiz do projeto
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def setup_logger() -> logging.Logger:
    log_dir  = _get_log_dir()
    log_file = os.path.join(log_dir, "launcher.log")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("LDKLauncher")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_048_576,  # 1MB por arquivo
        backupCount=2,        # mantém launcher.log + launcher.log.1
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "LDKLauncher") -> logging.Logger:
    return logging.getLogger(name)