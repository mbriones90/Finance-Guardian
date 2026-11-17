"""Calendario de pagos: cortes, pagos de tarjeta y cobros de suscripciones.

Eventos recurrentes mensuales (el día se ajusta al último del mes si hace
falta, ej. día 31 en febrero → 28/29):

- 💳 ``corte_tarjeta``: día de corte de cada tarjeta activa.
- 💰 ``pago_tarjeta``: día de pago de cada tarjeta activa.
- 📦 ``suscripcion``: día de cobro de cada suscripción activa.
- 💵 ``cobro_sueldo``: días de pago del sueldo (quincenal: día N y N+15).

La vista puede mostrar el calendario en modo semanal o mensual.
"""

import calendar
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.repositories import ingreso_repo, suscripcion_repo, tarjeta_repo
from src.services.convertidor import convertir_a_pesos
from src.services.ingresos import dias_cobro_del_mes
from src.services.presupuesto_semanal import lunes_de

TIPOS_EVENTO = ("corte_tarjeta", "pago_tarjeta", "suscripcion", "cobro_sueldo")

ICONO_EVENTO = {
    "corte_tarjeta": "💳",
    "pago_tarjeta": "💰",
    "suscripcion": "📦",
    "cobro_sueldo": "💵",
}


def _fecha_ajustada(year: int, month: int, dia: int) -> date:
    """Día del mes ajustado al último día si el mes es más corto."""
    ultimo = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(1, int(dia)), ultimo))


def _eventos_mes(year: int, month: int) -> List[Dict[str, Any]]:
    """Todos los eventos de pago de un mes concreto, ordenados por fecha."""
    eventos: List[Dict[str, Any]] = []

    for t in tarjeta_repo.get_activas():
        nombre = t["nombre"]
        eventos.append({
            "fecha": _fecha_ajustada(year, month, t["dia_corte"]).isoformat(),
            "tipo": "corte_tarjeta",
            "titulo": f"Corte {nombre}",
            "monto": None,
            "detalle": f"Día de corte de {nombre}",
        })
        eventos.append({
            "fecha": _fecha_ajustada(year, month, t["dia_pago"]).isoformat(),
            "tipo": "pago_tarjeta",
            "titulo": f"Pago {nombre}",
            "monto": None,
            "detalle": f"Fecha límite de pago de {nombre}",
        })

    for s in suscripcion_repo.get_activas():
        monto_pesos = convertir_a_pesos(s["monto"], s["moneda"])
        periodo = s.get("periodo", "mensual")
        eventos.append({
            "fecha": _fecha_ajustada(year, month, s["dia_cobro"]).isoformat(),
            "tipo": "suscripcion",
            "titulo": s["nombre"],
            "monto": monto_pesos,
            "detalle": (f"Cobro {periodo} de {s['nombre']}: "
                        f"${monto_pesos:,.2f} MXN"),
        })

    for ing in ingreso_repo.get_recurrentes():
        monto_pesos = float(ing["convertido_a_pesos"])
        frecuencia = ing.get("frecuencia") or "mensual"
        for dia in dias_cobro_del_mes(ing, year, month):
            eventos.append({
                "fecha": date(year, month, dia).isoformat(),
                "tipo": "cobro_sueldo",
                "titulo": f"Cobro {ing['categoria']}",
                "monto": monto_pesos,
                "detalle": (f"Sueldo {frecuencia} ({ing['categoria']}): "
                            f"+${monto_pesos:,.2f} MXN"),
            })

    eventos.sort(key=lambda e: (e["fecha"], e["tipo"]))
    return eventos


def eventos_del_mes(year: int, month: int) -> List[Dict[str, Any]]:
    """Eventos de un mes (para la vista mensual del calendario)."""
    year, month = int(year), int(month)
    if not 1 <= month <= 12:
        raise ValueError(f"Mes inválido: {month}. Debe estar entre 1 y 12.")
    return _eventos_mes(year, month)


def eventos_de_semana(lunes: Optional[date] = None) -> List[Dict[str, Any]]:
    """Eventos de la semana (lunes a domingo) del lunes indicado.

    La semana puede cruzar dos meses; se combinan los eventos de ambos.
    """
    lunes = lunes_de(lunes)
    domingo = lunes + timedelta(days=6)
    meses = {(lunes.year, lunes.month), (domingo.year, domingo.month)}

    eventos: List[Dict[str, Any]] = []
    for year, month in meses:
        for e in _eventos_mes(year, month):
            if lunes.isoformat() <= e["fecha"] <= domingo.isoformat():
                eventos.append(e)
    eventos.sort(key=lambda e: (e["fecha"], e["tipo"]))
    return eventos


def resumen_mes(year: int, month: int) -> Dict[str, Any]:
    """Totales del mes: eventos, pagos de suscripciones y cobros de sueldo."""
    eventos = eventos_del_mes(year, month)
    total_suscripciones = round(
        sum(e["monto"] or 0 for e in eventos if e["tipo"] == "suscripcion"), 2)
    total_sueldos = round(
        sum(e["monto"] or 0 for e in eventos if e["tipo"] == "cobro_sueldo"), 2)
    return {
        "eventos": len(eventos),
        "cortes": sum(1 for e in eventos if e["tipo"] == "corte_tarjeta"),
        "pagos_tarjeta": sum(1 for e in eventos if e["tipo"] == "pago_tarjeta"),
        "cobros_suscripcion": sum(1 for e in eventos
                                  if e["tipo"] == "suscripcion"),
        "total_suscripciones": total_suscripciones,
        "cobros_sueldo": sum(1 for e in eventos if e["tipo"] == "cobro_sueldo"),
        "total_sueldos": total_sueldos,
    }
