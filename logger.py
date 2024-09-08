import logging
from datetime import datetime
import os

# Definujeme novou úroveň logování
USER = 25
logging.addLevelName(USER, 'USER')


def setup_logging():
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Použij pomlčky místo dvojteček v časovém razítku
    current_time = datetime.now().strftime("log-%d-%m-%Y-%H-%M-%S")
    log_file_path = os.path.join(log_directory, f"{current_time}.txt")

    # Nastavení formátu logování
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Vytvoření logovacího handleru pro zápis do souboru
    file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Vytvoření logovacího handleru pro výpis na konzoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Konfigurace globálního logování
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

    # Ujistěte se, že všechny logy od debug a výše jsou zachyceny
    # logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)


def log_user(message):
    logger = logging.getLogger('DocumentProcessor')
    logger.log(USER, message)


def log_warning(message):
    logger = logging.getLogger('DocumentProcessor')
    logger.warning(message)


def log_info(message):
    logger = logging.getLogger('DocumentProcessor')

