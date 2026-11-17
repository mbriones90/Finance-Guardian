"""Perfiles de pago: Mínimo, Optimizado (líquido), Agresivo y Custom.

Cada perfil define cuánto se destina a pagar las tarjetas cada mes:

- **Mínimo**: paga ``max(monto_fijo, deuda × porcentaje)`` por tarjeta.
  El dashboard muestra cuánto tardaría en liquidar y la fecha del último pago.
- **Optimizado (líquido)**: mínimo + 50 % del excedente del mes
  (ingresos − suscripciones − mínimos de todas las tarjetas).
  Protege la liquidez y considera las suscripciones (globales) primero.
- **Agresivo**: destina todo el dinero disponible por encima de una
  reserva de seguridad (``flujo_minimo_efectivo``), sin tocar las
  suscripciones del mes. Opcionalmente prioriza la tarjeta con mayor tasa.
- **Custom**: usa la misma fórmula del mínimo pero con sus propios
  parámetros, y puede heredar módulos de dashboard de los otros perfiles.

El pago nunca excede ``deuda + interés del mes`` (liquidar de una vez).
"""

from datetime import date
from typing import Any, Dict, List, Optional

from src.repositories import (
    cuenta_repo,
    ingreso_repo,
    perfil_repo,
    suscripcion_repo,
    tarjeta_repo,
)
from src.services.convertidor import convertir_a_pesos
from src.services.proyeccion_deuda import proyectar

# Fracción del excedente mensual que el perfil Optimizado destina a
# pagar deuda extra (el resto queda como liquidez disponible).
EXTRA_OPTIMIZADO = 0.5


# ---------------------------------------------------------------------------
# CRUD de perfiles
# ---------------------------------------------------------------------------

def listar_perfiles() -> List[Dict[str, Any]]:
    return perfil_repo.get_all()


def obtener_perfil(perfil_id: int) -> Optional[Dict[str, Any]]:
    return perfil_repo.get_by_id(perfil_id)


def obtener_perfil_activo() -> Optional[Dict[str, Any]]:
    return perfil_repo.get_activo()


def crear_perfil(
    nombre: str,
    tipo_perfil: str,
    pago_minimo_porcentaje: float = 5.0,
    pago_minimo_monto_fijo: float = 200.0,
    flujo_minimo_efectivo: float = 0.0,
    priorizar_intereses_mayores: int = 0,
) -> int:
    if tipo_perfil not in {"minimo", "optimizado", "agresivo", "custom"}:
        raise ValueError(f"Tipo de perfil inválido: {tipo_perfil!r}")
    return perfil_repo.create(
        {
            "nombre": nombre,
            "tipo_perfil": tipo_perfil,
            "pago_minimo_porcentaje": float(pago_minimo_porcentaje),
            "pago_minimo_monto_fijo": float(pago_minimo_monto_fijo),
            "flujo_minimo_efectivo": float(flujo_minimo_efectivo),
            "priorizar_intereses_mayores": int(priorizar_intereses_mayores),
            "activo": 0,
        }
    )


def actualizar_perfil(perfil_id: int, datos: Dict[str, Any]) -> bool:
    permitidos = {
        "nombre", "pago_minimo_porcentaje", "pago_minimo_monto_fijo",
        "flujo_minimo_efectivo", "priorizar_intereses_mayores",
    }
    filtro = {k: v for k, v in datos.items() if k in permitidos}
    if not filtro:
        return False
    return perfil_repo.update(perfil_id, filtro)


def activar_perfil(perfil_id: int) -> None:
    """Marca un perfil como activo (solo puede haber uno)."""
    if not perfil_repo.get_by_id(perfil_id):
        raise ValueError(f"No existe el perfil con id {perfil_id}.")
    for p in perfil_repo.get_all():
        if p["id"] != perfil_id and p["activo"]:
            perfil_repo.update(p["id"], {"activo": 0})
    perfil_repo.update(perfil_id, {"activo": 1})


# ---------------------------------------------------------------------------
# Cálculo de pagos
# ---------------------------------------------------------------------------

def _rango_mes_actual() -> tuple:
    hoy = date.today()
    import calendar
    ultimo = calendar.monthrange(hoy.year, hoy.month)[1]
    return (
        date(hoy.year, hoy.month, 1).isoformat(),
        date(hoy.year, hoy.month, ultimo).isoformat(),
    )


def _suscripciones_mensuales_pesos() -> float:
    from src.services.suscripciones import total_mensual_pesos
    return total_mensual_pesos()


def _ingresos_del_mes_pesos() -> float:
    desde, hasta = _rango_mes_actual()
    filas = ingreso_repo.execute_query(
        "SELECT COALESCE(SUM(convertido_a_pesos), 0) AS total FROM ingresos "
        "WHERE fecha >= ? AND fecha <= ?",
        (desde, hasta),
    )
    return round(float(filas[0]["total"]), 2)


