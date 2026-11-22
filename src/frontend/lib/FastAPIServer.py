"""pyShelf's main frontend library."""
import os
import math
import random
import datetime
from datetime import date
from typing import Optional
from pathlib import Path
from json import dumps
from urllib.parse import unquote

import uvicorn
import anyio
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from backend.lib.storage import Storage
from backend.lib.config import Config
from .objects import JSInterface
from .runtime_paths import ensure_assets

# Instancias compartidas del servidor
config = Config(os.path.abspath(os.getcwd()))
storage = Storage(config)

app = FastAPI()
STATIC_DIR, TEMPLATES_DIR = ensure_assets()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Montaje de archivos estáticos a nivel de aplicación
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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

# --- FUNCIONES AUXILIARES ---

def base64decode(string) -> str:
    """Devuelve la ruta limpia de la portada o la imagen genérica por defecto."""
    if not string or string == "None":
        return "images/no-cover.jpg"
    return str(string).lstrip("/")

def summarize(string) -> str:
    """Acorta una cadena de texto a 50 caracteres."""
    try:
        if string and len(string) > 50:
            return string[:50] + "..."
        return string or ""
    except TypeError:
        return "None"

def convertDateTime(timestamp: datetime.datetime) -> str:
    """Convierte un objeto datetime a string legible."""
    if not timestamp:
        return ""
    return timestamp.strftime("%d/%m/%Y %H:%M:%S")

def books_tojson(obj) -> list:
    """Convierte una lista de objetos Book a diccionarios JSON-serializables."""
    _books: list = []
    if not obj:
        return _books
    for book in obj:
        is_dict = isinstance(book, dict)
        get_val = lambda key: book.get(key) if is_dict else getattr(book, key, None)
        convert_none = lambda x: x if x is not None else "None"

        _books.append({
            "book_id": get_val('id'),
            "title": get_val('title'),
            "author": get_val('author'),
            "categories": convert_none(get_val('categories')),
            "cover": base64decode(get_val('cover')),
            "pages": convert_none(get_val('pages')),
            "progress": convert_none(get_val('progress')),
            "file_name": get_val('file_name'),
            "description": convert_none(get_val('description')),
            "sample_text": convert_none(get_val('sample_text')),
            "date": convertDateTime(get_val('date')),
            "rights": convert_none(get_val('rights')),
            "tags": convert_none(get_val('tags')),
            "identifier": convert_none(get_val('identifier')),
            "publisher": convert_none(get_val('publisher')),
        })
    return _books

def tojson(obj) -> str:
    """Serializa un objeto Python a una cadena JSON limpia."""
    try:
        return dumps(obj)
    except Exception:
        return "[]"

def collections_to_dict(collection_list) -> list:
    """Convierte colecciones a una lista limpia de diccionarios."""
    _collections = []
    _collection_id_set = set()
    for _collection in collection_list:
        c_id = getattr(_collection, 'id', None) if not isinstance(_collection, dict) else _collection.get('id')
        c_name = (getattr(_collection, 'name', None) if not isinstance(_collection, dict) else _collection.get('name')) or str(_collection)
        
        if c_id not in _collection_id_set:
            if c_id is not None:
                _collection_id_set.add(c_id)
            _collections.append({
                "collection_id": c_id,
                "collection": c_name,
            })
    return _collections

# REGISTRO DE FILTROS EN JINJA2
templates.env.filters["b64decode"] = base64decode
templates.env.filters["summarize"] = summarize
templates.env.filters["books_tojson"] = books_tojson
templates.env.filters["collections_tojson"] = collections_to_dict
templates.env.filters["tojson"] = tojson


# --- ENDPOINTS / RUTAS ---


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    filter: str = "all"
):
    page = max(1, page)
    collection_filter = {"books": "Libros", "articles": "Artículos"}.get(filter)

    if q and q.strip():
        all_filtered_books = storage.search_books_by_text(q, limit=500) or []
    else:
        all_filtered_books = storage.get_books(collection=collection_filter) or []

    total_books = len(all_filtered_books)
    total_pages = math.ceil(total_books / limit) if limit > 0 else 1
    page = min(page, total_pages) if total_pages > 0 else 1

    skip = (page - 1) * limit
    paginated_books = all_filtered_books[skip: skip + limit]

    all_books = storage.get_books() or []
    featured_book = random.Random(date.today().isoformat()).choice(all_books) if all_books else None

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request,
            "books": paginated_books,
            "search_query": q,
            "featured_book": featured_book,
            "page": page, "limit": limit,
            "total_pages": total_pages, "total_books": total_books,
            "current_filter": filter,
        },
    )

@app.get("/api/books")
async def books(request: Request, skip: int = 0, limit: int = 10, collection=None):
    books = storage.get_books(collection, skip=skip, limit=limit)
    return JSONResponse(content=books_tojson(books))


@app.get("/api/admin/cleanup_titles/preview")
async def cleanup_titles_preview():
    """Muestra qué títulos cambiarían, sin tocar la BD."""
    changes = storage.cleanup_titles(dry_run=True)
    return {"count": len(changes), "changes": changes}

@app.post("/api/admin/cleanup_titles/apply")
async def cleanup_titles_apply():
    """Aplica la corrección de títulos en la BD."""
    changes = storage.cleanup_titles(dry_run=False)
    return {"status": "ok", "updated": len(changes), "changes": changes}

