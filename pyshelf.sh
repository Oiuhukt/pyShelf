#!/usr/bin/env bash

if [ -f "/etc/pyShelf/release/pyshelf" ]; then
    cd /etc/pyShelf
    export PYSHELF_ASSETS=/etc/pyShelf/src/frontend
    exec /usr/local/bin/python3.12 src/__main__.py
else
    cd /home/oiuhukt/gitclones/pyShelf
    export PYSHELF_ASSETS=/home/oiuhukt/gitclones/pyShelf/src/frontend
    exec /usr/local/bin/python3.12 src/__main__.py
fi
