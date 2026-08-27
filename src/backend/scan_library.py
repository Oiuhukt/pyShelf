#!/usr/bin/env python3
"""CLI script para escanear, sincronizar y limpiar la biblioteca pyShelf."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.lib.config import Config
from backend.lib.storage import Storage


def main():
    print("\n" + "=" * 60)
    print("[pyShelf] Iniciando gestor de biblioteca...")
    print("=" * 60)

    config = Config(os.path.abspath(os.getcwd()))
    storage = Storage(config)

    # 1. Asegurar tablas
    storage.create_tables()

    # 2. Limpieza opcional de huérfanos
    if "--clean" in sys.argv:
        print("[pyShelf] Ejecutando depuración de registros huérfanos...")
        storage.clean_orphaned_books()

    # 3. Descubrir libros (esto ya genera las portadas de los archivos nuevos)
    print("[pyShelf] Sincronizando archivos con la base de datos...")
    storage.auto_discover_books()

    # 4. Solo regenerar si se pide explícitamente sin descubrir de cero
    if "--force-covers" in sys.argv:
        print("[pyShelf] Forzando regeneración manual de portadas...")
        storage.regenerate_all_covers(force=True)

    # 5. Organizar colecciones
    print("[pyShelf] Actualizando colecciones...")
    storage.make_collections()

    print("\n" + "=" * 60)
    print("[pyShelf] Proceso completado con éxito.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
