#!/usr/bin/env bash
# Configuración usando Python nativo de FreeBSD

if [ -f "/etc/pyShelf/release/pyshelf" ]; then
    cd /etc/pyShelf
    export PYSHELF_ASSETS=/etc/pyShelf/src/frontend
    
    # Ejecuta directamente con el python3 instalado en el sistema
    exec /usr/local/bin/python3 /etc/pyShelf/src/__main__.py
else
    # Fallback si lo estás corriendo desde tu home
    cd /home/oiuhukt/gitclones/pyShelf
    export PYSHELF_ASSETS=/home/oiuhukt/gitclones/pyShelf/src/frontend
    exec /usr/local/bin/python3 src/__main__.py
fi
