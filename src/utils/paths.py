"""Rutas de archivos según el sistema operativo.

Detecta si se ejecuta en Windows (PC) o Android para ubicar la base de datos.
"""

import os
import sys

def get_data_dir() -> str:
    """Retorna la carpeta donde se debe guardar la base de datos."""
    if getattr(sys, "flet_build", False):
        # Android: almacenamiento privado de la app
        return os.path.join(os.path.expanduser("~"), "data")
    # Windows: carpeta data/ del proyecto
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data")

def get_db_path() -> str:
    """Ruta del archivo SQLite.

    Se puede sobreescribir con la variable de entorno ``FINANZAS_DB``
    (útil para pruebas aisladas).
    """
    override = os.environ.get("FINANZAS_DB")
    if override:
        os.makedirs(os.path.dirname(os.path.abspath(override)), exist_ok=True)
        return override
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "finanzas.db")
