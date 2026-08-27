"""pyShelf's main frontend library."""
import uvicorn
import os
import sass
import datetime
import math
import random
from pathlib import Path
from json import dumps
from base64 import b64encode
from urllib.parse import unquote
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from backend.lib.storage import Storage
from .objects import JSInterface
from .runtime_paths import ensure_assets
from backend.lib.config import Config

# Instancias ÚNICAS compartidas para todo el ciclo de vida de la aplicación
config = Config(os.path.abspath(os.getcwd()))
storage = Storage(config)

app = FastAPI()
STATIC_DIR, TEMPLATES_DIR = ensure_assets()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

origins = [
    "http://localhost",
    "http://localhost:8081",
    "http://localhost:8080",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def base64decode(string) -> str:
    """Decode a base64 string."""
    try:
        result = b64encode(string).decode("utf-8")
    except Exception:
        result = "None"
    return result


def summarize(string) -> str:
    """Summarize a string."""
    try:
        if len(string) > 50:
            return string[:50] + "..."
        return string
    except TypeError:
        return "None"


def convertDateTime(timestamp: datetime) -> str:
    """Convert a datetime object to a string."""
    if not timestamp:
        return ""
    return timestamp.strftime("%d/%m/%Y %H:%M:%S")


def books_tojson(obj) -> list:
    """Convert an object to a list of dicts."""
    _books: list = []
    if not obj:
        return _books
    for book in obj:
        convert_none = lambda x: x if x is not None else "None"
        _books.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "categories": convert_none(getattr(book, 'categories', None)),
            "cover": base64decode(book.cover),
            "pages": convert_none(book.pages),
            "progress": convert_none(book.progress),
            "file_name": book.file_name,
            "description": convert_none(book.description),
            "sample_text": convert_none(getattr(book, 'sample_text', None)),
            "date": convertDateTime(book.date),
            "rights": convert_none(book.rights),
            "tags": convert_none(book.tags),
            "identifier": convert_none(book.identifier),
            "publisher": convert_none(book.publisher),
        })
    return _books


def book_tojson(book) -> dict:
    """Convert a book object to a dict."""
    if not book:
        return {}
    return {
        "book_id": book.id,
        "title": book.title,
        "author": book.author,
        "categories": getattr(book, 'categories', None),
        "cover": base64decode(book.cover),
        "pages": book.pages,
        "progress": book.progress,
        "file_name": book.file_name,
        "description": book.description,
        "sample_text": getattr(book, 'sample_text', None),
        "date": convertDateTime(book.date),
        "rights": book.rights,
        "tags": book.tags,
        "identifier": book.identifier,
        "publisher": book.publisher,
    }


def tojson(obj) -> dumps:
    return dumps(obj)

# CÓDIGO NUEVO:
def collections_to_dict(collection_list) -> list:
    """Convert a collections object to a clean Python list of dicts."""
    _collections = []
    _collection_id_set = set()
    for _collection in collection_list:
        c_id = getattr(_collection, 'id', None)
        c_name = getattr(_collection, 'name', None) or str(_collection)
        
        if c_id not in _collection_id_set:
            if c_id is not None:
                _collection_id_set.add(c_id)
            _collections.append({
                "collection_id": c_id,
                "collection": c_name,
            })
    return _collections

templates.env.filters["b64decode"] = base64decode
templates.env.filters["summarize"] = summarize
templates.env.filters["books_tojson"] = books_tojson
templates.env.filters["collections_tojson"] = collections_to_dict
templates.env.filters["tojson"] = tojson



@app.get("/", response_class=HTMLResponse)
async def index(request: Request, skip: int = 0, limit: int = 10, filter: str = "all"):
    # 1. Definir la colección a consultar
    collection_filter = None
    if filter == "books":
        collection_filter = "Libros"
    elif filter == "articles":
        collection_filter = "Artículos"

    # 2. Obtener todos los libros filtrados para calcular el total
    all_filtered_books = storage.get_books(collection=collection_filter) or []
    total_books = len(all_filtered_books)
    
    # 3. Aplicar paginación manual en Python
    books = all_filtered_books[skip : skip + limit]
    total_pages = (total_books + limit - 1) // limit if limit > 0 else 1

    # 4. Seleccionar un libro aleatorio de toda la biblioteca
    all_books = storage.get_books() or []
    featured_book = random.choice(all_books) if all_books else None

    return templates.TemplateResponse(
            request=request,
        name="index.html",
        context={
            "books": books,
            "featured_book": featured_book,
            "page": skip,
            "limit": limit,
            "total_pages": total_pages,
            "current_filter": filter
        }
    )
# AHORA:
@app.get("/api/books")
async def books(request: Request, skip: int = 0, limit: int = 10, collection=None):
    books = storage.get_books(collection, skip=skip, limit=limit)
    return JSONResponse(content=books_tojson(books))  # Al ser books_tojson una lista de Python, ya no rompe Content-Length

@app.get("/api/cover/{book_id}")
async def get_cover(book_id: int):
    # 1. Prioridad: Buscar la portada directa por ID ({book_id}.jpg)
    cover_by_id = os.path.join(STATIC_DIR, "covers", f"{book_id}.jpg")
    if os.path.exists(cover_by_id):
        return FileResponse(cover_by_id, media_type="image/jpeg")

    # 2. Si no existe por ID, intentar extraer la propiedad 'cover' del objeto en la BD
    book = storage.get_book(book_id)
    if book:
        # Desestructurar la fila Row de SQLAlchemy si es necesario
        book_obj = book[0] if (hasattr(book, "__getitem__") and len(book) > 0) else book
        
        cover_attr = None
        if isinstance(book_obj, dict):
            cover_attr = book_obj.get("cover")
        else:
            cover_attr = getattr(book_obj, "cover", None)

        if cover_attr:
            cover_val = str(cover_attr).lstrip("/")
            cover_by_attr = os.path.join(STATIC_DIR, cover_val)
            if os.path.exists(cover_by_attr):
                return FileResponse(cover_by_attr)

    # 3. Fallback a la portada genérica de "no cover"
    fallback_path = os.path.join(STATIC_DIR, "images", "no-cover.jpg")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path)

    return JSONResponse(status_code=404, content={"error": "Cover not found"})

