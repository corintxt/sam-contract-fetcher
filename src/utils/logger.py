import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure the logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=LOG_LEVEL
)

def log_info(message):
    logging.info(message)

def log_warning(message):
    logging.warning(message)

def log_error(message):
    logging.error(message)

def log_debug(message):
    logging.debug(message)