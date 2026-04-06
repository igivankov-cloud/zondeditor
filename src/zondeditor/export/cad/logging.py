from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CAD_LOGGER_NAME = "ZondEditor.CAD"


def cad_log_path() -> Path:
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "cad_export.log"


def get_cad_logger() -> logging.Logger:
    logger = logging.getLogger(_CAD_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = RotatingFileHandler(cad_log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
