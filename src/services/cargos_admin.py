"""Cargos por administración por no alcanzar el mínimo de uso mensual.

Caso real: tarjeta Invex de Sams — hay que gastar $2,000 MXN al mes;
si no se alcanza, se cobra un cargo de administración (~$300 MXN).

Reglas:
- El "uso del mes" se mide con los gastos de la tarjeta en ese mes
  (excluyendo los propios cargos de administración, para no contar el
  cargo como "uso").
- El cargo se aplica como un gasto con categoría ``cargo_administracion``
  que aumenta la deuda de la tarjeta.
- Es idempotente por mes: si ya se aplicó el cargo de ese mes, no se duplica.
"""

import calendar
from datetime import date, datetime
from typing import Any, Dict

from src.repositories import cuenta_repo, gasto_repo, tarjeta_repo
from src.services.convertidor import convertir_a_pesos

CATEGORIA_CARGO = "cargo_administracion"


def _rango_mes(year: int, month: int) -> tuple:
    """Primer y último día del mes en formato ISO."""
    ultimo = calendar.monthrange(year, month)[1]
    return (
        date(year, month, 1).isoformat(),
        date(year, month, ultimo).isoformat(),
    )


def uso_del_mes(cuenta_id: int, year: int, month: int) -> float:
    """Suma en pesos de los gastos de la tarjeta en el mes indicado.

    Excluye los cargos de administración para que no cuenten como uso.
    """
    desde, hasta = _rango_mes(year, month)
    gastos = gasto_repo.execute_query(
        """SELECT COALESCE(SUM(convertido_a_pesos), 0) AS total
           FROM gastos
           WHERE cuenta_id = ? AND fecha >= ? AND fecha <= ?
             AND categoria != ?""",
        (cuenta_id, desde, hasta, CATEGORIA_CARGO),
    )
    return round(float(gastos[0]["total"]), 2)


def cargo_ya_aplicado(cuenta_id: int, year: int, month: int) -> bool:
    """True si el cargo de administración de ese mes ya fue aplicado.

    Se rastrea por el mes evaluado en la descripción del cargo
    (no por la fecha del gasto), porque el cargo puede registrarse
    en una fecha distinta al mes que lo originó.
    """
    marcador = f"({year}-{month:02d})"
    filas = gasto_repo.execute_query(
        """SELECT COUNT(*) AS n FROM gastos
           WHERE cuenta_id = ? AND categoria = ? AND descripcion LIKE ?""",
        (cuenta_id, CATEGORIA_CARGO, f"%{marcador}%"),
    )
    return int(filas[0]["n"]) > 0


def evaluar_minimo_uso(
    cuenta_id: int, year: int, month: int, aplicar: bool = True
) -> Dict[str, Any]:
    """Evalúa si la tarjeta alcanzó su mínimo de uso mensual.

    Devuelve un resumen con el uso, el mínimo, y si se aplicó el cargo.
    Con ``aplicar=True`` el cargo se registra y sube la deuda.
    """
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    if cuenta["tipo"] != "tarjeta_credito":
        raise ValueError("La cuenta indicada no es una tarjeta de crédito.")

    reglas = tarjeta_repo.get_by_cuenta(cuenta_id)
    if not reglas:
        raise ValueError("La tarjeta no tiene reglas configuradas.")

    minimo = float(reglas.get("minimo_uso_monto") or 0)
    costo = float(reglas.get("costo_admin_si_no_alcance") or 0)
    uso = uso_del_mes(cuenta_id, year, month)

    resultado: Dict[str, Any] = {
        "cuenta_id": cuenta_id,
        "nombre": cuenta["nombre"],
        "year": year,
        "month": month,
        "uso_del_mes": uso,
        "minimo_uso": minimo,
        "costo_admin": costo,
        "alcanza_minimo": uso >= minimo if minimo > 0 else True,
        "cargo_aplicado": False,
        "deuda_nueva": float(cuenta["balance_actual"]),
    }

    if not resultado["alcanza_minimo"] and costo > 0:
        if cargo_ya_aplicado(cuenta_id, year, month):
            resultado["mensaje"] = "El cargo de administración ya fue aplicado este mes."
            return resultado

        if not aplicar:
            resultado["mensaje"] = (
                f"No alcanzó el mínimo de uso (${minimo:,.2f}). "
                f"Se aplicaría un cargo de ${costo:,.2f}."
            )
            return resultado

        fecha_hoy = date.today().isoformat()
        gasto_repo.create(
            {
                "cuenta_id": cuenta_id,
                "categoria": CATEGORIA_CARGO,
                "descripcion": f"Cargo por no alcanzar mínimo de uso de ${minimo:,.2f} ({year}-{month:02d})",
                "monto": costo,
                "moneda": "MXN",
                "fecha": fecha_hoy,
                "convertido_a_pesos": costo,
            }
        )
        deuda_nueva = round(float(cuenta["balance_actual"]) + costo, 2)
        cuenta_repo.update(cuenta_id, {"balance_actual": deuda_nueva})

        resultado["cargo_aplicado"] = True
        resultado["deuda_nueva"] = deuda_nueva
        resultado["mensaje"] = (
            f"Cargo de administración de ${costo:,.2f} aplicado por no "
            f"alcanzar el mínimo de uso de ${minimo:,.2f}."
        )
    elif resultado["alcanza_minimo"]:
        resultado["mensaje"] = "Mínimo de uso alcanzado. Sin cargo de administración."

    return resultado
