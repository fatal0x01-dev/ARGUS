"""
Centralised logger for the orchestrator system.
Call get_logger(__name__) in every module.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import config.settings as cfg


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    level = getattr(logging, cfg.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (rotating, 5 MB × 3 backups)
    if cfg.LOG_TO_FILE:
        os.makedirs(os.path.dirname(cfg.LOG_FILE), exist_ok=True)
        fh = RotatingFileHandler(cfg.LOG_FILE, maxBytes=5_000_000, backupCount=3)
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.propagate = False
    return logger