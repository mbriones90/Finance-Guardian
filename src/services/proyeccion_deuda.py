"""Proyección de deuda de tarjetas de crédito (1 a 12 meses).

Dado un pago mensual fijo, proyecta mes a mes:
    saldo_inicial → + interés (tasa mensual) → - pago → saldo_final

Cuando el saldo llega a cero se registra la fecha estimada de liquidación.
Opcionalmente guarda cada fila en la tabla ``simulaciones_deuda``.

Nota: la proyección no incluye cargos por administración recurrentes;
esos se modelan aparte (ver cargos_admin).
"""

import calendar
from datetime import date
from typing import Any, Dict, List, Optional

from src.database import get_connection
from src.repositories import cuenta_repo, tarjeta_repo


def _sumar_meses(d: date, meses: int) -> date:
    """Suma meses a una fecha ajustando al último día del mes si hace falta."""
    total = d.month - 1 + meses
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _obtener_reglas(cuenta_id: int) -> Dict[str, Any]:
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    if cuenta["tipo"] != "tarjeta_credito":
        raise ValueError("La proyección de deuda aplica solo a tarjetas de crédito.")
    reglas = tarjeta_repo.get_by_cuenta(cuenta_id)
    if not reglas:
        raise ValueError("La tarjeta no tiene reglas configuradas.")
    return reglas


def proyectar_desde_saldo(
    saldo_inicial: float,
    tasa_interes_mensual: float,
    pago_mensual: float,
    meses: int = 12,
    desde: Optional[date] = None,
) -> Dict[str, Any]:
    """Proyección pura (no toca la base de datos).

    Útil para simulaciones ("¿qué pasa si compro X?") sin guardar nada.
    """
    saldo_inicial = round(float(saldo_inicial), 2)
    pago_mensual = float(pago_mensual)
    if pago_mensual <= 0:
        raise ValueError("El pago mensual debe ser mayor que cero.")
    if meses < 1:
        raise ValueError("El horizonte debe ser de al menos 1 mes.")

    desde = desde or date.today()
    saldo = saldo_inicial
    filas: List[Dict[str, Any]] = []
    interes_total = 0.0
    meses_para_liquidar: Optional[int] = None
    fecha_liquidacion: Optional[str] = None

    for mes in range(1, meses + 1):
        saldo_inicial_mes = saldo
        interes = round(saldo_inicial_mes * float(tasa_interes_mensual) / 100, 2)
        interes_total = round(interes_total + interes, 2)
        pago = round(min(pago_mensual, saldo_inicial_mes + interes), 2)
        saldo_final = round(saldo_inicial_mes + interes - pago, 2)
        fecha_mes = _sumar_meses(desde, mes)

        liquidada = saldo_final <= 0
        filas.append(
            {
                "mes_proyectado": mes,
                "saldo_inicial": saldo_inicial_mes,
                "pago_aplicado": pago,
                "interes_generado": interes,
                "cargo_admin": 0.0,
                "saldo_final": max(0.0, saldo_final),
                "fecha": fecha_mes.isoformat(),
                "liquidada": liquidada,
            }
        )

        if liquidada and meses_para_liquidar is None:
            meses_para_liquidar = mes
            fecha_liquidacion = fecha_mes.isoformat()

        saldo = saldo_final
        if liquidada:
            break

    saldos_por_horizonte = {}
    for h in (1, 3, 6, 9, 12):
        if h <= len(filas):
            saldos_por_horizonte[f"mes_{h}"] = filas[h - 1]["saldo_final"]
        else:
            saldos_por_horizonte[f"mes_{h}"] = 0.0

    return {
        "filas": filas,
        "meses_para_liquidar": meses_para_liquidar,
        "fecha_estimada_liquidacion": fecha_liquidacion,
        "interes_total": interes_total,
        "saldos_por_horizonte": saldos_por_horizonte,
    }


def proyectar(
    cuenta_id: int,
    pago_mensual: float,
    meses: int = 12,
    guardar: bool = True,
    perfil_id: Optional[int] = None,
    desde: Optional[date] = None,
) -> Dict[str, Any]:
    """Proyecta la reducción de deuda de una tarjeta real.

    Args:
        cuenta_id: id de la cuenta tipo tarjeta_credito.
        pago_mensual: pago fijo aplicado cada mes.
        meses: horizonte de proyección (por defecto 12).
        guardar: si True, inserta las filas en simulaciones_deuda.
        perfil_id: perfil de pago asociado (opcional en Fase 5).
        desde: fecha base de la proyección (por defecto hoy).
    """
    desde = desde or date.today()
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    reglas = _obtener_reglas(cuenta_id)
    tasa = float(reglas.get("tasa_interes_mensual") or 0)
    deuda = round(float(cuenta["balance_actual"]), 2)

    resultado = proyectar_desde_saldo(deuda, tasa, pago_mensual, meses, desde)

    if guardar:
        _guardar(cuenta_id, perfil_id, resultado["filas"], resultado["fecha_estimada_liquidacion"])

    return {
        "cuenta_id": cuenta_id,
        "nombre": cuenta["nombre"],
        "deuda_actual": deuda,
        "tasa_interes_mensual": tasa,
        "pago_mensual": pago_mensual,
        **resultado,
    }


def _guardar(
    cuenta_id: int,
    perfil_id: Optional[int],
    filas: List[Dict[str, Any]],
    fecha_liquidacion: Optional[str],
) -> None:
    """Guarda la proyección en la tabla simulaciones_deuda."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM simulaciones_deuda WHERE cuenta_id = ? AND perfil_id IS ?",
            (cuenta_id, perfil_id),
        )
        for f in filas:
            # La tabla guarda solo los primeros 12 meses (horizontes mayores,
            # como el de liquidación completa, se calculan en memoria).
            if f["mes_proyectado"] > 12:
                continue
            cur.execute(
                """INSERT INTO simulaciones_deuda
                   (perfil_id, cuenta_id, mes_proyectado, saldo_inicial,
                    pago_aplicado, interes_generado, cargo_admin, saldo_final,
                    fecha_estimada_liquidacion)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    perfil_id,
                    cuenta_id,
                    f["mes_proyectado"],
                    f["saldo_inicial"],
                    f["pago_aplicado"],
                    f["interes_generado"],
                    f["cargo_admin"],
                    f["saldo_final"],
                    fecha_liquidacion if f["liquidada"] else None,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def obtener_proyeccion_guardada(cuenta_id: int) -> List[Dict[str, Any]]:
    """Devuelve la última proyección guardada de una tarjeta."""
    from src.repositories import BaseRepository

    repo = BaseRepository("simulaciones_deuda")
    return repo.execute_query(
        """SELECT s.*, p.nombre AS perfil
           FROM simulaciones_deuda s
           LEFT JOIN perfiles_pago p ON s.perfil_id = p.id
           WHERE s.cuenta_id = ?
           ORDER BY s.mes_proyectado""",
        (cuenta_id,),
    )
