import threading
import os
import sys

# Garante imports relativos ao repositório novo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.logger import setup_logger, get_logger

logger = setup_logger()
logger.info("Logger inicializado")

from config.settings import primeira_execucao, LAUNCHER_VERSION, obter_install_dir
from core.auto_updater import verificar_atualizacao_launcher, baixar_e_aplicar_update


def _garantir_exclusao_pasta_padrao():
    try:
        from core.antivirus import esta_excluida, adicionar_exclusao
        import threading
        pasta = obter_install_dir()
        if not esta_excluida(pasta):
            logger.info(f"Pasta padrão não excluída do Defender. Adicionando: {pasta}")
            os.makedirs(pasta, exist_ok=True)
            threading.Thread(
                target=adicionar_exclusao,
                args=(pasta,),
                daemon=True,
            ).start()
        else:
            logger.info("Pasta padrão já está excluída do Defender.")
    except Exception as e:
        logger.warning(f"Erro ao verificar exclusão do Defender: {e}")


def main():
    # ── Lock de instância única ───────────────────────────────────────────────
    import msvcrt
    import tempfile
    lock_path = os.path.join(
        os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
        "LDKLauncher", "launcher.lock"
    )
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        lock_file = open(lock_path, "w")
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        logger.warning("Outra instância já está rodando. Encerrando.")
        sys.exit(0)

    logger.info(f"LDKLauncher v{LAUNCHER_VERSION} iniciando...")

    # ── Qt app ────────────────────────────────────────────────────────────────
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    app = QApplication(sys.argv)
    app.setApplicationName("LDKLauncher")

    # Ícone global (taskbar, alt+tab)
    try:
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icone = os.path.join(base_path, "assets", "ldkf.ico")
        if os.path.exists(icone):
            app.setWindowIcon(QIcon(icone))
    except Exception:
        pass

    # ── Splash ────────────────────────────────────────────────────────────────
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()

    # ── Verifica atualização do launcher ──────────────────────────────────────
    splash.set_status("Verificando atualizações...")
    try:
        if verificar_atualizacao_launcher():
            logger.info("Iniciando processo de auto-update...")
            splash.set_status("Baixando atualização...")
            if baixar_e_aplicar_update(callback_status=splash.set_status):
                logger.info("Update aplicado. Encerrando para reiniciar.")
                splash.fechar()
                sys.exit(0)
    except Exception as e:
        logger.warning(f"Erro ao verificar atualização: {e}")

    # ── Antivírus (só se não é primeira execução) ─────────────────────────────
    if not primeira_execucao():
        splash.set_status("Verificando antivírus...")
        _garantir_exclusao_pasta_padrao()

    splash.set_status("Iniciando...")
    splash.fechar()

    # ── Janela principal ──────────────────────────────────────────────────────
    from ui.main_window import MainWindow
    janela = MainWindow()

    if primeira_execucao():
        logger.info("Primeira execução detectada — abrindo SetupWindow")
        from ui.setup_window import SetupWindow
        setup = SetupWindow(
            janela,
            callback_concluido=lambda: threading.Thread(target=janela._inicializar, daemon=True).start()
        )
        setup.exec()
    else:
        logger.info("Configuração existente — iniciando normalmente")
        threading.Thread(target=janela._inicializar, daemon=True).start()

    janela.show()
    logger.info("LDKLauncher iniciado")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()