@app.get("/api/get_book/{book_id}")
async def get_book(book_id: int):
    book = storage.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado en la base de datos.")

    # Si es una fila Row de SQLAlchemy o una tupla/lista, desempaquetar el primer elemento
    if hasattr(book, "__getitem__") and len(book) > 0:
        book_obj = book[0]
    else:
        book_obj = book

    # Obtener el atributo 'file_name' directamente del objeto Book o diccionario
    file_path = None
    if isinstance(book_obj, dict):
        file_path = book_obj.get("file_name") or book_obj.get("file_path")
    else:
        file_path = getattr(book_obj, "file_name", None) or getattr(book_obj, "file_path", None)

    # Limpiar saltos de línea y retornos de carro residuales
    if file_path:
        file_path = str(file_path).replace("\n", "").replace("\r", "").strip()

    if not file_path or file_path == "None" or not os.path.exists(file_path):
        print(f"[ERROR GET_BOOK] ID {book_id} -> Objeto: {book_obj} | Ruta calculada: '{file_path}'")
        return JSONResponse(
            status_code=404,
            content={"error": f"Archivo no encontrado en disco: {file_path}"}
        )

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    media_type = "application/pdf" if ext == ".pdf" else "application/epub+zip"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        content_disposition_type="inline"
    )

@app.post("/api/admin/rescan")
async def rescan_library(background_tasks: BackgroundTasks):
    """Dispara la sincronización y limpieza de la biblioteca en segundo plano."""
    def run_scan_and_sync():
        storage.auto_discover_books()
        storage.clean_orphaned_books()
        storage.make_collections()

    background_tasks.add_task(run_scan_and_sync)
    return {"status": "success", "message": "Escaneo de biblioteca iniciado en segundo plano."}


@app.get("/api/collections")
async def collections(request: Request):
    collections = storage.get_collections()
    # Pasa el objeto limpio de Python para que FastAPI arme el JSON correctamente
    data = [{"collection_id": c.id, "collection": c.name} for c in collections]
    return JSONResponse(content=data)

@app.get("/collection/{collection}", response_class=HTMLResponse)
@app.get("/api/collection/{collection}", response_class=HTMLResponse)
async def collection(request: Request, collection: str, skip: int = 0, limit: int = 30):
    skip_num = 0 if skip <= 0 else skip * limit
    decoded_collection = unquote(collection)

    # La base de datos ahora busca directamente por el texto del nombre
    books = storage.get_books(decoded_collection, skip=skip_num, limit=limit)
    total_books = len(storage.get_books(decoded_collection))
    collections = storage.get_collections()

    context = {
        "request": request,
        "books": books,
        "collections": collections,
        "collection": decoded_collection,
        "collection_id": collection,
        "total_pages": math.ceil(total_books / limit) if limit > 0 else 1,
        "page": skip,
        "limit": limit
    }
    return templates.TemplateResponse(request=request, name="collection.html", context=context)

@app.get("/api/search", response_class=HTMLResponse)
async def search_books_api(request: Request, search: str):
    books = storage.fuzzy_search_books(search)
    total_books = len(books)
    collections = storage.get_collections()
    context = {
        "request": request,
        "books": books,
        "collections": collections,
        "total_pages": 1,
        "total_books": total_books,
    }
    return templates.TemplateResponse(request=request, name="search.html", context=context)


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/static/images/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(STATIC_DIR, "images", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    # 204 No Content debe devolver una respuesta vacía sin cuerpo (Response())
    return Response(status_code=204)

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    collections = storage.get_collections()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "books": [],
        "collections": collections,
        "total_pages": 1,
        "page": 0,
        "limit": 30,
        "open_about": True
    })


class FastAPIServer():
    """Entry point for FastAPI server."""

    def __init__(self, config):
        """Initialize FastAPIServer object parameters."""
        self.config = config
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        self.fe_config = uvicorn.Config(app, host="0.0.0.0", port=8085,
                                        log_level="info", reload=True)
        self.fe_server = uvicorn.Server(self.fe_config)
        self.JSInterface: JSInterface = JSInterface(self.config)
        self.compile_static_files()

    def compile_static_files(self):
        """Compila los estilos SASS del frontend a CSS."""
        try:
            compiled_css = sass.compile(
                filename=f"{STATIC_DIR}/styles/pyShelf.sass",
                output_style='compressed'
            )
            with open(f"{STATIC_DIR}/styles/pyShelf.css", 'w', encoding='utf-8') as f:
                f.write(compiled_css)
            return True
        except Exception as e:
            print(f"Error al compilar SASS: {e}")
            return False

    def use_route_names_as_operation_ids(self, app: FastAPI) -> None:
        """Use route name as operation id."""
        for route in app.routes:
            if isinstance(route, APIRoute):
                route.operation_id = route.name

    async def run(self):
        """Front end server entrypoint."""
        self.config.logger.info("Starting FastAPI server.")
        self.use_route_names_as_operation_ids(app)
        await self.fe_server.serve()