def _efectivo_total_pesos() -> float:
    total = 0.0
    for c in cuenta_repo.get_by_tipo("cuenta"):
        total += convertir_a_pesos(c["balance_actual"], c["moneda"])
    return round(total, 2)


def pago_minimo_tarjeta(deuda: float, perfil: Dict[str, Any]) -> float:
    """Pago mínimo según el perfil: max(monto fijo, deuda × %)."""
    deuda = float(deuda)
    if deuda <= 0:
        return 0.0
    pct = float(perfil.get("pago_minimo_porcentaje") or 0)
    fijo = float(perfil.get("pago_minimo_monto_fijo") or 0)
    return round(max(fijo, deuda * pct / 100), 2)


def _tarjetas_con_deuda() -> List[Dict[str, Any]]:
    tarjetas = []
    for t in tarjeta_repo.get_activas():
        cuenta = cuenta_repo.get_by_id(t["cuenta_id"])
        if not cuenta:
            continue
        deuda = float(cuenta["balance_actual"])
        if deuda <= 0:
            continue
        tasa = float(t.get("tasa_interes_mensual") or 0)
        tarjetas.append({
            "cuenta_id": t["cuenta_id"],
            "nombre": cuenta["nombre"],
            "moneda": cuenta["moneda"],
            "deuda": deuda,
            "tasa": tasa,
            "deuda_con_interes": round(deuda * (1 + tasa / 100), 2),
        })
    return tarjetas


def calcular_pago_mensual(tarjeta_id: int, perfil_id: Optional[int] = None) -> Dict[str, Any]:
    """Calcula el pago mensual de una tarjeta bajo un perfil.

    Returns:
        Dict con pago_minimo, pago_extra, pago_mensual, contexto del perfil
        (ingresos del mes, suscripciones, reserva, etc.).
    """
    perfil = perfil_repo.get_by_id(perfil_id) if perfil_id else perfil_repo.get_activo()
    if not perfil:
        raise ValueError("No hay perfil de pago configurado o activo.")

    cuenta = cuenta_repo.get_by_id(tarjeta_id)
    if not cuenta or cuenta["tipo"] != "tarjeta_credito":
        raise ValueError("El pago mensual aplica solo a tarjetas de crédito.")
    reglas = tarjeta_repo.get_by_cuenta(tarjeta_id)
    if not reglas:
        raise ValueError("La tarjeta no tiene reglas configuradas.")

    deuda = round(float(cuenta["balance_actual"]), 2)
    tasa = float(reglas.get("tasa_interes_mensual") or 0)
    deuda_con_interes = round(deuda * (1 + tasa / 100), 2)
    tipo = perfil["tipo_perfil"]

    contexto = {
        "perfil_id": perfil["id"],
        "perfil_nombre": perfil["nombre"],
        "tipo_perfil": tipo,
        "deuda": deuda,
        "tasa_interes_mensual": tasa,
        "deuda_con_interes": deuda_con_interes,
    }

    if deuda <= 0:
        contexto.update({"pago_minimo": 0.0, "pago_extra": 0.0, "pago_mensual": 0.0})
        return contexto

    minimo = pago_minimo_tarjeta(deuda, perfil)

    if tipo in ("minimo", "custom"):
        extra = 0.0
    elif tipo == "optimizado":
        # Excedente: ingresos del mes menos suscripciones y los mínimos
        # de TODAS las tarjetas (para no comprometer dinero dos veces).
        suma_minimos = sum(
            pago_minimo_tarjeta(t["deuda"], perfil)
            for t in _tarjetas_con_deuda()
        )
        excedente = max(
            0.0,
            _ingresos_del_mes_pesos()
            - _suscripciones_mensuales_pesos()
            - suma_minimos,
        )
        extra = round(min(excedente * EXTRA_OPTIMIZADO, deuda_con_interes - minimo), 2)
    elif tipo == "agresivo":
        disponible = max(
            0.0,
            _efectivo_total_pesos()
            - float(perfil.get("flujo_minimo_efectivo") or 0)
            - _suscripciones_mensuales_pesos(),
        )
        extra = round(min(disponible, deuda_con_interes - minimo), 2)
    else:
        extra = 0.0

    pago = round(min(minimo + max(0.0, extra), deuda_con_interes), 2)
    contexto.update({
        "pago_minimo": minimo,
        "pago_extra": round(max(0.0, pago - minimo), 2),
        "pago_mensual": pago,
        "efectivo_total": _efectivo_total_pesos(),
        "suscripciones_mes": _suscripciones_mensuales_pesos(),
        "ingresos_mes": _ingresos_del_mes_pesos(),
        "reserva_flujo": float(perfil.get("flujo_minimo_efectivo") or 0),
    })
    return contexto


