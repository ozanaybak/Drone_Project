import logging
import os
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with the specified name.
    Configures a console handler and a rotating file handler
    that writes to logs/{name}.log with max size 1MB and 3 backups.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        ch.setFormatter(console_format)
        logger.addHandler(ch)

        # Ensure logs directory exists
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # File handler
        log_file = os.path.join(logs_dir, f"{name.lower()}.log")
        fh = RotatingFileHandler(log_file, maxBytes=1*1024*1024, backupCount=3)
        fh.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(file_format)
        logger.addHandler(fh)

    return logger

def set_global_log_level(level_str: str):
    """
    Set the root logger's level based on a string name.
    """
    import logging
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
