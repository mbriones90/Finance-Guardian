"""Servicio de registro de gastos.

Reglas:
- En una cuenta normal el gasto reduce el saldo disponible.
- En una tarjeta de crédito el gasto aumenta la deuda.
- Si el gasto es en USD se guarda el monto original y su equivalente en pesos.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.repositories import cuenta_repo, gasto_repo, tarjeta_repo
from src.services.convertidor import convertir_a_pesos


def registrar_gasto(
    cuenta_id: int,
    categoria: str,
    monto: float,
    moneda: str = "MXN",
    descripcion: str = "",
    fecha: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra un gasto, actualiza el balance y devuelve el gasto + alertas."""
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto del gasto debe ser mayor que cero.")
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")

    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")

    monto_pesos = convertir_a_pesos(monto, moneda)
    fecha = fecha or date.today().isoformat()

    gasto_id = gasto_repo.create(
        {
            "cuenta_id": cuenta_id,
            "categoria": categoria,
            "descripcion": (descripcion or "").strip(),
            "monto": monto,
            "moneda": (moneda or "MXN").upper(),
            "fecha": fecha,
            "convertido_a_pesos": monto_pesos,
        }
    )

    balance_previo = float(cuenta["balance_actual"])
    if cuenta["tipo"] == "cuenta":
        nuevo_balance = round(balance_previo - monto_pesos, 2)
    else:
        # Tarjeta de crédito: la deuda sube.
        nuevo_balance = round(balance_previo + monto_pesos, 2)
    cuenta_repo.update(cuenta_id, {"balance_actual": nuevo_balance})

    alertas = _evaluar_alertas_tarjeta(cuenta_id, cuenta["tipo"], nuevo_balance)

    return {
        "id": gasto_id,
        "cuenta_id": cuenta_id,
        "categoria": categoria,
        "monto": monto,
        "moneda": (moneda or "MXN").upper(),
        "convertido_a_pesos": monto_pesos,
        "fecha": fecha,
        "balance_nuevo": nuevo_balance,
        "alertas": alertas,
    }


def _evaluar_alertas_tarjeta(
    cuenta_id: int, tipo: str, deuda: float
) -> List[str]:
    alertas: List[str] = []
    if tipo != "tarjeta_credito":
        return alertas
    reglas = tarjeta_repo.get_by_cuenta(cuenta_id)
    if not reglas:
        return alertas
    limite = reglas.get("limite_credito_maximo")
    if limite:
        uso = deuda / float(limite) * 100 if limite > 0 else 0
        if uso >= 100:
            alertas.append("Límite de crédito excedido.")
        elif uso >= 90:
            alertas.append(f"Uso del crédito al {uso:.0f}% del límite.")
    return alertas


def _efecto_en_balance(tipo_cuenta: str, pesos: float) -> float:
    """Delta que un gasto aplica al balance: resta en cuenta, suma en tarjeta."""
    return -pesos if tipo_cuenta == "cuenta" else pesos


def editar_gasto(
    gasto_id: int,
    categoria: Optional[str] = None,
    monto: Optional[float] = None,
    moneda: Optional[str] = None,
    descripcion: Optional[str] = None,
    fecha: Optional[str] = None,
) -> Dict[str, Any]:
    """Edita un gasto existente corrigiendo el balance de su cuenta.

    Revierte el efecto del gasto anterior y aplica el nuevo, así el
    saldo (o la deuda, si es tarjeta) siempre cuadra con los registros.
    La cuenta del gasto no se puede cambiar (borra y vuelve a registrar).
    """
    gasto = gasto_repo.get_by_id(gasto_id)
    if not gasto:
        raise ValueError(f"No existe el gasto con id {gasto_id}.")
    cuenta = cuenta_repo.get_by_id(gasto["cuenta_id"])
    if not cuenta:
        raise ValueError("La cuenta del gasto ya no existe.")

    nueva_categoria = (categoria if categoria is not None
                       else gasto["categoria"] or "").strip()
    if not nueva_categoria:
        raise ValueError("La categoría es obligatoria.")
    nuevo_monto = float(monto) if monto is not None else float(gasto["monto"])
    if nuevo_monto <= 0:
        raise ValueError("El monto del gasto debe ser mayor que cero.")
    nueva_moneda = (moneda or gasto["moneda"] or "MXN").upper()
    nueva_fecha = (fecha or gasto["fecha"]).strip()
    nueva_descripcion = (descripcion if descripcion is not None
                         else gasto["descripcion"] or "").strip()
    nuevos_pesos = convertir_a_pesos(nuevo_monto, nueva_moneda)

    # Balance: quita el efecto viejo y aplica el nuevo.
    delta = (_efecto_en_balance(cuenta["tipo"], nuevos_pesos)
             - _efecto_en_balance(cuenta["tipo"], float(gasto["convertido_a_pesos"])))
    balance_nuevo = round(float(cuenta["balance_actual"]) + delta, 2)

    gasto_repo.update(gasto_id, {
        "categoria": nueva_categoria,
        "monto": nuevo_monto,
        "moneda": nueva_moneda,
        "descripcion": nueva_descripcion,
        "fecha": nueva_fecha,
        "convertido_a_pesos": nuevos_pesos,
    })
    cuenta_repo.update(cuenta["id"], {"balance_actual": balance_nuevo})

    return {
        "id": gasto_id,
        "cuenta_id": cuenta["id"],
        "categoria": nueva_categoria,
        "monto": nuevo_monto,
        "moneda": nueva_moneda,
        "convertido_a_pesos": nuevos_pesos,
        "fecha": nueva_fecha,
        "balance_nuevo": balance_nuevo,
    }


def eliminar_gasto(gasto_id: int) -> bool:
    """Elimina un gasto y revierte su efecto en el balance de la cuenta."""
    gasto = gasto_repo.get_by_id(gasto_id)
    if not gasto:
        raise ValueError(f"No existe el gasto con id {gasto_id}.")
    cuenta = cuenta_repo.get_by_id(gasto["cuenta_id"])
    if cuenta:
        delta = -_efecto_en_balance(cuenta["tipo"],
                                    float(gasto["convertido_a_pesos"]))
        cuenta_repo.update(cuenta["id"], {
            "balance_actual": round(float(cuenta["balance_actual"]) + delta, 2)
        })
    return gasto_repo.delete(gasto_id)


def listar_gastos(
    cuenta_id: Optional[int] = None, desde: Optional[str] = None, hasta: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lista gastos, opcionalmente por cuenta y rango de fechas (ISO)."""
    if cuenta_id is not None:
        return gasto_repo.get_by_cuenta(cuenta_id)

    query = "SELECT * FROM gastos"
    params: list = []
    condiciones = []
    if desde:
        condiciones.append("fecha >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("fecha <= ?")
        params.append(hasta)
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY fecha DESC"
    return gasto_repo.execute_query(query, tuple(params))
