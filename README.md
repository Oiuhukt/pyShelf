# pyShelf 📚

Un servidor de libros electrónicos (*eBook server*) ligero, autónomo y administrable desde la terminal o navegador web, enfocado en un consumo mínimo de recursos y sin dependencia de un servidor gráfico (X11/GUI).

---

## 🌟 Características

- **Almacenamiento eficiente:** Portadas extraídas dinámicamente al sistema de archivos local (`static/covers/`), manteniendo la base de datos SQLite ultraligera (~2 MB).
- **Auto-descubrimiento y Colecciones:** Detecta de forma recursiva tus libros y asigna automáticamente la subcarpeta como Colección (ej. `Libros`, `Artículos`).
- **Extractor Nactivo con Poppler:** Renderizado directo de la primera página del PDF a imagen HD.
- **Búsqueda Fuzzy optimizada:** Filtra la biblioteca rápidamente por nombres de archivos y títulos.
- **Formatos soportados:** PDF, EPUB y MOBI con sistema de descarga e integración de lectura.

---

## 🚀 Requisitos e Instalación

### Requisitos previos
- **Python:** 3.10+ (probado en Python 3.12, FreeBSD y Linux).
- **Dependencias del sistema:** `poppler-utils` (para extracción de portadas PDF).
- **Herramientas:** `git`, `sqlite3`, `uv` (opcional para gestión de entornos).

### Instalación rápida

1. **Clonar el repositorio:**
   ```bash
   git clone git@github.com:Oiuhukt/pyShelf.git
   cd pyShelf

    Configurar el entorno virtual e instalar dependencias:
    Bash

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r pyproject.toml # O usando 'uv sync'

    Configuración inicial:
    Edita el archivo config.json para definir la ruta donde se alojan tus libros:
    JSON

    {
      "library_path": "/usr/local/biblioteca"
    }

    Poblar la base de datos e indexar libros:
    Bash

    python3 -m src.backend.pyShelf_ScanLibrary

    Iniciar el servidor:
    Bash

    ./pyshelf.sh

📂 Estructura del Proyecto

    src/backend/: Lógica del servidor, modelos y utilidades (pyShelf_ScanLibrary.py, storage.py).

    src/frontend/static/covers/: Almacenamiento físico de imágenes de portada ({book_id}.jpg).

    src/frontend/lib/FastAPIServer.py: Endpoints de la API y servidor principal con FastAPI.

    pyshelf.sqlite3: Base de datos SQLite con metadatos, categorías y rutas de archivos.

🛠️ Administración y Mantenimiento

Toda la gestión de la biblioteca se controla a través del script centralizador de backend pyShelf_ScanLibrary.py:
1. Sincronización habitual (Auto-descubrimiento)

Escanea la biblioteca en busca de nuevos archivos .pdf o .epub, actualiza o asigna la Colección según la subcarpeta contenedora (Libros, Artículos, etc.) y genera las portadas faltantes.
Bash

python3 -m src.backend.pyShelf_ScanLibrary

2. Limpieza de libros eliminados (--clean)

Purga de la base de datos SQLite los registros de libros cuyos archivos fueron borrados o movidos fuera del disco, eliminando también su imagen de portada en static/covers/.
Bash

python3 -m src.backend.pyShelf_ScanLibrary --clean

3. Reconstrucción total de portadas (--force)

Fuerza a Poppler a re-procesar la primera página de cada PDF y sobrescribir todas las imágenes de portada en static/covers/. Ideal si se desalinearon las imágenes.
Bash

python3 -m src.backend.pyShelf_ScanLibrary --force
