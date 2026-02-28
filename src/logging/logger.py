import logging
import sys


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a configured logger. Use module __name__ or leave None for root."""
    logger = logging.getLogger(name or "audit_backend")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
