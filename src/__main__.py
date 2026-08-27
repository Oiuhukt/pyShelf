"""pyShelf main entry point."""
import asyncio
import os
import threading
from contextlib import asynccontextmanager
from backend.lib.config import Config
from backend.lib.storage import Storage
from frontend.lib.FastAPIServer import FastAPIServer, app


def run_background_sync(config: Config):
    """Ejecuta el escaneo y la limpieza en segundo plano para no bloquear el inicio."""
    config.logger.info("Iniciando escaneo de biblioteca en segundo plano...")
    storage = Storage(config)
    storage.auto_discover_books()
    storage.clean_orphaned_books()
    storage.make_collections()
    config.logger.info("Escaneo en segundo plano completado.")


@asynccontextmanager
async def lifespan(app_instance):
    """Gestor de ciclo de vida moderno para FastAPI (reemplaza a @app.on_event)."""
    config = Config(os.path.abspath(os.getcwd()))
    # Iniciar la sincronización en un hilo secundario
    threading.Thread(target=run_background_sync, args=(config,), daemon=True).start()
    yield


# Asignar el gestor lifespan a la instancia de FastAPI
app.router.lifespan_context = lifespan


async def main():
    config = Config(os.path.abspath(os.getcwd()))
    config.logger.info("Inicializando pyShelf...")
    
    server = FastAPIServer(config)
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nServidor detenido por el usuario.")
