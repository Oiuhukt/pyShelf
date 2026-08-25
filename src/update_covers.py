import os
import sqlite3
from pathlib import Path
from pdf2image import convert_from_path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "pyshelf.sqlite3"
COVERS_DIR = BASE_DIR / "src" / "frontend" / "static" / "covers"

os.makedirs(COVERS_DIR, exist_ok=True)

def generate_and_update_covers():
    if not DB_PATH.exists():
        print(f"Error: No se encontró la base de datos en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, file_name FROM Book ORDER BY id ASC;")
    books = cursor.fetchall()

    updated = 0
    errors = 0

    print(f"Procesando {len(books)} libros...")

    for book_id, file_path in books:
        if not file_path or not os.path.exists(file_path):
            print(f"[{book_id}] Archivo no encontrado: {file_path}")
            errors += 1
            continue

        jpg_filename = f"{book_id:03d}.jpg"
        jpg_path = COVERS_DIR / jpg_filename

        try:
            # Si el JPG no existe en disco, se extrae la primera página del PDF usando poppler
            if not jpg_path.exists() and file_path.lower().endswith(".pdf"):
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if images:
                    images[0].save(jpg_path, "JPEG")

            # Inyectar el JPG en la columna BLOB de SQLite
            if jpg_path.exists():
                with open(jpg_path, "rb") as f:
                    blob_data = f.read()

                cursor.execute(
                    "UPDATE Book SET cover = ? WHERE id = ?;",
                    (sqlite3.Binary(blob_data), book_id)
                )
                updated += 1
            else:
                errors += 1

        except Exception as e:
            print(f"[{book_id}] Error procesando {file_path}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print("\n--- Extracción e Inyección Finalizada ---")
    print(f"Portadas vinculadas en BD: {updated}")
    print(f"Errores / Omitidos:         {errors}")

if __name__ == "__main__":
    generate_and_update_covers()
