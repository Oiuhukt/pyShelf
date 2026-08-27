"""Pyshelf's Configuration Object."""
import json
from pathlib import Path, PurePath
import os
from loguru import logger


class Config:
    """Main System Configuration."""

    # Variable de clase para asegurar que el Sink del archivo de logs se registre SOLO UNA VEZ
    _logger_initialized = False

    def __init__(self, root):
        """Initialize main configuration options."""
        self.root = root
        self.config_structure = {
            "TITLE": "pyShelf E-Book Server",
            "VERSION": "0.7.0",
            "BOOKPATH": "/usr/local/biblioteca",
            "DB_HOST": "localhost",
            "DB_PORT": "5432",
            "DB_ENGINE": "sqlite",
            "DATABASE": "pyshelf",
            "USER": "pyshelf",
            "PASSWORD": "pyshelf",
            "BOOKSHELF": "data/shelf.json",
            "ALLOWED_HOSTS": [
                "localhost",
                "127.0.0.1",
                "[::1]",
                "0.0.0.0"
            ],
            "BUILD_MODE": "development"
        }
        env = os.environ.copy()
        self._fp = "config.json"
        try:
            self._cp = Path.joinpath(root, self._fp)
        except AttributeError:
            self._cp = Path(root, self._fp)
        
        self._data = self.init_config()
        
        # Inicializa o reutiliza el logger singleton
        self.logger = self.get_logger()

        self.book_path = env.get("BOOKPATH", self._data["BOOKPATH"])
        self.TITLE = env.get("TITLE", self._data["TITLE"])
        self.VERSION = env.get("VERSION", self._data["VERSION"])
        self.TITLE = self.TITLE + " ver " + self.VERSION
        self.book_shelf = env.get("BOOKSHELF", self._data["BOOKSHELF"])
        self.catalogue_db = env.get("DATABASE", self._data["DATABASE"])
        self.user = self._data["USER"]
        self.password = self._data["PASSWORD"]
        self.db_host = env.get("DB_HOST", self._data["DB_HOST"])
        self.db_port = env.get("DB_PORT", self._data["DB_PORT"])
        self.file_array = [self.book_shelf]
        self.auto_scan = True
        self.allowed_hosts = env.get("ALLOWED_HOSTS",
                                     self._data["ALLOWED_HOSTS"])
        self.db_engine = env.get("DB_ENGINE", self._data["DB_ENGINE"])
        self.db_user = env.get("USER", self._data["USER"])
        self.db_pass = env.get("PASSWORD", self._data["PASSWORD"])
        self.build_mode = env.get("BUILD_MODE", self._data["BUILD_MODE"])

    def init_config(self):
        try:
            return self.open_file()
        except FileNotFoundError:
            with open(self._fp, 'w') as _config_file:
                json.dump(self.config_structure, _config_file)
            return self.open_file()

    def get_logger(self):
        """Instantiate logging system cleanly without thread leaks."""
        if not Config._logger_initialized:
            log_file = PurePath(self.root, 'data', 'pyshelf.log')
            # enqueue=False previene spawnear hilos en background por cada handler
            logger.add(
                log_file,
                rotation="2 MB",
                enqueue=False,
                colorize=True
            )
            Config._logger_initialized = True
        return logger

    def open_file(self):
        """Open config.json and reads in configuration options."""
        with open(str(self._cp), "r") as read_file:
            data = json.load(read_file)
        return data
