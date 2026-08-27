"""pyShelf's frontend database hooks."""
from backend.lib.storage import Storage


class BookInterface:
    """Access point for book database."""

    def __init__(self, config):
        """Initialize class variables."""
        self.config = config
        self.db = Storage(self.config)
