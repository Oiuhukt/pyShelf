# pyShelf 📚

Un servidor de libros electrónicos (*eBook server*) ligero, autónomo y administrable desde la terminal o navegador web, enfocado en un consumo mínimo de recursos y sin dependencia de un servidor gráfico (X11/GUI).

---

## 🌟 Características

- **Almacenamiento eficiente:** Portadas extraídas dinámicamente al sistema de archivos local (`static/covers/`), manteniendo la base de datos SQLite ultraligera (~2 MB).
- **Búsqueda Fuzzy optimizada:** Filtra la biblioteca sólo por nombres de archivos.
- **Escaneo recursivo:** Detecta y organiza tus libros almacenados en carpetas.
- **Organización por colecciones:** Agrupación automática según estructura de directorios y soporte para colecciones.
- **Formatos soportados:** EPUB y MOBI con sistema de descarga integrado.

---

## 🚀 Requisitos e Instalación

### Requisitos previos
- **Python:** 3.10+ (probado en Python 3.12 y FreeBSD / Linux).
- **Herramientas:** `git`, `sqlite3`, `uv` (opcional para gestión de entornos).

### Instalación rápida

1. **Clonar el repositorio:**
   ```bash
   git clone git@github.com:Oiuhukt/pyShelf.git
   cd pyShelfi

   onfigurar el entorno virtual e instalar dependencias:
    Bash

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r pyproject.toml # O usando 'uv sync'

    Configuración inicial:
    Edita el archivo config.json para definir la ruta donde se alojan tus libros:
    JSON

    {
      "library_path": "/ruta/a/tus/libros"
    }

    Poblar la base de datos e indexar libros:
    Bash

    python3 poblador.py

    Iniciar el servidor:
    Bash

    ./pyshelf.sh

📂 Estructura del Proyecto

    src/backend/: Lógica de servidor, API y modelos con SQLAlchemy (models.py, storage.py).

    src/frontend/static/covers/: Directorio donde se almacenan físicamente las imágenes de portada en formato .jpg.

    pyshelf.sqlite3: Base de datos SQLite optimizada con información de libros y relaciones.

    poblador.py: Script encargada del escaneo recursivo e indexación de archivos.

🛠️ Desarrollo y Mantenimiento
Migrar o extraer portadas

Si cuentas con portadas binarias almacenadas internamente en la base de datos, las imágenes se extraen automáticamente a la carpeta estática del frontend para optimizar las consultas y reducir la latencia de respuesta.
Bash

python3 -c "import sqlite3; conn =
sqlite3.connect('pyshelf.sqlite3'); conn.execute('VACUUM;');
conn.close()"
