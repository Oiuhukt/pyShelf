# pyShelf v1.1.1

Servidor de biblioteca digital ligero y elegante construido con **FastAPI**, **Jinja2** y **PicoCSS 2**.

## 🚀 Novedades en v1.1.1
- **Frontend Estable**: Interfaz homogeneizada con componentes de PicoCSS 2 y visualización responsive de tarjetas de libros.
- **Tema Desierto Académico**: Nueva paleta global de 8 colores basada en tonos arcilla, arena y ocre.
- **Destacado y Filtros**: Sección principal con selección aleatoria de documentos y filtrado rápido por categoría (*Todos*, *Libros*, *Artículos*).
- **Backend Optimizado**: API adaptada a FastAPI/Starlette con manejo eficiente de headers e integración fluida con SQLite.

## 🛠️ Instalación y Uso

1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/TU_USUARIO/pyShelf.git](https://github.com/TU_USUARIO/pyShelf.git)
   cd pyShelf

    Iniciar el servidor:
    Bash

    ./pyshelf.sh


---

### **4. Guardar cambios y crear el Release en GitHub**

Ejecuta esta secuencia de comandos en tu terminal para registrar los cambios, poner la etiqueta de versión y subir todo a GitHub:

```bash
# 1. Ver qué archivos se van a incluir
git status

# 2. Agregar todos los cambios respetando el .gitignore
git add .

# 3. Guardar el commit con la descripción de la versión
git commit -m "release: v1.1.1 - Frontend PicoCSS desértico y backend estable"

# 4. Crear la etiqueta Git (Tag) de la versión
git tag -a v1.1.1 -m "Versión 1.1.1 - Primera versión pública estable"

# 5. Subir código y etiquetas al repositorio remoto
git push origin main
git push origin v1.1.1
