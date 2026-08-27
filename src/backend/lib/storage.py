"""Pyshelf's Main Storage Class."""

import re
import os
import glob
import hashlib
import datetime
import subprocess
from pathlib import Path
from collections import defaultdict
from rapidfuzz import process, fuzz
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import Book, Collection, BookCollection


class Storage:
    """Create a new Storage object."""

    def __init__(self, config):
        """Initialize storage object."""
        self.config = config
        self.sql = self.config.catalogue_db
        self.user = self.config.user
        self.password = self.password = self.config.password
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

    def get_sample_text_for_file(self, pdf_path: str) -> str | None:
        """Busca en ./paginas_aleatorias un .txt que coincida con el nombre del archivo."""
        destino = "./paginas_aleatorias"
        if not os.path.exists(destino):
            return None

        filename_no_ext = os.path.splitext(os.path.basename(pdf_path))[0]
        for txt_file in os.listdir(destino):
            if txt_file.startswith(filename_no_ext) and txt_file.endswith(".txt"):
                txt_path = os.path.join(destino, txt_file)
                try:
                    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read().strip()
                except Exception:
                    return None
        return None

    def generate_pdf_cover(self, pdf_path: str, book_id: int | str, force: bool = False) -> str | None:
        """Genera la portada JPG llamando directamente a pdftoppm nativo de Poppler."""
        covers_dir = Path(self.config.root) / "src" / "frontend" / "static" / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)
        
        output_prefix = str(covers_dir / str(book_id))
        final_jpg = covers_dir / f"{book_id}.jpg"
        relative_cover_path = f"covers/{book_id}.jpg"

        if final_jpg.exists() and not force and final_jpg.stat().st_size > 0:
            return relative_cover_path

        try:
            # Comando de Poppler: extrae página 1 a JPG escalado
            cmd = [
                "pdftoppm",
                "-jpeg",
                "-f", "1",
                "-l", "1",
                "-singlefile",
                "-scale-to", "600",
                pdf_path,
                output_prefix
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return relative_cover_path
        except Exception as e:
            self.config.logger.error(f"[Storage] Error generando portada con pdftoppm para ID {book_id}: {e}")
        return None

    def auto_discover_books(self):
        """Descubre nuevos PDFs/EPUBs e inserta o actualiza portadas en la BD."""
        search_path = getattr(self.config, 'book_path', '/usr/local/biblioteca')
        files = sorted(
            glob.glob(f'{search_path}/**/*.pdf', recursive=True) +
            glob.glob(f'{search_path}/**/*.epub', recursive=True)
        )
        now = datetime.datetime.now()
        new_count = 0

        with Session(self.engine) as session:
            for path in files:
                existing = session.execute(
                    select(Book).where(Book.file_name == path)
                ).scalar_one_or_none()

                parent_dir = os.path.basename(os.path.dirname(path))
                category = parent_dir if parent_dir.lower() != 'biblioteca' else 'General'
                sample_txt = self.get_sample_text_for_file(path)

                if existing:
                    existing.categories = category
                    if sample_txt:
                        existing.sample_text = sample_txt
                    
                    # Generar portada si falta o no está en la BD
                    if not existing.cover or not (Path(self.config.root) / "src" / "frontend" / "static" / existing.cover).exists():
                        cover_rel_path = self.generate_pdf_cover(path, existing.id)
                        if cover_rel_path:
                            existing.cover = cover_rel_path
                else:
                    title = os.path.splitext(os.path.basename(path))[0]
                    new_book = Book(
                        title=title,
                        author="Desconocido",
                        file_name=path,
                        cover="",
                        date=now,
                        categories=category,
                        sample_text=sample_txt
                    )
                    session.add(new_book)
                    session.flush()  # Genera new_book.id
                    
                    cover_rel_path = self.generate_pdf_cover(path, new_book.id)
                    if cover_rel_path:
                        new_book.cover = cover_rel_path
                    
                    new_count += 1
            session.commit()
        self.config.logger.info(f"[Storage] Libros sincronizados: {new_count} nuevos.")

    def regenerate_all_covers(self, force: bool = True):
        """Fuerza la regeneración masiva de portadas de todos los libros."""
        with Session(self.engine) as session:
            books = session.execute(select(Book)).scalars().all()
            updated_count = 0
            for book in books:
                if book.file_name and os.path.exists(book.file_name):
                    cover_rel_path = self.generate_pdf_cover(book.file_name, book.id, force=force)
                    if cover_rel_path:
                        book.cover = cover_rel_path
                        updated_count += 1
            session.commit()
        self.config.logger.info(f"[Storage] Se regeneraron {updated_count} portadas con pdftoppm.")

    def clean_orphaned_books(self):
        """Elimina de la BD los registros de archivos borrados en disco y sus portadas."""
        covers_dir = Path(self.config.root) / "src" / "frontend" / "static" / "covers"
        deleted_count = 0

        with Session(self.engine) as session:
            books = session.execute(select(Book)).scalars().all()
            for book in books:
                if book.file_name and not os.path.exists(book.file_name):
                    cover_path = covers_dir / f"{book.id}.jpg"
                    if cover_path.exists():
                        cover_path.unlink(missing_ok=True)
                    session.delete(book)
                    deleted_count += 1
            session.commit()
        self.config.logger.info(f"[Storage] Registros huérfanos eliminados: {deleted_count}")

    def insert_book(self, book):
        """Insert a new book into the database saving the cover to disk."""
        with Session(self.engine) as session:
            try:
                cover_path_relative = None
                raw_cover = book[2]

                if raw_cover:
                    try:
                        cover_bytes = raw_cover.data if hasattr(raw_cover, 'data') else raw_cover
                    except Exception:
                        cover_bytes = raw_cover

                    if cover_bytes and isinstance(cover_bytes, bytes):
                        cover_filename = f"{hashlib.md5(cover_bytes).hexdigest()[:12]}.jpg"
                        covers_dir = Path(self.config.root) / "src" / "frontend" / "static" / "covers"
                        covers_dir.mkdir(parents=True, exist_ok=True)
                        full_cover_path = covers_dir / cover_filename

                        if not full_cover_path.exists():
                            with open(full_cover_path, "wb") as f:
                                f.write(cover_bytes)

                        cover_path_relative = f"covers/{cover_filename}"

                _book = Book(
                    title=book[0],
                    author=book[1],
                    cover=cover_path_relative,
                    file_name=book[3],
                    description=book[4],
                    identifier=book[5],
                    publisher=book[6],
                    rights=book[8],
                    tags=book[9],
                )
                session.add(_book)
                session.commit()
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
                # Si 'collection' es un número (ID), filtra por ID. Si es texto, filtra por Nombre.
                if isinstance(collection, int) or str(collection).isdigit():
                    stmt = (
                        select(Book)
                        .join(BookCollection)
                        .where(BookCollection.collection_id == int(collection))
                    )
                else:
                    stmt = (
                        select(Book)
                        .join(BookCollection)
                        .join(Collection, BookCollection.collection_id == Collection.id)
                        .where(Collection.name == collection)
                    )
                
                result = session.execute(
                    stmt.offset(skip or 0).limit(limit)
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
