import os
import sqlite3

DB_PATH = "pyshelf.sqlite3"
BIBLIOTECA_PATH = "/usr/local/biblioteca"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

insertados = 0

# Recorre la raíz y subcarpetas como 'Artículos'
for root, dirs, files in os.walk(BIBLIOTECA_PATH):
    for file in files:
        if file.lower().endswith(('.pdf', '.epub')):
            full_path = os.path.join(root, file)
            title = os.path.splitext(file)[0]
            
            try:
                # Usa file_name y title que son los campos NOT NULL requeridos
                cursor.execute(
                    "INSERT INTO Book (title, file_name) VALUES (?, ?);",
                    (title, full_path)
                )
                insertados += 1
            except sqlite3.IntegrityError:
                pass  # Ignora si el archivo ya existe en la base de datos

conn.commit()
conn.close()

print(f"¡Éxito! Se inyectaron {insertados} libros a la Base de Datos.")