@app.get("/api/cover/{book_id}")
async def get_cover(book_id: int):
    cover_by_id = os.path.join(STATIC_DIR, "covers", f"{book_id}.jpg")
    
    if os.path.exists(cover_by_id) and os.path.getsize(cover_by_id) > 0:
        return FileResponse(
            path=cover_by_id, 
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    book = storage.get_book(book_id)
    if book:
        book_obj = book[0] if (hasattr(book, "__getitem__") and len(book) > 0) else book
        cover_attr = book_obj.get("cover") if isinstance(book_obj, dict) else getattr(book_obj, "cover", None)

        if cover_attr:
            cover_val = str(cover_attr).lstrip("/")
            cover_by_attr = os.path.join(STATIC_DIR, cover_val)
            if os.path.exists(cover_by_attr) and os.path.getsize(cover_by_attr) > 0:
                return FileResponse(
                    path=cover_by_attr,
                    headers={"Cache-Control": "public, max-age=86400"}
                )

    fallback_path = os.path.join(STATIC_DIR, "images", "no-cover.jpg")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Portada no encontrada")

@app.get("/api/get_book/{book_id}")
async def get_book(book_id: int):
    book = storage.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado en la base de datos.")

    book_obj = book[0] if (hasattr(book, "__getitem__") and len(book) > 0) else book

    file_path = book_obj.get("file_name") or book_obj.get("file_path") if isinstance(book_obj, dict) else (getattr(book_obj, "file_name", None) or getattr(book_obj, "file_path", None))

    if file_path:
        file_path = str(file_path).replace("\n", "").replace("\r", "").strip()

    if not file_path or file_path == "None" or not os.path.exists(file_path):
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
    """Ejecuta el rescaneo en un hilo secundario sin bloquear FastAPI."""
    def run_scan_and_sync():
        storage.auto_discover_books()
        storage.clean_orphaned_books()
        storage.make_collections()

    background_tasks.add_task(anyio.to_thread.run_sync, run_scan_and_sync)
    return {"status": "success", "message": "Escaneo de biblioteca iniciado en segundo plano."}

@app.get("/api/collections")
async def collections(request: Request):
    collections_data = storage.get_collections()
    data = [{"collection_id": c.id, "collection": c.name} for c in collections_data]
    return JSONResponse(content=data)

@app.get("/collection/{collection}", response_class=HTMLResponse)
@app.get("/api/collection/{collection}", response_class=HTMLResponse)
async def collection(request: Request, collection: str, skip: int = 0, limit: int = 30):
    skip_num = 0 if skip <= 0 else skip * limit
    decoded_collection = unquote(collection)

    books = storage.get_books(decoded_collection, skip=skip_num, limit=limit)
    collections_data = storage.get_collections()

    if skip == 0 and len(books) < limit:
        total_books = len(books)
    else:
        total_books = len(storage.get_books(decoded_collection))

    context = {
        "request": request,
        "books": books,
        "collections": collections_data,
        "collection": decoded_collection,
        "collection_id": collection,
        "total_pages": math.ceil(total_books / limit) if limit > 0 else 1,
        "page": skip,
        "limit": limit
    }
    return templates.TemplateResponse(request=request, name="collection.html", context=context)

@app.get("/api/search", response_class=HTMLResponse)
async def search_books_api(
    request: Request, 
    search: str, 
    page: int = 1, 
    limit: int = 12
):
    page = max(1, page)
    books_found = storage.search_books_by_text(search, limit=500) or []
    total_books = len(books_found)

    # Aplicar paginación a los resultados de búsqueda
    total_pages = math.ceil(total_books / limit) if limit > 0 else 1
    if page > total_pages and total_pages > 0:
        page = total_pages

    skip = (page - 1) * limit
    paginated_books = books_found[skip : skip + limit]

    collections_data = storage.get_collections()
    
    context = {
        "request": request,
        "books": paginated_books,
        "collections": collections_data,
        "total_pages": total_pages,
        "total_books": total_books,
        "page": page,
        "limit": limit,
        "search_query": search
    }
    return templates.TemplateResponse(request=request, name="search.html", context=context)




@app.get("/favicon.ico", include_in_schema=False)
@app.get("/static/images/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(STATIC_DIR, "images", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    collections_data = storage.get_collections()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "books": [],
        "collections": collections_data,
        "total_pages": 1,
        "page": 0,
        "limit": 30,
        "open_about": True
    })

# --- CLASE PRINCIPAL DEL SERVIDOR ---
class FastAPIServer:
    """Entry point para el servidor FastAPI."""

    def __init__(self, config: Config):
        self.config = config
        self.fe_config = uvicorn.Config(app, host="127.0.0.1", port=8085, log_level="info", reload=True)
        self.fe_server = uvicorn.Server(self.fe_config)
        self.JSInterface: JSInterface = JSInterface(self.config)

    def use_route_names_as_operation_ids(self, app_inst: FastAPI) -> None:
        """Asigna los nombres de las rutas como operation_id para OpenAPI."""
        for route in app_inst.routes:
            if isinstance(route, APIRoute):
                route.operation_id = route.name

    async def run(self):
        """Inicia el servidor frontend."""
        self.config.logger.info("Starting FastAPI server.")
        self.use_route_names_as_operation_ids(app)
        await self.fe_server.serve()
