"""Inventario del personaje: armaduras por calidad y fondos.

Calidades de armadura (con costo en puntos para desbloquear):
    gris (0, inicial) · verde (200) · azul (500) · morado (1200) · naranja (3000)

Los fondos corresponden a los paisajes de las dimensiones
(``assets/fondos/*.png``) y se pueden cambiar libremente: los temas
visuales son generales por versión de la app.
"""

from typing import Any, Dict, List

from src.repositories import BaseRepository, personaje_repo
from src.services.puntos import gastar_puntos, obtener_puntos

_inv = BaseRepository("inventario_armadura")

COSTO_ARMADURA = {
    "gris": 0,
    "verde": 200,
    "azul": 500,
    "morado": 1200,
    "naranja": 3000,
}
ORDEN_CALIDAD = ["gris", "verde", "azul", "morado", "naranja"]

FONDOS = {
    "default": None,
    "d1_despertar_dia": "assets/fondos/d1_despertar_dia.png",
    "d1_despertar_tormenta": "assets/fondos/d1_despertar_tormenta.png",
    "d2_camino_oro": "assets/fondos/d2_camino_oro.png",
    "d3_bosque_gastos": "assets/fondos/d3_bosque_gastos.png",
    "d4_puerta_credito": "assets/fondos/d4_puerta_credito.png",
    "d5_camara_reglas": "assets/fondos/d5_camara_reglas.png",
    "d6_llanura_presupuesto": "assets/fondos/d6_llanura_presupuesto.png",
    "d7_mercado_suscripciones": "assets/fondos/d7_mercado_suscripciones.png",
    "d8_prueba_dragon": "assets/fondos/d8_prueba_dragon.png",
    "d9_salon_estrategas": "assets/fondos/d9_salon_estrategas.png",
    "d10_forja_guardian": "assets/fondos/d10_forja_guardian.png",
    "d11_torre_comparacion": "assets/fondos/d11_torre_comparacion.png",
    "d12_santuario_datos": "assets/fondos/d12_santuario_datos.png",
    "d13_dimension_maestra": "assets/fondos/d13_dimension_maestra.png",
}


def listar_armaduras() -> List[Dict[str, Any]]:
    """Inventario con estado: desbloqueada, costo y equipada."""
    personaje = personaje_repo.get_default()
    equipada = personaje["armadura_actual"] if personaje else None
    filas = _inv.execute_query(
        f"""SELECT * FROM inventario_armadura
            ORDER BY CASE calidad {' '.join(f"WHEN '{c}' THEN {i}" for i, c in enumerate(ORDEN_CALIDAD))}
            END"""
    )
    resultado = []
    for f in filas:
        calidad = f["calidad"]
        resultado.append({
            "id": f["id"],
            "nombre": f["nombre"],
            "calidad": calidad,
            "desbloqueada": bool(f["desbloqueada"]),
            "costo": COSTO_ARMADURA.get(calidad, 0),
            "equipada": calidad == equipada,
        })
    return resultado


def _fila_armadura(calidad: str) -> Dict[str, Any]:
    filas = _inv.execute_query(
        "SELECT * FROM inventario_armadura WHERE calidad = ?", (calidad,)
    )
    if not filas:
        raise ValueError(
            f"Calidad inválida: {calidad!r}. Usa {ORDEN_CALIDAD}."
        )
    return filas[0]


def desbloquear_armadura(calidad: str) -> Dict[str, Any]:
    """Desbloquea una armadura pagando su costo con puntos."""
    fila = _fila_armadura(calidad)
    if fila["desbloqueada"]:
        raise ValueError(f"La armadura {calidad!r} ya está desbloqueada.")
    costo = COSTO_ARMADURA.get(calidad, 0)
    saldo = gastar_puntos(costo)  # lanza error si no alcanza
    _inv.update(fila["id"], {"desbloqueada": 1})
    return {"calidad": calidad, "costo": costo, "puntos_restantes": saldo}


def equipar_armadura(calidad: str) -> None:
    """Equipa una armadura (debe estar desbloqueada)."""
    fila = _fila_armadura(calidad)
    if not fila["desbloqueada"]:
        raise ValueError(
            f"La armadura {calidad!r} no está desbloqueada "
            f"(costo: {COSTO_ARMADURA.get(calidad, 0)} puntos)."
        )
    personaje_repo.update(1, {"armadura_actual": calidad})


def equipar_fondo(nombre_fondo: str) -> None:
    """Cambia el fondo visual del personaje (libre, sin costos)."""
    if nombre_fondo not in FONDOS:
        raise ValueError(f"Fondo inválido. Disponibles: {sorted(FONDOS)}")
    personaje_repo.update(1, {"fondo_actual": nombre_fondo})


def listar_fondos() -> List[Dict[str, Any]]:
    personaje = personaje_repo.get_default()
    actual = personaje["fondo_actual"] if personaje else "default"
    return [
        {"nombre": nombre, "imagen": imagen, "actual": nombre == actual}
        for nombre, imagen in FONDOS.items()
    ]


def puntos_disponibles() -> int:
    return obtener_puntos()
