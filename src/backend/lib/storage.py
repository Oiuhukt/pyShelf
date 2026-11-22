"""Pyshelf's Main Storage Class."""

import re
import os
import glob
import datetime
import subprocess
import unicodedata
from PIL import Image
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import Book, Collection, BookCollection


# --- Utilidades de normalización (módulo) ---

_EXT_RE = re.compile(r"\.(pdf|epub|mobi|azw3|djvu|fb2|cbz|cbr)$", re.IGNORECASE)
_JUNK_TITLE_RE = re.compile(
    r"^(microsoft word|untitled|document\d*|unknown|sin t[ií]tulo|\d+)\b",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    """minúsculas, sin acentos, sin espacios múltiples."""
    return re.sub(r"\s+", " ", _strip_accents(text or "").lower()).strip()


def clean_title_from_filename(path_or_name: str) -> str:
    """El_Quijote_-_Cervantes.pdf -> 'El Quijote - Cervantes'."""
    name = os.path.basename(path_or_name or "")
    name = _EXT_RE.sub("", name)
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    # quitar corchetes/paréntesis finales tipo "[PDF]" o "(1)"
    name = re.sub(r"\s*[\[\(][^\]\)]{1,20}[\]\)]\s*$", "", name).strip()
    if name and (name.islower() or name.isupper()):
        name = name.title()
    return name or "Sin título"


def is_junk_title(title: str) -> bool:
    if not title or not title.strip():
        return True
    t = title.strip()
    if _EXT_RE.search(t):
        return True
    if t.isdigit():
        return True
    if _JUNK_TITLE_RE.match(t):
        return True
    return False


class Storage:
    """Create a new Storage object."""

    def __init__(self, config):
        self.config = config
        from sqlalchemy.pool import NullPool
        self.engine = create_engine(
            self.get_connection_string(),
            pool_pre_ping=True,
            poolclass=NullPool,
            connect_args={"check_same_thread": False, "timeout": 30},
        ) 

    def get_connection_string(self):
        return f"sqlite:////{self.config.root}/pyshelf.sqlite3"

    def create_tables(self):
        tables = [Book, Collection]
        for table in tables:
            table.metadata.create_all(self.engine)

    # ---------- Metadatos ----------

    def extract_pdf_metadata(self, pdf_path: str) -> tuple[str, str]:
        """Extrae Título/Autor con pdfinfo. Fallback: nombre limpio del archivo."""
        title = None
        author = None

        if pdf_path.lower().endswith((".pdf",)):
            try:
                res = subprocess.run(
                    ["pdfinfo", pdf_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, timeout=5,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if line.startswith("Title:"):
                            val = line.split("Title:", 1)[1].strip()
                            if val and not is_junk_title(val):
                                title = val
                        elif line.startswith("Author:"):
                            val = line.split("Author:", 1)[1].strip()
                            if val and not is_junk_title(val):
                                author = val
            except Exception as e:
                self.config.logger.error(
                    f"[Storage] pdfinfo falló en {pdf_path}: {e}"
                )

        if not title:
            title = clean_title_from_filename(pdf_path)
        if not author:
            author = "Sin datos"

        return title, author

    # ---------- Portadas ----------

    def generate_pdf_cover(self, pdf_path: str, book_id, force: bool = False):
        covers_dir = Path(self.config.root) / "src" / "frontend" / "static" / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)

        output_prefix = str(covers_dir / str(book_id))
        final_jpg = covers_dir / f"{book_id}.jpg"
        relative_cover_path = f"covers/{book_id}.jpg"

        if final_jpg.exists() and not force:
            return relative_cover_path

        if pdf_path.lower().endswith(".pdf"):
            try:
                cmd = [
                    "pdftoppm", "-jpeg", "-f", "1", "-l", "1",
                    "-singlefile", "-scale-to", "800",
                    pdf_path, output_prefix,
                ]
                subprocess.run(
                    cmd, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                )
            except Exception as e:
                self.config.logger.error(
                    f"[Storage] Error extrayendo portada ID {book_id}: {e}"
                )

        if final_jpg.exists():
            try:
                with Image.open(final_jpg) as img:
                    width, height = img.size
                    if width > height:
                        img.crop((width / 2, 0, width, height)).save(
                            final_jpg, "JPEG", quality=90
                        )
            except Exception as e:
                self.config.logger.error(
                    f"[Storage] Error recortando portada ID {book_id}: {e}"
                )

        return relative_cover_path if final_jpg.exists() else None

    # ---------- Descubrimiento / sincronización ----------

    def auto_discover_books(self):
        search_path = getattr(self.config, "book_path", "/usr/local/biblioteca")
        files = sorted(
            glob.glob(f"{search_path}/**/*.pdf", recursive=True)
            + glob.glob(f"{search_path}/**/*.epub", recursive=True)
        )
        now = datetime.datetime.now()
        new_count = 0
        fixed_count = 0

        with Session(self.engine) as session:
            for path in files:
                existing = session.execute(
                    select(Book).where(Book.file_name == path)
                ).scalar_one_or_none()

                parent_dir = os.path.basename(os.path.dirname(path))
                category = parent_dir if parent_dir.lower() != "biblioteca" else "General"

                title, author = self.extract_pdf_metadata(path)

                if existing:
                    existing.categories = category

                    # Corregir título si es basura / nombre de archivo
                    raw_basename = os.path.basename(path)
                    needs_title_fix = (
                        not existing.title
                        or existing.title == raw_basename
                        or is_junk_title(existing.title)
                    )
                    if needs_title_fix and title and title != existing.title:
                        existing.title = title
                        fixed_count += 1

                    if (not existing.author or existing.author == "Sin datos") and author:
                        existing.author = author

                    if not existing.cover or not (
                        Path(self.config.root) / "src" / "frontend" / "static" / existing.cover
                    ).exists():
                        cover_rel_path = self.generate_pdf_cover(path, existing.id)
                        if cover_rel_path:
                            existing.cover = cover_rel_path
                else:
                    new_book = Book(
                        title=title, author=author, file_name=path,
                        cover="", date=now, categories=category,
                    )
                    session.add(new_book)
                    session.flush()
                    cover_rel_path = self.generate_pdf_cover(path, new_book.id)
                    if cover_rel_path:
                        new_book.cover = cover_rel_path
                    new_count += 1
            session.commit()

        self.config.logger.info(
            f"[Storage] Libros sincronizados: {new_count} nuevos, "
            f"{fixed_count} títulos corregidos."
        )

    def clean_orphaned_books(self):
        covers_dir = Path(self.config.root) / "src" / "frontend" / "static" / "covers"
        deleted_count = 0

        with Session(self.engine) as session:
            for book in session.execute(select(Book)).scalars().all():
                if book.file_name and not os.path.exists(book.file_name):
                    cover_path = covers_dir / f"{book.id}.jpg"
                    if cover_path.exists():
                        cover_path.unlink(missing_ok=True)
                    session.delete(book)
                    deleted_count += 1
            session.commit()
        self.config.logger.info(f"[Storage] Huérfanos eliminados: {deleted_count}")

    # ---------- Colecciones ----------

    def make_collections(self):
        self.config.logger.info("Making collections.")
        with Session(self.engine) as session:
            for book_id, file_name in session.execute(
                select(Book.id, Book.file_name)
            ).all():
                try:
                    relative_parts = Path(file_name).relative_to(self.config.book_path).parts
                except ValueError:
                    continue
                folder = "Unsorted" if len(relative_parts) < 2 else relative_parts[0]

                collection = session.execute(
                    select(Collection).where(Collection.name == folder)
                ).scalar_one_or_none()
                if not collection:
                    collection = Collection(name=folder)
                    session.add(collection)
                    session.flush()

                exists = session.execute(
                    select(BookCollection).where(
                        BookCollection.book_id == book_id,
                        BookCollection.collection_id == collection.id,
                    )
                ).first()
                if not exists:
                    session.add(BookCollection(book_id=book_id, collection_id=collection.id))
            session.commit()
        self.config.logger.info("Finished making collections.")

    def get_books(self, collection=None, skip=None, limit=None):
        with Session(self.engine) as session:
            if collection is not None:
                if isinstance(collection, int) or str(collection).isdigit():
                    stmt = (
                        select(Book).join(BookCollection)
                        .where(BookCollection.collection_id == int(collection))
                    )
                else:
                    stmt = (
                        select(Book)
                        .join(BookCollection)
                        .join(Collection, BookCollection.collection_id == Collection.id)
                        .where(Collection.name == collection)
                    )
                result = session.execute(stmt.offset(skip or 0).limit(limit)).scalars().all()
            else:
                result = session.execute(
                    select(Book).offset(skip or 0).limit(limit)
                ).scalars().all()
        return result

    def get_book(self, id):
        with Session(self.engine) as session:
            return session.execute(select(Book).where(Book.id == id)).first()

    def get_collections(self):
        with Session(self.engine) as session:
            return session.execute(
                select(Collection).join(BookCollection).distinct()
            ).scalars().all()

    def get_collection(self, name):
        with Session(self.engine) as session:
            return session.execute(
                select(Collection).where(Collection.name == name).join(Book)
            ).all()

    # ---------- Búsqueda (reescrita) ----------

    def search_books_by_text(self, query: str, limit: int = 200):
        """
        Búsqueda FTS5 con prefijo por término, ranking BM25 y orden estable.
        Mantiene el comportamiento AND (todos los términos deben aparecer).
        """
        if not query or not query.strip():
            return []

        terms = re.findall(r"\w+", query, flags=re.UNICODE)
        if not terms:
            return []
        fts_query = " ".join(f"{t}*" for t in terms)

        from sqlalchemy import text as _sqltext

        with Session(self.engine) as session:
            try:
                id_rows = session.execute(
                    _sqltext(
                        "SELECT b.id FROM Book_fts "
                        "JOIN Book b ON b.id = Book_fts.rowid "
                        "WHERE Book_fts MATCH :q "
                        "ORDER BY bm25(Book_fts, 10.0, 5.0, 2.0, 3.0, 1.0, 2.0, 0.5) "
                        "LIMIT :lim"
                    ),
                    {"q": fts_query, "lim": limit},
                ).all()
            except Exception as e:
                self.config.logger.error(
                    f"[Storage] FTS5 search error: {e!r} (q={fts_query!r})"
                )
                return []
            ids = [r[0] for r in id_rows]
            if not ids:
                return []
            books = session.execute(
                select(Book).where(Book.id.in_(ids))
            ).scalars().all()
            order = {bid: i for i, bid in enumerate(ids)}
            books.sort(key=lambda b: order[b.id])
            return books

    # ---------- Migración de títulos ----------

    def cleanup_titles(self, dry_run: bool = True):
        """Corrige títulos basura o que quedaron como nombre de archivo."""
        changes = []
        with Session(self.engine) as session:
            for book in session.execute(select(Book)).scalars().all():
                raw_base = os.path.basename(book.file_name or "")
                needs_fix = (
                    not book.title
                    or book.title == raw_base
                    or is_junk_title(book.title)
                )
                if not needs_fix:
                    continue
                new_title = clean_title_from_filename(raw_base)
                if new_title and new_title != book.title:
                    changes.append({
                        "id": book.id,
                        "old": book.title,
                        "new": new_title,
                        "file_name": book.file_name,
                    })
                    if not dry_run:
                        book.title = new_title
            if not dry_run:
                session.commit()
        return changes
