"""Suscripciones y gastos fijos generales (luz, internet, Netflix, etc.).

Son GLOBALES para toda la app: no pertenecen a ningún perfil de pago,
aunque los perfiles sí las consideran al calcular el dinero disponible.

Cada suscripción tiene un día de cobro del mes y una cuenta de la que
se descuenta. Los periodos soportados son ``mensual`` y ``anual``
(el anual se prorratea como monto/12 al medir impacto mensual).
"""

import calendar
from datetime import date
from typing import Any, Dict, List, Optional

from src.repositories import BaseRepository, cuenta_repo
from src.services.convertidor import convertir_a_pesos

_repo = BaseRepository("suscripciones")
PERIODOS_VALIDOS = {"mensual", "anual"}


def agregar_suscripcion(
    nombre: str,
    monto: float,
    moneda: str = "MXN",
    dia_cobro: int = 1,
    periodo: str = "mensual",
    cuenta_id: int = None,
    descripcion: str = "",
    activa: bool = True,
) -> int:
    """Registra una suscripción recurrente global."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre de la suscripción es obligatorio.")
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero.")
    if periodo not in PERIODOS_VALIDOS:
        raise ValueError(f"Periodo inválido: {periodo!r}. Usa {sorted(PERIODOS_VALIDOS)}.")
    if not 1 <= int(dia_cobro) <= 31:
        raise ValueError("El día de cobro debe estar entre 1 y 31.")
    if cuenta_id is None or not cuenta_repo.get_by_id(cuenta_id):
        raise ValueError("Debe indicarse una cuenta válida para el cobro.")

    return _repo.create(
        {
            "nombre": nombre,
            "monto": monto,
            "moneda": (moneda or "MXN").upper(),
            "dia_cobro": int(dia_cobro),
            "periodo": periodo,
            "cuenta_id": cuenta_id,
            "activa": 1 if activa else 0,
        }
    )


def editar_suscripcion(suscripcion_id: int, datos: Dict[str, Any]) -> bool:
    """Edita campos de una suscripción (nombre, monto, moneda, día, periodo, cuenta)."""
    permitidos = {"nombre", "monto", "moneda", "dia_cobro", "periodo", "cuenta_id", "activa"}
    filtro = {k: v for k, v in datos.items() if k in permitidos}
    if not filtro:
        return False
    return _repo.update(suscripcion_id, filtro)


def eliminar_suscripcion(suscripcion_id: int) -> bool:
    return _repo.delete(suscripcion_id)


def set_activa(suscripcion_id: int, activa: bool) -> bool:
    """Activa o desactiva sin borrar (ideal para cancelaciones temporales)."""
    return _repo.update(suscripcion_id, {"activa": 1 if activa else 0})


def listar_suscripciones(solo_activas: bool = True) -> List[Dict[str, Any]]:
    if solo_activas:
        return _repo.execute_query("SELECT * FROM suscripciones WHERE activa = 1 ORDER BY dia_cobro")
    return _repo.get_all()


def costo_mensual_pesos(suscripcion: Dict[str, Any]) -> float:
    """Costo mensual equivalente en pesos (el anual se divide entre 12)."""
    monto_pesos = convertir_a_pesos(suscripcion["monto"], suscripcion["moneda"])
    if suscripcion.get("periodo") == "anual":
        return round(monto_pesos / 12, 2)
    return round(monto_pesos, 2)


def total_mensual_pesos(solo_activas: bool = True) -> float:
    """Suma del impacto mensual en pesos de todas las suscripciones."""
    total = sum(costo_mensual_pesos(s) for s in listar_suscripciones(solo_activas))
    return round(total, 2)


def _fecha_cobro_en_mes(dia_cobro: int, year: int, month: int) -> date:
    ultimo = calendar.monthrange(year, month)[1]
    return date(year, month, min(int(dia_cobro), ultimo))


def cobros_del_mes(year: int, month: int, solo_activas: bool = True) -> List[Dict[str, Any]]:
    """Lista los cobros estimados de un mes concreto, ordenados por día."""
    cobros = []
    for s in listar_suscripciones(solo_activas):
        fecha = _fecha_cobro_en_mes(s["dia_cobro"], year, month)
        cobros.append({
            "id": s["id"],
            "nombre": s["nombre"],
            "fecha_cobro": fecha.isoformat(),
            "dia_cobro": s["dia_cobro"],
            "monto": s["monto"],
            "moneda": s["moneda"],
            "monto_pesos": convertir_a_pesos(s["monto"], s["moneda"]),
            "costo_mensual_pesos": costo_mensual_pesos(s),
            "periodo": s["periodo"],
            "cuenta_id": s["cuenta_id"],
        })
    cobros.sort(key=lambda c: c["fecha_cobro"])
    return cobros


def impacto_en_semana(lunes: date, solo_activas: bool = True) -> List[Dict[str, Any]]:
    """Suscripciones que caen dentro de la semana (lunes a domingo).

    Recorre los 7 días de la semana y considera cobros cuyo día del mes
    coincida, incluyendo los casos en que la semana cruza dos meses.
    """
    if isinstance(lunes, str):
        lunes = date.fromisoformat(lunes)
    lunes = lunes_de(lunes)
    dias = {lunes + __import__("datetime").timedelta(days=i) for i in range(7)}
    impacto = []
    for s in listar_suscripciones(solo_activas):
        dia_cobro = int(s["dia_cobro"])
        for d in dias:
            ultimo = calendar.monthrange(d.year, d.month)[1]
            if d.day == min(dia_cobro, ultimo):
                impacto.append({
                    "id": s["id"],
                    "nombre": s["nombre"],
                    "fecha_cobro": d.isoformat(),
                    "monto": s["monto"],
                    "moneda": s["moneda"],
                    "monto_pesos": convertir_a_pesos(s["monto"], s["moneda"]),
                    "cuenta_id": s["cuenta_id"],
                })
                break
    impacto.sort(key=lambda c: c["fecha_cobro"])
    return impacto


def lunes_de(fecha: Optional[date] = None) -> date:
    """Devuelve el lunes de la semana a la que pertenece `fecha`."""
    fecha = fecha or date.today()
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    return fecha - __import__("datetime").timedelta(days=fecha.weekday())
