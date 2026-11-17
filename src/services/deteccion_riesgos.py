"""Detección de riesgos financieros y alertas del dashboard.

Evalúa el estado global y devuelve alertas con semáforo:
- 🔴 ``rojo``: acción inmediata requerida.
- 🟡 ``amarillo``: advertencia, revisar.
- 🟢 ``verde``: todo bajo control.

Riesgos evaluados en Fase 5:
1. Uso del límite de crédito por tarjeta.
2. Riesgo de no alcanzar el mínimo de uso mensual (cargo de administración).
3. Suscripciones que pesan demasiado sobre los ingresos del mes.
4. Deuda creciente (pago <= interés mensual) — función auxiliar por tarjeta.
"""

import calendar
from datetime import date
from typing import Any, Dict, List, Optional

from src.repositories import (
    cuenta_repo,
    gasto_repo,
    ingreso_repo,
    suscripcion_repo,
    tarjeta_repo,
)
from src.services.cargos_admin import uso_del_mes
from src.services.convertidor import convertir_a_pesos


def riesgo_deuda_creciente(deuda: float, tasa_interes_mensual: float, pago_mensual: float) -> bool:
    """True si el pago mensual no alcanza a cubrir el interés del mes.

    En ese caso, aunque se pague, la deuda seguiría creciendo.
    """
    deuda = float(deuda)
    if deuda <= 0:
        return False
    interes = deuda * float(tasa_interes_mensual) / 100
    return float(pago_mensual) <= interes


def _rango_mes_actual() -> tuple:
    hoy = date.today()
    ultimo = calendar.monthrange(hoy.year, hoy.month)[1]
    return (
        date(hoy.year, hoy.month, 1).isoformat(),
        date(hoy.year, hoy.month, ultimo).isoformat(),
    )


def evaluar_riesgos() -> List[Dict[str, Any]]:
    """Evalúa todos los riesgos conocidos y devuelve la lista de alertas."""
    alertas: List[Dict[str, Any]] = []

    # 1. Límite de crédito y mínimo de uso por tarjeta
    for t in tarjeta_repo.get_activas():
        cuenta_id = t["cuenta_id"]
        cuenta = cuenta_repo.get_by_id(cuenta_id)
        if not cuenta:
            continue

        deuda = float(cuenta["balance_actual"])
        limite = t.get("limite_credito_maximo")
        minimo = float(t.get("minimo_uso_monto") or 0)

        if limite:
            uso = deuda / float(limite) * 100 if limite > 0 else 0
            if uso >= 100:
                alertas.append({
                    "nivel": "rojo",
                    "tipo": "limite_credito",
                    "cuenta_id": cuenta_id,
                    "mensaje": f"{cuenta['nombre']}: límite de crédito EXCEDIDO "
                               f"(${deuda:,.2f} de ${float(limite):,.2f}).",
                })
            elif uso >= 90:
                alertas.append({
                    "nivel": "amarillo",
                    "tipo": "limite_credito",
                    "cuenta_id": cuenta_id,
                    "mensaje": f"{cuenta['nombre']}: uso del crédito al {uso:.0f}% "
                               "del límite.",
                })

        if minimo > 0:
            hoy = date.today()
            uso_mes = uso_del_mes(cuenta_id, hoy.year, hoy.month)
            if uso_mes < minimo:
                alertas.append({
                    "nivel": "amarillo",
                    "tipo": "minimo_uso",
                    "cuenta_id": cuenta_id,
                    "mensaje": f"{cuenta['nombre']}: llevas ${uso_mes:,.2f} del mínimo "
                               f"de uso de ${minimo:,.2f}. Si no alcanzas, se cobra "
                               f"${float(t.get('costo_admin_si_no_alcance') or 0):,.2f} "
                               "de administración.",
                })

    # 2. Suscripciones vs ingresos del mes
    from src.services.suscripciones import total_mensual_pesos
    total_suscripciones = total_mensual_pesos()

    desde, hasta = _rango_mes_actual()
    ingresos_mes = ingreso_repo.execute_query(
        "SELECT COALESCE(SUM(convertido_a_pesos), 0) AS total FROM ingresos "
        "WHERE fecha >= ? AND fecha <= ?",
        (desde, hasta),
    )[0]["total"]

    if total_suscripciones > 0 and float(ingresos_mes) <= 0:
        alertas.append({
            "nivel": "amarillo",
            "tipo": "suscripciones",
            "cuenta_id": None,
            "mensaje": f"Tienes ${total_suscripciones:,.2f} en suscripciones este mes "
                       "y aún no registras ingresos.",
        })
    elif total_suscripciones > 0 and float(ingresos_mes) > 0:
        ratio = total_suscripciones / float(ingresos_mes)
        if ratio > 0.2:
            alertas.append({
                "nivel": "amarillo",
                "tipo": "suscripciones",
                "cuenta_id": None,
                "mensaje": f"Las suscripciones (${total_suscripciones:,.2f}) "
                           f"representan el {ratio*100:.0f}% de tus ingresos del mes "
                           "(umbral: 20%).",
            })

    # 3. Sin deudas ni gastos: estado sano
    if not alertas:
        alertas.append({
            "nivel": "verde",
            "tipo": "ok",
            "cuenta_id": None,
            "mensaje": "Todo bajo control, Guardián. Sin riesgos detectados.",
        })

    return alertas
