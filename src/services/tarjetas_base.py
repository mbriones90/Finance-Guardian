"""Cálculos de fechas de corte y pago de tarjetas de crédito (nivel base).

Aún no calcula intereses ni cargos por administración (eso es Fase 5).
Aquí solo se resuelven las fechas del ciclo y la cuenta regresiva.
"""

import calendar
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.repositories import cuenta_repo, tarjeta_repo


def _fecha_con_dia(year: int, month: int, day: int) -> date:
    """Construye una fecha ajustando el día al último del mes si hace falta."""
    ultimo_dia = calendar.monthrange(year, month)[1]
    return date(year, month, min(max(1, day), ultimo_dia))


def proxima_fecha_mes(dia: int, desde: Optional[date] = None) -> date:
    """Devuelve la próxima ocurrencia del día del mes (hoy cuenta como hoy)."""
    if not 1 <= int(dia) <= 31:
        raise ValueError("El día del mes debe estar entre 1 y 31.")
    desde = desde or date.today()
    candidato = _fecha_con_dia(desde.year, desde.month, dia)
    if candidato < desde:
        if desde.month == 12:
            candidato = _fecha_con_dia(desde.year + 1, 1, dia)
        else:
            candidato = _fecha_con_dia(desde.year, desde.month + 1, dia)
    return candidato


def dias_hasta(dia: int, desde: Optional[date] = None) -> int:
    """Días que faltan para el próximo día indicado del mes."""
    desde = desde or date.today()
    return (proxima_fecha_mes(dia, desde) - desde).days


def configurar_tarjeta(
    cuenta_id: int,
    dia_corte: int,
    dia_pago: int,
    dias_para_pagar: int = 30,
    tasa_interes_mensual: float = 0.0,
    limite_credito_maximo: Optional[float] = None,
    minimo_uso_monto: float = 0.0,
    costo_admin_si_no_alcance: float = 0.0,
    activa: bool = True,
) -> None:
    """Crea o actualiza las reglas de una tarjeta de crédito (upsert)."""
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    if cuenta["tipo"] != "tarjeta_credito":
        raise ValueError("Solo se pueden configurar cuentas de tipo 'tarjeta_credito'.")
    if not (1 <= int(dia_corte) <= 31) or not (1 <= int(dia_pago) <= 31):
        raise ValueError("Los días de corte y pago deben estar entre 1 y 31.")
    if int(dias_para_pagar) < 0:
        raise ValueError("Los días para pagar no pueden ser negativos.")

    datos = {
        "dia_corte": int(dia_corte),
        "dia_pago": int(dia_pago),
        "dias_para_pagar": int(dias_para_pagar),
        "tasa_interes_mensual": float(tasa_interes_mensual),
        "limite_credito_maximo": limite_credito_maximo,
        "minimo_uso_monto": float(minimo_uso_monto),
        "costo_admin_si_no_alcance": float(costo_admin_si_no_alcance),
        "activa": 1 if activa else 0,
    }

    if tarjeta_repo.get_by_cuenta(cuenta_id):
        tarjeta_repo.update_by_cuenta(cuenta_id, datos)
    else:
        datos["cuenta_id"] = cuenta_id
        tarjeta_repo.create(datos)


def info_tarjeta(cuenta_id: int, desde: Optional[date] = None) -> Dict[str, Any]:
    """Resumen del ciclo de una tarjeta: corte, pago y días restantes."""
    desde = desde or date.today()
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    if cuenta["tipo"] != "tarjeta_credito":
        raise ValueError("La cuenta indicada no es una tarjeta de crédito.")

    reglas = tarjeta_repo.get_by_cuenta(cuenta_id)
    if not reglas:
        raise ValueError("La tarjeta no tiene reglas configuradas.")

    prox_corte = proxima_fecha_mes(reglas["dia_corte"], desde)
    prox_pago = proxima_fecha_mes(reglas["dia_pago"], desde)
    # Fecha límite de pago derivada del corte + días de gracia
    pago_por_corte = prox_corte + timedelta(days=int(reglas["dias_para_pagar"]))

    return {
        "cuenta_id": cuenta_id,
        "nombre": cuenta["nombre"],
        "dia_corte": reglas["dia_corte"],
        "dia_pago": reglas["dia_pago"],
        "dias_para_pagar": reglas["dias_para_pagar"],
        "proximo_corte": prox_corte.isoformat(),
        "dias_hasta_corte": (prox_corte - desde).days,
        "proximo_pago": prox_pago.isoformat(),
        "dias_hasta_pago": (prox_pago - desde).days,
        "pago_por_corte": pago_por_corte.isoformat(),
        "dias_hasta_pago_por_corte": (pago_por_corte - desde).days,
        "balance_deuda": cuenta["balance_actual"],
        "moneda": cuenta["moneda"],
    }


def listar_tarjetas(desde: Optional[date] = None) -> List[Dict[str, Any]]:
    """Lista las tarjetas activas con su información de ciclo."""
    desde = desde or date.today()
    resultado = []
    for t in tarjeta_repo.get_activas():
        try:
            resultado.append(info_tarjeta(t["cuenta_id"], desde))
        except ValueError:
            continue
    return resultado
