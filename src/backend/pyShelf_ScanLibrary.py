import os
import sys
import traceback
from pathlib import Path
from pdf2image import convert_from_path

COVERS_DIR = Path("src/frontend/static/covers")
COVERS_DIR.mkdir(parents=True, exist_ok=True)


def generate_pdf_cover(pdf_path: str, book_id: str, force: bool = False) -> bool:
    """Genera la portada JPG. Devuelve True si se generó/existe correctamente, False si falló."""
    output_cover_path = COVERS_DIR / f"{book_id}.jpg"

    if output_cover_path.exists():
        if force or output_cover_path.stat().st_size == 0:
            output_cover_path.unlink(missing_ok=True)
        else:
            return True

    try:
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=1,
            dpi=150,
            strict=False
        )
        if images:
            images[0].save(output_cover_path, "JPEG", optimize=True, quality=80)
            print(f"  [OK] Portada generada para ID {book_id}")
            return True
        else:
            print(f"  [FALLO] El PDF {pdf_path} no devolvió ninguna página renderizable.")
    except Exception as e:
        print(f"  [ERROR EN PDF] ID {book_id} | Archivo: {pdf_path}")
        print(f"                Causa: {e}")

    return False


def execute_scan(*args, **kwargs):
    """Recorre los libros y reporta errores al finalizar."""
    print("\n" + "="*60)
    print("[pyShelf] Iniciando escaneo secuencial de portadas...")
    print("="*60)

    force_rebuild = kwargs.get('force', False)
    failed_books = []
    success_count = 0
    skipped_count = 0

    try:
        from backend.lib.storage import Storage
        from backend.lib.config import Config

        config = kwargs.get('config') or Config(os.path.abspath(os.getcwd()))
        storage = Storage(config)
        books = storage.get_books()

        print(f"[pyShelf] Total de libros a evaluar: {len(books) if books else 0}\n")

        for book in books:
            if isinstance(book, dict):
                file_path = book.get('file_name') or book.get('path')
                book_id = book.get('id') or book.get('_id')
                title = book.get('title', 'Sin título')
            else:
                file_path = getattr(book, 'file_name', None) or getattr(book, 'path', None)
                book_id = getattr(book, 'id', None)
                title = getattr(book, 'title', 'Sin título')

            if not file_path or not book_id:
                continue

            if str(file_path).lower().endswith('.pdf'):
                if not os.path.exists(file_path):
                    print(f"  [ARCHIVO NO ENCONTRADO] ID {book_id}: {file_path}")
                    failed_books.append((book_id, title, file_path, "Archivo no existe en disco"))
                    continue

                cover_file = COVERS_DIR / f"{book_id}.jpg"
                already_exists = cover_file.exists() and cover_file.stat().st_size > 0

                if already_exists and not force_rebuild:
                    skipped_count += 1
                    continue

                ok = generate_pdf_cover(str(file_path), str(book_id), force=force_rebuild)
                if ok:
                    success_count += 1
                else:
                    failed_books.append((book_id, title, file_path, "Error al convertir con poppler"))

    except Exception as err:
        print(f"[ERROR CRÍTICO] Ocurrió una excepción durante el escaneo: {err}")
        traceback.print_exc()

    print("\n" + "="*60)
    print(f"[pyShelf] Resumen de extracción:")
    print(f"  - Existentes/Omitidos: {skipped_count}")
    print(f"  - Nuevos procesados con éxito: {success_count}")
    print(f"  - Fallidos / Con error: {len(failed_books)}")
    print("="*60)

    if failed_books:
        print("\n[LISTA DE LIBROS CON ERROR EN PORTADA]:")
        for b_id, title, path, reason in failed_books:
            print(f"  - ID: {b_id} | Título: {title}")
            print(f"    Ruta: {path}")
            print(f"    Razón: {reason}\n")
    print("="*60 + "\n")


def clean_orphaned_books():
    """Elimina de la base de datos registros cuyas rutas ya no existen en disco y sus portadas."""
    db_file = os.path.join(os.getcwd(), 'pyshelf.sqlite3')
    if not os.path.exists(db_file):
        return

    import sqlite3
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    cur.execute("SELECT id, file_name FROM Book")
    rows = cur.fetchall()
    
    deleted_count = 0
    for book_id, file_path in rows:
        if file_path and not os.path.exists(file_path):
            cur.execute("DELETE FROM Book WHERE id = ?", (book_id,))
            cover_path = COVERS_DIR / f"{book_id}.jpg"
            if cover_path.exists():
                cover_path.unlink(missing_ok=True)
            deleted_count += 1
            print(f"  [LIMPIEZA] Eliminado libro ID {book_id} -> {file_path}")

    conn.commit()
    conn.close()
    print(f"[pyShelf] Registros huérfanos eliminados: {deleted_count}")

def auto_discover_books():
    """Busca archivos .pdf y .epub en /usr/local/biblioteca y asigna su subcarpeta como Colección."""
    db_file = os.path.join(os.getcwd(), 'pyshelf.sqlite3')
    if not os.path.exists(db_file):
        return

    import sqlite3, glob, datetime
    print("[pyShelf] Buscando nuevos archivos y carpetas en /usr/local/biblioteca/...")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    files = sorted(
        glob.glob('/usr/local/biblioteca/**/*.pdf', recursive=True) + 
        glob.glob('/usr/local/biblioteca/**/*.epub', recursive=True)
    )
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_count = 0

    for path in files:
        title = os.path.splitext(os.path.basename(path))[0]
        
        # Extraer el nombre de la subcarpeta como Categoría/Colección
        parent_dir = os.path.basename(os.path.dirname(path))
        category = parent_dir if parent_dir.lower() != 'biblioteca' else 'General'

        cur.execute('''
            INSERT INTO Book (title, author, file_name, cover, date, categories) 
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_name) DO UPDATE SET categories = excluded.categories
        ''', (title, 'Desconocido', path, '', now_str, category))
        
        if cur.rowcount > 0:
            new_count += 1
            
    conn.commit()
    conn.close()
    print(f"[pyShelf] Registros y colecciones actualizados: {new_count}")


if __name__ == "__main__":
    # 1. Si pasas --clean, purga libros borrados de la biblioteca
    if "--clean" in sys.argv:
        print("[pyShelf] Ejecutando depuración de base de datos...")
        clean_orphaned_books()

    # 2. Descubrir automáticamente nuevos PDFs/EPUBs
    auto_discover_books()

    # 3. Extraer portadas (si usas --force, las rehece todas)
    force = "--force" in sys.argv
    execute_scan(force=force)
