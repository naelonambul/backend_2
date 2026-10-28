import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def configure_logging() -> None:
    root_logger = logging.getLogger()
    handler = next(
        (handler for handler in root_logger.handlers if handler.name == "app_rotating_file"),
        None,
    )
    if handler is None:
        handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
            delay=True,
        )
        handler.name = "app_rotating_file"
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        root_logger.addHandler(handler)

    root_logger.setLevel(logging.INFO)
    # Uvicorn's default loggers do not propagate to the root logger.
    for name in ("uvicorn", "uvicorn.access"):
        logger = logging.getLogger(name)
        if not logger.propagate and handler not in logger.handlers:
            logger.addHandler(handler)
