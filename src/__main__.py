#!/usr/bin/env python3
"""PyShelf Entrypoint."""
import asyncio
import sys
from pathlib import Path
from threading import Thread
from backend.lib.config import Config
from backend.lib.storage import Storage
from backend.pyShelf_ScanLibrary import execute_scan
from frontend.lib.FastAPIServer import FastAPIServer
# import websockets


root = Path.cwd()
config = Config(root)
PRG_PATH = Path.cwd().__str__()
sys.path.insert(0, PRG_PATH)


def run_import():
    """Begin live import of books."""
    config.logger.info("Begining book import.")
    execute_scan(PRG_PATH, config=config)
    config.logger.info("Finished book import.")
    storage = Storage(config=config)
    # MakeCollections(PRG_PATH, config=config)
    storage.make_collections()
    return "Import Complete"


async def main():
    """Program entrypoint."""
    Storage(config=config).create_tables()
    
    # 1. Ejecutar la importación y generación de portadas de forma directa y bloqueante
    run_import()
    
    # 2. Una vez terminado todo el escaneo y colecciones, iniciar el servidor FastAPI
    fe_server = FastAPIServer(config)
    _task = await asyncio.create_task(fe_server.run())
    return [_task]

if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
