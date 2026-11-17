"""Catálogo de categorías de gastos.

Todos los gastos caen dentro de una categoría (dropdown al registrarlos).
Las mismas categorías se usan para distribuir el presupuesto semanal y
para la sección de distribución de gastos (real y proyectada).
"""

from typing import List

CATEGORIAS_GASTO: List[str] = [
    "Alimentos",
    "Comida Fuera",
    "Supermercado",
    "Transporte",
    "Hogar",
    "Servicios",
    "Suscripciones",
    "Tecnología",
    "Intereses",
    "Salud",
    "Personal",
    "Ropa",
    "Educación",
    "Entretenimiento",
    "Salidas",
    "Mascotas",
    "Viajes",
    "Ahorro e Inversión",
    "Otros",
]

CATEGORIA_DEFAULT = "Alimentos"


def es_categoria_valida(categoria: str) -> bool:
    return (categoria or "").strip() in CATEGORIAS_GASTO
