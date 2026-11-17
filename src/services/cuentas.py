"""Servicio de cuentas y tarjetas.

Convención de `balance_actual`:
- tipo ``cuenta``: saldo disponible (positivo = dinero que tienes).
- tipo ``tarjeta_credito``: deuda actual (positivo = dinero que debes).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.repositories import cuenta_repo
from src.services.convertidor import convertir_a_pesos

TIPOS_VALIDOS = {"cuenta", "tarjeta_credito"}


def crear_cuenta(
    nombre: str,
    tipo: str,
    moneda: str = "MXN",
    balance_inicial: float = 0.0,
) -> int:
    """Crea una cuenta o tarjeta y devuelve su id."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre de la cuenta no puede estar vacío.")
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo inválido: {tipo!r}. Usa 'cuenta' o 'tarjeta_credito'.")

    return cuenta_repo.create(
        {
            "nombre": nombre,
            "tipo": tipo,
            "moneda": (moneda or "MXN").upper(),
            "balance_actual": float(balance_inicial),
            "fecha_creacion": datetime.now().isoformat(),
        }
    )


def listar_cuentas(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista cuentas, opcionalmente filtradas por tipo."""
    if tipo:
        return cuenta_repo.get_by_tipo(tipo)
    return cuenta_repo.get_all()


def obtener_cuenta(cuenta_id: int) -> Optional[Dict[str, Any]]:
    return cuenta_repo.get_by_id(cuenta_id)


def actualizar_balance(cuenta_id: int, nuevo_balance: float) -> bool:
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    return cuenta_repo.update(cuenta_id, {"balance_actual": round(float(nuevo_balance), 2)})


def ajustar_balance(cuenta_id: int, delta: float) -> float:
    """Suma `delta` al balance de la cuenta y devuelve el nuevo balance."""
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    nuevo = round(float(cuenta["balance_actual"]) + float(delta), 2)
    cuenta_repo.update(cuenta_id, {"balance_actual": nuevo})
    return nuevo


def editar_cuenta(cuenta_id: int, nombre: Optional[str] = None,
                  balance: Optional[float] = None) -> Dict[str, Any]:
    """Edita el nombre y/o el balance de una cuenta o tarjeta.

    El balance es un ajuste manual directo (útil para corregir el saldo
    inicial registrado en la Dimensión 1).
    """
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")
    cambios = {}
    if nombre is not None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre de la cuenta no puede estar vacío.")
        cambios["nombre"] = nombre
    if balance is not None:
        cambios["balance_actual"] = round(float(balance), 2)
    if cambios:
        cuenta_repo.update(cuenta_id, cambios)
    return cuenta_repo.get_by_id(cuenta_id)


def eliminar_cuenta(cuenta_id: int) -> bool:
    """Elimina una cuenta solo si no tiene registros ligados.

    Para no romper el historial ni los saldos, una cuenta con gastos,
    ingresos, suscripciones o reglas de tarjeta no se puede borrar:
    primero elimina esos registros.
    """
    cuenta = cuenta_repo.get_by_id(cuenta_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")

    from src.repositories import (
        gasto_repo,
        ingreso_repo,
        suscripcion_repo,
        tarjeta_repo,
    )
    if gasto_repo.get_by_cuenta(cuenta_id):
        raise ValueError("La cuenta tiene gastos registrados: elimínalos "
                         "primero para no perder el historial.")
    if any(i.get("cuenta_id") == cuenta_id for i in ingreso_repo.get_all()):
        raise ValueError("La cuenta tiene ingresos registrados: elimínalos "
                         "primero.")
    if any(s["cuenta_id"] == cuenta_id
           for s in suscripcion_repo.get_all()):
        raise ValueError("La cuenta tiene suscripciones ligadas: elimínalas "
                         "primero en la Dimensión 7.")
    if tarjeta_repo.get_by_cuenta(cuenta_id):
        raise ValueError("Es una tarjeta configurada: primero quita sus "
                         "reglas y gastos.")
    return cuenta_repo.delete(cuenta_id)


def _balance_en_pesos(cuenta: Dict[str, Any]) -> float:
    return convertir_a_pesos(cuenta["balance_actual"], cuenta["moneda"])


def efectivo_total_pesos() -> float:
    """Suma del saldo de todas las cuentas (sin tarjetas de crédito)."""
    total = sum(
        _balance_en_pesos(c) for c in cuenta_repo.get_by_tipo("cuenta")
    )
    return round(total, 2)


def deuda_total_pesos() -> float:
    """Suma de la deuda de todas las tarjetas de crédito."""
    total = sum(
        _balance_en_pesos(c) for c in cuenta_repo.get_by_tipo("tarjeta_credito")
    )
    return round(total, 2)


def patrimonio_neto_pesos() -> float:
    """Efectivo disponible menos deuda de tarjetas."""
    return round(efectivo_total_pesos() - deuda_total_pesos(), 2)
