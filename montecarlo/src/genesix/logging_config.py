"""Structured logging configuration for GenesiX."""

import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure structured logging for GenesiX.
    
    Logs to:
    1. Console (INFO+) — for Streamlit/development
    2. File: logs/genesix.log (DEBUG+) — for debugging
    3. File: logs/genesix_errors.log (ERROR+) — for monitoring
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    LOG_DIR.mkdir(exist_ok=True)
    
    logger = logging.getLogger('genesix')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler (INFO+)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, level.upper()))
    console.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(console)
    
    # File handler (DEBUG+, all messages)
    file_handler = logging.FileHandler(
        LOG_DIR / 'genesix.log',
        encoding='utf-8',
        mode='a'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(file_handler)
    
    # Error file handler (ERROR+ only, detailed)
    error_handler = logging.FileHandler(
        LOG_DIR / 'genesix_errors.log',
        encoding='utf-8',
        mode='a'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d\n%(message)s\n%(exc_info)s\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(error_handler)
    
    return logger


# Get module-level logger
logger = logging.getLogger('genesix')


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(f'genesix.{name}')
