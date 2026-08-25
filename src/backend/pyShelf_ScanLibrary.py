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

    # Si se pide forzar o el archivo existente está vacío (0 bytes), borrarlo
    if output_cover_path.exists():
        if force or output_cover_path.stat().st_size == 0:
            output_cover_path.unlink(missing_ok=True)
        else:
            return True  # Ya existe una portada válida

    try:
        # Intentar extraer la primera página con poppler
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=1,
            dpi=150,
            strict=False  # Tolera algunos errores menores en la estructura del PDF
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

    # Si pasas force=True, re-procesará TODOS los PDFs aunque ya tengan imagen
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
            # Obtener datos del libro
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

            # Verificar si es PDF
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

    # --- RESUMEN Y REPORTE DE ERRORES ---
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


if __name__ == "__main__":
    # Permite correrlo manualmente desde consola pasándole --force si quieres rehacer todas
    force = "--force" in sys.argv
    execute_scan(force=force)
