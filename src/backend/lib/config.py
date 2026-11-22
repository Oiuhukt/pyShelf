"""Pyshelf's Configuration Object."""
import json
import os
from pathlib import Path, PurePath
from loguru import logger


class Config:
    """Main System Configuration."""

    _logger_initialized = False

    def __init__(self, root):
        self.root = root
        self._cp = Path(root, "config.json")
        self._data = self._load_config()
        self.logger = self._get_logger()

        self.book_path = os.environ.get(
            "BOOKPATH",
            self._data.get("BOOKPATH", "/usr/local/biblioteca")
        )
        self.db_engine = "sqlite"  # hardcodeado: solo SQLite

    def _load_config(self):
        try:
            with open(self._cp, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _get_logger(self):
        if not Config._logger_initialized:
            log_dir = Path(self.root, "data")
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(log_dir / "pyshelf.log"),
                rotation="2 MB",
                enqueue=False,
                colorize=True
            )
            Config._logger_initialized = True
        return logger
