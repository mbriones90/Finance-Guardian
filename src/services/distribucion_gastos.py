"""Distribución de gastos por categoría: real y proyectada.

- **Real**: lo gastado en la semana actual y en el mes actual, por categoría.
- **Proyección**: el promedio semanal histórico de la categoría (o su
  presupuesto base si aún no hay gastos) llevado a 1 semana, 1 mes,
  1 año y 10 años.

Todas las categorías del catálogo aparecen, aunque no tengan gastos.
"""

import calendar
from datetime import date
from typing import Any, Dict, List

from src.repositories import gasto_repo
from src.services.categorias import CATEGORIAS_GASTO
from src.services.presupuesto_semanal import (
    listar_presupuesto_base,
    obtener_presupuesto_general,
    rango_semana,
)


def _gastos_reales() -> Dict[str, Dict[str, float]]:
    """Gasto real por categoría en la semana y el mes actuales."""
    inicio_sem, fin_sem = rango_semana()
    hoy = date.today()
    ultimo = calendar.monthrange(hoy.year, hoy.month)[1]
    inicio_mes = date(hoy.year, hoy.month, 1).isoformat()
    fin_mes = date(hoy.year, hoy.month, ultimo).isoformat()

    filas = gasto_repo.execute_query(
        """SELECT categoria,
                  COALESCE(SUM(CASE WHEN fecha >= ? AND fecha <= ?
                                    THEN convertido_a_pesos ELSE 0 END), 0) AS semana,
                  COALESCE(SUM(CASE WHEN fecha >= ? AND fecha <= ?
                                    THEN convertido_a_pesos ELSE 0 END), 0) AS mes
           FROM gastos GROUP BY categoria""",
        (inicio_sem, fin_sem, inicio_mes, fin_mes),
    )
    return {
        f["categoria"]: {"semana": round(float(f["semana"]), 2),
                         "mes": round(float(f["mes"]), 2)}
        for f in filas
    }


def _promedios_semanales() -> Dict[str, float]:
    """Promedio semanal histórico por categoría.

    Se calcula desde el primer gasto registrado (mínimo 1 semana) para no
    inflar el promedio con historiales vacíos.
    """
    filas = gasto_repo.execute_query(
        """SELECT categoria,
                  COALESCE(SUM(convertido_a_pesos), 0) AS total,
                  MIN(fecha) AS primera
           FROM gastos GROUP BY categoria"""
    )
    hoy = date.today()
    promedios: Dict[str, float] = {}
    for f in filas:
        primera = date.fromisoformat(f["primera"])
        semanas = max(1, ((hoy - primera).days + 1 + 6) // 7)
        promedios[f["categoria"]] = round(float(f["total"]) / semanas, 2)
    return promedios


def distribucion_gastos() -> Dict[str, Any]:
    """Tabla de distribución por categoría: real y proyecciones."""
    reales = _gastos_reales()
    promedios = _promedios_semanales()
    base = {f["categoria"]: float(f["monto_limite_base"])
            for f in listar_presupuesto_base()}

    categorias: List[Dict[str, Any]] = []
    for cat in CATEGORIAS_GASTO:
        real_sem = reales.get(cat, {}).get("semana", 0.0)
        real_mes = reales.get(cat, {}).get("mes", 0.0)
        # Base de proyección: promedio histórico; si no hay gastos, el
        # presupuesto base planeado.
        proy_sem = promedios.get(cat, base.get(cat, 0.0))
        fila = {
            "categoria": cat,
            "real_semana": real_sem,
            "real_mes": real_mes,
            "presupuesto_semanal": round(base.get(cat, 0.0), 2),
            "proy_semana": round(proy_sem, 2),
            "proy_mes": round(proy_sem * 52 / 12, 2),
            "proy_ano": round(proy_sem * 52, 2),
            "proy_diez_anos": round(proy_sem * 520, 2),
        }
        categorias.append(fila)

    totales = {
        "real_semana": round(sum(c["real_semana"] for c in categorias), 2),
        "real_mes": round(sum(c["real_mes"] for c in categorias), 2),
        "presupuesto_semanal": round(sum(c["presupuesto_semanal"]
                                         for c in categorias), 2),
        "proy_semana": round(sum(c["proy_semana"] for c in categorias), 2),
        "proy_mes": round(sum(c["proy_mes"] for c in categorias), 2),
        "proy_ano": round(sum(c["proy_ano"] for c in categorias), 2),
        "proy_diez_anos": round(sum(c["proy_diez_anos"] for c in categorias), 2),
    }

    return {
        "categorias": categorias,
        "totales": totales,
        "presupuesto_general": obtener_presupuesto_general(),
        "con_datos": bool(promedios),
    }
