"""Exportación de datos a CSV (Santuario de Datos / Dimensión 12).

Genera archivos CSV UTF-8 con encabezados desde las tablas principales.
"""

import csv
import os
from typing import Any, Dict, List

from src.repositories import BaseRepository, gasto_repo, ingreso_repo, suscripcion_repo

# Tablas exportables: nombre lógico -> repositorio
EXPORTABLES = {
    "gastos": gasto_repo,
    "ingresos": ingreso_repo,
    "suscripciones": suscripcion_repo,
    "cuentas": BaseRepository("cuentas"),
    "tarjetas_credito": BaseRepository("tarjetas_credito"),
    "perfiles_pago": BaseRepository("perfiles_pago"),
    "simulaciones_deuda": BaseRepository("simulaciones_deuda"),
    "simulacion_compra_cara": BaseRepository("simulacion_compra_cara"),
    "presupuestos_semanales": BaseRepository("presupuestos_semanales"),
}

CARPETA_DEFAULT = "exports"


def exportar_tabla(nombre: str, carpeta: str = CARPETA_DEFAULT) -> str:
    """Exporta una tabla a CSV y devuelve la ruta del archivo."""
    if nombre not in EXPORTABLES:
        raise ValueError(
            f"Tabla no exportable: {nombre!r}. Usa {sorted(EXPORTABLES)}."
        )
    filas: List[Dict[str, Any]] = EXPORTABLES[nombre].get_all()

    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{nombre}.csv")
    columnas = list(filas[0].keys()) if filas else _columnas(nombre)

    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)
    return os.path.abspath(ruta)


def _columnas(nombre: str) -> List[str]:
    filas = EXPORTABLES[nombre].execute_query(f"PRAGMA table_info({nombre})")
    return [f["name"] for f in filas]


def exportar_todo(carpeta: str = CARPETA_DEFAULT) -> Dict[str, str]:
    """Exporta todas las tablas. Devuelve {tabla: ruta}."""
    return {nombre: exportar_tabla(nombre, carpeta) for nombre in EXPORTABLES}


def listar_tablas() -> List[str]:
    return sorted(EXPORTABLES)
