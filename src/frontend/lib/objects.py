"""pyShelf's Frontend Objects."""
from backend.lib.config import Config


class JSInterface:
    """A class to interface with the JavaScript side of pyShelf."""

    def __init__(self, config: Config):
        """Initialize the JSInterface object."""
        self.config: Config = config
