"""pyShelf's Frontend Objects."""
from pathlib import Path
from backend.lib.config import Config


class JSInterface():
    """A class to interface with the JavaScript side of pyShelf."""

    def __init__(self, config: Config):
        """Initialize the JSInterface object."""
        self.config: Config = config

    def install(self):
        """Install the JavaScript dependencies (desactivado: sin dependencias de Node)."""
        pass
