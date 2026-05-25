"""Central logging configuration — rotating file logs via platformdirs."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_state_dir

APP_NAME = "strudel-gen"
LOG_DIR = Path(user_state_dir(APP_NAME, ensure_exists=True)) / "logs"
LOG_FILE = LOG_DIR / f"{APP_NAME}.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with a rotating file handler.

    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove default handlers to avoid duplicate logs
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Capture warnings via logging
    logging.captureWarnings(True)