# ---------------------------------------------------------------------------
# Liquidación por perfil y comparación
# ---------------------------------------------------------------------------

def fecha_liquidacion_por_perfil(
    perfil_id: int,
    tarjeta_id: int,
    horizonte: int = 120,
    guardar: bool = True,
) -> Dict[str, Any]:
    """Calcula el pago del perfil y proyecta hasta liquidar (o agotar horizonte)."""
    calc = calcular_pago_mensual(tarjeta_id, perfil_id)
    perfil = perfil_repo.get_by_id(perfil_id)
    if calc["pago_mensual"] <= 0:
        return {
            "perfil_id": perfil_id,
            "perfil": perfil["nombre"],
            "tipo_perfil": perfil["tipo_perfil"],
            "pago_mensual": 0.0,
            "meses_para_liquidar": 0,
            "fecha_estimada_liquidacion": None,
            "interes_total": 0.0,
            "saldos_por_horizonte": {},
        }

    proy = proyectar(
        tarjeta_id,
        pago_mensual=calc["pago_mensual"],
        meses=horizonte,
        guardar=guardar,
        perfil_id=perfil_id,
    )
    return {
        "perfil_id": perfil_id,
        "perfil": perfil["nombre"],
        "tipo_perfil": perfil["tipo_perfil"],
        "pago_mensual": calc["pago_mensual"],
        "pago_minimo": calc["pago_minimo"],
        "pago_extra": calc["pago_extra"],
        "meses_para_liquidar": proy["meses_para_liquidar"],
        "fecha_estimada_liquidacion": proy["fecha_estimada_liquidacion"],
        "interes_total": proy["interes_total"],
        "saldos_por_horizonte": proy["saldos_por_horizonte"],
    }


def comparar_perfiles(tarjeta_id: int, horizonte: int = 120) -> List[Dict[str, Any]]:
    """Compara lado a lado los 4 perfiles sobre una tarjeta.

    Para cada perfil devuelve pago mensual, meses para liquidar, fecha del
    último pago e interés total (bajo el supuesto de pago constante).
    """
    return [
        fecha_liquidacion_por_perfil(p["id"], tarjeta_id, horizonte)
        for p in perfil_repo.get_all()
    ]


# ---------------------------------------------------------------------------
# Distribución de un presupuesto de pago entre varias tarjetas
# ---------------------------------------------------------------------------

def distribuir_pago_total(
    perfil_id: int, presupuesto_total: float
) -> Dict[str, Any]:
    """Reparte un presupuesto mensual entre todas las tarjetas con deuda.

    Paso 1: asegura el pago mínimo de cada tarjeta.
    Paso 2: el sobrante se asigna a la tarjeta con mayor tasa de interés
    (si el perfil lo prioriza) o a la de mayor deuda.
    """
    perfil = perfil_repo.get_by_id(perfil_id)
    if not perfil:
        raise ValueError("Perfil no encontrado.")
    presupuesto_total = round(float(presupuesto_total), 2)
    if presupuesto_total < 0:
        raise ValueError("El presupuesto no puede ser negativo.")

    tarjetas = _tarjetas_con_deuda()
    asignaciones: List[Dict[str, Any]] = []
    restante = presupuesto_total

    # Paso 1: mínimos
    for t in tarjetas:
        minimo = min(pago_minimo_tarjeta(t["deuda"], perfil), restante)
        asignado = min(minimo, t["deuda_con_interes"])
        asignaciones.append({
            "cuenta_id": t["cuenta_id"],
            "nombre": t["nombre"],
            "deuda": t["deuda"],
            "tasa_interes_mensual": t["tasa"],
            "pago_minimo": asignado,
            "pago_extra": 0.0,
            "pago_total": round(asignado, 2),
        })
        restante = round(restante - asignado, 2)

    # Paso 2: extra según prioridad
    orden = sorted(
        range(len(asignaciones)),
        key=lambda i: (
            -asignaciones[i]["tasa_interes_mensual"]
            if perfil.get("priorizar_intereses_mayores")
            else -asignaciones[i]["deuda"]
        ),
    )
    for i in orden:
        if restante <= 0:
            break
        t = tarjetas[i]
        margen = round(t["deuda_con_interes"] - asignaciones[i]["pago_total"], 2)
        extra = round(min(restante, max(0.0, margen)), 2)
        asignaciones[i]["pago_extra"] = extra
        asignaciones[i]["pago_total"] = round(asignaciones[i]["pago_total"] + extra, 2)
        restante = round(restante - extra, 2)

    total_asignado = round(sum(a["pago_total"] for a in asignaciones), 2)
    return {
        "perfil_id": perfil_id,
        "perfil": perfil["nombre"],
        "presupuesto": presupuesto_total,
        "asignaciones": asignaciones,
        "total_asignado": total_asignado,
        "sobrante": round(presupuesto_total - total_asignado, 2),
    }
