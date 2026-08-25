"""Pyshelf's Main Storage Class."""
import re
from collections import defaultdict
from rapidfuzz import process, fuzz
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pathlib import Path

from .models import Book, Collection, BookCollection


class Storage:
    """Create a new Storage object."""

    def __init__(self, config):
        """Initialize storage object."""
        self.config = config
        self.sql = self.config.catalogue_db
        self.user = self.config.user
        self.password = self.config.password
        self.db_host = self.config.db_host
        self.db_port = self.config.db_port
        self.engine = create_engine(self.get_connection_string(), pool_pre_ping=True)

    def get_connection_string(self):
        """Get connection string."""
        if self.config.db_engine == "sqlite":
            return f"sqlite:////{self.config.root}/pyshelf.sqlite3"
        elif self.config.db_engine == "psql":
            return f"postgresql://{self.user}:{self.password}@{self.db_host}:{self.db_port}/{self.sql}"
        elif self.config.db_engine == "mysql":
            return f"mysql://{self.user}:{self.password}@{self.db_host}:{self.db_port}/{self.sql}"

    def create_tables(self):
        """Create table structure."""
        tables = [Book, Collection]
        for table in tables:
            table.metadata.create_all(self.engine)

    def insert_book(self, book):
        """Insert a new book into the database."""
        with Session(self.engine) as session:
            try:
                try:
                    cover_image = book[2].data
                except Exception:
                    cover_image = book[2]
                if not book[2]:
                    cover_image = None

                _book = Book(
                    title=book[0],
                    author=book[1],
                    cover=cover_image,
                    file_name=book[3],
                    description=book[4],
                    identifier=book[5],
                    publisher=book[6],
                    rights=book[8],
                    tags=book[9],
                )
                session.add(_book)
                session.commit()
                session.close()
                return True
            except Exception as e:
                self.config.logger.error(f"{book[0][0:80]} :: {e}")
                return False

    def book_paths_list(self):
        """Get file paths from database for comparison to system files."""
        session = Session(self.engine)
        _result = session.scalars(select(Book.file_name)).fetchall()
        session.close()
        return _result

    def parse_collections_from_path(self, book: dict) -> list:
        """Parse book paths to determine common folder structure."""
        collections = []
        title_regx = re.compile(r"^[0-9][0-9]*|-|\ \B")
        book_path: Path = Path(book[3])
        store_path: Path = Path(self.config.book_path)
        relative_book_path: Path = book_path.relative_to(store_path)
        for folder in relative_book_path.parts[:-1]:
            clean_name = re.sub(title_regx, "", folder).strip()
            if clean_name:
                collections.append(clean_name)
        return collections

    def make_collections(self):
        """Ensure collections exist and link them to books (many-to-many)."""
        self.config.logger.info("Making collections.")
        session = Session(self.engine)

        books = session.execute(select(Book.id, Book.file_name)).all()

        for book_id, file_name in books:
            try:
                relative_parts = Path(file_name).relative_to(self.config.book_path).parts
            except ValueError:
                continue
            if len(relative_parts) < 2:
                folder = "Unsorted"
            else:
                folder = relative_parts[0]

            collection = session.execute(
                select(Collection).where(Collection.name == folder)
            ).scalar_one_or_none()
            if not collection:
                collection = Collection(name=folder)
                session.add(collection)
                session.flush()

            link_exists = session.execute(
                select(BookCollection).where(
                    BookCollection.book_id == book_id,
                    BookCollection.collection_id == collection.id
                )
            ).first()

            if not link_exists:
                session.add(BookCollection(book_id=book_id, collection_id=collection.id))

        session.commit()
        session.close()
        self.config.logger.info("Finished making collections.")

    def get_books(self, collection=None, skip=None, limit=None):
        """Get books from database."""
        with Session(self.engine) as session:
            if collection is not None:
                result = session.execute(
                    select(Book)
                    .join(BookCollection)
                    .where(BookCollection.collection_id == collection)
                    .offset(skip or 0)
                    .limit(limit)
                ).scalars().all()
            else:
                result = session.execute(
                    select(Book)
                    .offset(skip or 0)
                    .limit(limit)
                ).scalars().all()
        return result

    def get_book(self, id):
        """Get book from database."""
        session = Session(self.engine)
        _result = session.execute(select(Book).where(Book.id == id)).first()
        session.close()
        return _result

    def get_collections(self):
        """Get collections from database."""
        with Session(self.engine) as session:
            result = session.execute(
                select(Collection).join(BookCollection).distinct()
            ).scalars().all()
        return result

    def get_collection(self, name):
        """Get collection from database."""
        session = Session(self.engine)
        _result = session.execute(select(Collection).where(Collection.name == name).join(Book)).all()
        session.close()
        return _result

    def fuzzy_search_books(self, query: str, limit: int = 30):
        """Búsqueda por nombre de archivo manteniendo el orden de relevancia descendente."""
        with Session(self.engine) as session:
            books = session.execute(select(Book)).scalars().all()

        book_map = {b.id: b.file_name or "" for b in books if b.file_name}

        fuzzy_results = process.extract(
            query,
            book_map,
            scorer=fuzz.WRatio,
            limit=limit
        )

        books_by_id = {b.id: b for b in books}
        matched_books = []
        for match, score, book_id in fuzzy_results:
            if score > 30:
                book = books_by_id.get(book_id)
                if book:
                    matched_books.append(book)

        return matched_books
