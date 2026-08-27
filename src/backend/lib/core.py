#!/usr/bin/env python3
"""Core application orchestrator for pyShelf."""

from .config import Config
from .library import Catalogue
from .storage import Storage


class PyShelfApp:
    """Orquestador principal de pyShelf."""

    def __init__(self, root_dir: str):
        self.config = Config(root_dir)
        self.storage = Storage(self.config)
        self.catalogue = Catalogue(self.config)

    def initialize_system(self):
        """Inicializa esquemas de tablas y sincroniza la biblioteca."""
        self.config.logger.info("[Core] Inicializando estructuras de base de datos...")
        self.storage.create_tables()
        self.storage.auto_discover_books()
        self.storage.make_collections()
        self.config.logger.info("[Core] Sistema listo.")
