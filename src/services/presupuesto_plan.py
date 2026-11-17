"""Gastos planeados y cierre del período de presupuesto.

Flujo de la sección Presupuesto:
1. Durante la semana (o el mes) anotas **gastos planeados**: compras que
   piensas hacer. Se pueden añadir o quitar libremente.
2. El panel muestra el límite del período, lo ya gastado, lo planeado
   pendiente y lo que queda **disponible** (límite - gastado - planeado).
3. Cuando el período **termina**, confirmas el cierre:
   - cada gasto planeado se marca como "se gastó" (registra el gasto real)
     o "no se hizo";
   - lo que se gastó de más aparece como **gastos nuevos** (no planeados);
   - si gastaste menos que el límite, la diferencia es **ahorro**.
   El cierre se guarda una sola vez por período.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from src.repositories import BaseRepository, gasto_repo
from src.services.gastos import registrar_gasto
from src.services.presupuesto_semanal import (
    estado_mes,
    estado_semana,
    lunes_de,
    reclamar_puntos_semanales,
)

TIPOS_PERIODO = ("semanal", "mensual")

_planos = BaseRepository("gastos_planeados")
_cierres = BaseRepository("cierres_presupuesto")


# ---------------------------------------------------------------------------
# Utilidades de período
# ---------------------------------------------------------------------------

def inicio_periodo(tipo: str, fecha: Optional[date] = None) -> date:
    """Inicio del período: el lunes de la semana o el día 1 del mes."""
    tipo = _validar_tipo(tipo)
    if fecha is None:
        fecha = date.today()
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    if tipo == "semanal":
        return lunes_de(fecha)
    return fecha.replace(day=1)


def rango_periodo(tipo: str, inicio: Optional[date] = None) -> tuple:
    """Rango (desde ISO, hasta ISO) inclusive del período."""
    inicio = inicio_periodo(tipo, inicio)
    if tipo == "semanal":
        fin = inicio + timedelta(days=6)
    else:
        fin = inicio.replace(day=calendar.monthrange(inicio.year,
                                                     inicio.month)[1])
    return inicio.isoformat(), fin.isoformat()


def avanzar_periodo(tipo: str, inicio: Optional[date] = None, n: int = 1) -> date:
    """Se desplaza n períodos (negativo = períodos pasados)."""
    inicio = inicio_periodo(tipo, inicio)
    n = int(n)
    if tipo == "semanal":
        return inicio + timedelta(weeks=n)
    mes = inicio.month - 1 + n
    year = inicio.year + mes // 12
    month = mes % 12 + 1
    return date(year, month, 1)


def periodo_terminado(tipo: str, inicio: Optional[date] = None,
                      hoy: Optional[date] = None) -> bool:
    """True si el período ya acabó (su último día es anterior a hoy)."""
    hoy = hoy or date.today()
    _, hasta = rango_periodo(tipo, inicio)
    return date.fromisoformat(hasta) < hoy


def _validar_tipo(tipo: str) -> str:
    tipo = (tipo or "").strip().lower()
    if tipo not in TIPOS_PERIODO:
        raise ValueError(f"Tipo de período inválido: {tipo!r}. "
                         f"Usa {list(TIPOS_PERIODO)}.")
    return tipo


# ---------------------------------------------------------------------------
# Gastos planeados
# ---------------------------------------------------------------------------

def agregar_planeado(tipo: str, categoria: str, monto: float,
                     descripcion: str = "",
                     inicio: Optional[date] = None) -> Dict[str, Any]:
    """Añade una compra planeada al período (semana o mes)."""
    tipo = _validar_tipo(tipo)
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto planeado debe ser mayor que cero.")
    inicio = inicio_periodo(tipo, inicio)

    planeado_id = _planos.create({
        "tipo_periodo": tipo,
        "periodo_inicio": inicio.isoformat(),
        "categoria": categoria,
        "descripcion": (descripcion or "").strip(),
        "monto": round(monto, 2),
        "estado": "planeado",
        "fecha_creacion": datetime.now().isoformat(),
    })
    return _planos.get_by_id(planeado_id)


def listar_planeados(tipo: str, inicio: Optional[date] = None,
                     estado: Optional[str] = None) -> List[Dict[str, Any]]:
    """Planeados del período, opcionalmente filtrados por estado."""
    tipo = _validar_tipo(tipo)
    inicio = inicio_periodo(tipo, inicio)
    query = ("SELECT * FROM gastos_planeados WHERE tipo_periodo = ? "
             "AND periodo_inicio = ?")
    params: list = [tipo, inicio.isoformat()]
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    query += " ORDER BY fecha_creacion"
    return _planos.execute_query(query, tuple(params))


def quitar_planeado(planeado_id: int) -> bool:
    """Quita una compra planeada (solo si sigue pendiente)."""
    planeado = _planos.get_by_id(planeado_id)
    if not planeado:
        raise ValueError(f"No existe el gasto planeado con id {planeado_id}.")
    if planeado["estado"] != "planeado":
        raise ValueError("Solo se pueden quitar gastos aún pendientes.")
    return _planos.delete(planeado_id)


def marcar_planeado_gastado(planeado_id: int, cuenta_id: int,
                            moneda: str = "MXN") -> Dict[str, Any]:
    """Confirma que la compra planeada se hizo: registra el gasto real.

    El gasto queda con la fecha de hoy (o del último día del período si
    este ya terminó, para que cuente en el período correcto).
    """
    planeado = _planeado_pendiente(planeado_id)
    hoy = date.today()
    _, hasta = rango_periodo(planeado["tipo_periodo"],
                             date.fromisoformat(planeado["periodo_inicio"]))
    fecha = min(hoy, date.fromisoformat(hasta)).isoformat()
    gasto = registrar_gasto(cuenta_id, planeado["categoria"],
                            float(planeado["monto"]), moneda=moneda,
                            descripcion=planeado["descripcion"] or "",
                            fecha=fecha)
    _planos.update(planeado_id, {"estado": "gastado"})
    return {"planeado_id": planeado_id, "gasto": gasto}


def marcar_planeado_omitido(planeado_id: int) -> bool:
    """Confirma que la compra planeada al final no se hizo."""
    planeado = _planeado_pendiente(planeado_id)
    return _planos.update(planeado["id"], {"estado": "omitido"})


def _planeado_pendiente(planeado_id: int) -> Dict[str, Any]:
    planeado = _planos.get_by_id(planeado_id)
    if not planeado:
        raise ValueError(f"No existe el gasto planeado con id {planeado_id}.")
    if planeado["estado"] != "planeado":
        raise ValueError("Ese gasto planeado ya fue confirmado.")
    return planeado


# ---------------------------------------------------------------------------
# Resumen del período (límite vs gastado vs planeado)
# ---------------------------------------------------------------------------

def resumen_periodo(tipo: str, inicio: Optional[date] = None) -> Dict[str, Any]:
    """Estado del período: límite, gasto real, planeado y disponible.

    ``disponible`` = límite - gastado - planeado pendiente: lo que de
    verdad te queda si haces todas las compras que planeaste.
    """
    tipo = _validar_tipo(tipo)
    inicio = inicio_periodo(tipo, inicio)
    desde, hasta = rango_periodo(tipo, inicio)

    if tipo == "semanal":
        est = estado_semana(inicio)
        limite, gastado = est["limite_total"], est["gastado_total"]
        semaforo = est["semaforo_total"]
    else:
        est = estado_mes(inicio.year, inicio.month)
        limite, gastado = est["limite"], est["gastado"]
        semaforo = est["semaforo"]

    pendientes = listar_planeados(tipo, inicio, estado="planeado")
    planeado = round(sum(float(p["monto"]) for p in pendientes), 2)
    disponible = round(limite - gastado - planeado, 2)

    return {
        "tipo": tipo,
        "inicio": desde,
        "fin": hasta,
        "limite": round(limite, 2),
        "gastado": round(gastado, 2),
        "planeado": planeado,
        "pendientes": len(pendientes),
        "disponible": disponible,
        "porcentaje": round((gastado + planeado) / limite * 100, 1)
        if limite > 0 else None,
        "semaforo": semaforo,
        "terminado": periodo_terminado(tipo, inicio),
        "cerrado": obtener_cierre(tipo, inicio) is not None,
    }


# ---------------------------------------------------------------------------
# Cierre del período
# ---------------------------------------------------------------------------

def obtener_cierre(tipo: str, inicio: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """El cierre guardado del período, o None si aún no se confirma."""
    tipo = _validar_tipo(tipo)
    inicio = inicio_periodo(tipo, inicio)
    filas = _cierres.execute_query(
        "SELECT * FROM cierres_presupuesto WHERE tipo_periodo = ? "
        "AND periodo_inicio = ?",
        (tipo, inicio.isoformat()),
    )
    return filas[0] if filas else None


def cerrar_periodo(tipo: str, inicio: Optional[date] = None,
                   hoy: Optional[date] = None) -> Dict[str, Any]:
    """Confirma el cierre del período terminado.

    - Los planeados que quedaron pendientes se marcan como "no se hizo"
      (los que sí se hicieron ya debiste confirmarlos con "Se gastó").
    - ``nuevos_total`` = gasto real que no venía de un planeado.
    - ``resultado``: ``ahorro`` si gastaste menos que el límite,
      ``excedido`` si te pasaste, ``justo`` si quedó en ceros.
    - Si es semanal, también reclama el premio de la masmorra (50 pts)
      cuando la semana se derrotó.

    Es idempotente: un período cerrado no se puede volver a cerrar.
    """
    tipo = _validar_tipo(tipo)
    inicio = inicio_periodo(tipo, inicio)
    hoy = hoy or date.today()

    existente = obtener_cierre(tipo, inicio)
    if existente:
        return {**existente, "premios": [], "ya_existia": True}
    if not periodo_terminado(tipo, inicio, hoy):
        _, hasta = rango_periodo(tipo, inicio)
        raise ValueError(
            f"El período aún no termina (acaba el {hasta}). "
            "Confirma el cierre cuando acabe.")

    resumen = resumen_periodo(tipo, inicio)
    # Los planeados pendientes quedan como "no se hizo".
    for p in listar_planeados(tipo, inicio, estado="planeado"):
        _planos.update(p["id"], {"estado": "omitido"})

    gastado_confirmado = round(sum(
        float(p["monto"])
        for p in listar_planeados(tipo, inicio, estado="gastado")
    ), 2)
    nuevos = round(max(0.0, resumen["gastado"] - gastado_confirmado), 2)
    ahorro = round(resumen["limite"] - resumen["gastado"], 2)
    if ahorro > 0.005:
        resultado = "ahorro"
    elif ahorro < -0.005:
        resultado = "excedido"
    else:
        resultado = "justo"

    _cierres.create({
        "tipo_periodo": tipo,
        "periodo_inicio": inicio.isoformat(),
        "limite": resumen["limite"],
        "gastado": resumen["gastado"],
        "ahorro": ahorro,
        "planeados_total": gastado_confirmado,
        "nuevos_total": nuevos,
        "resultado": resultado,
        "fecha_cierre": hoy.isoformat(),
    })

    premios = reclamar_puntos_semanales(ultimas=1, hoy=hoy) if tipo == "semanal" else []

    cierre = obtener_cierre(tipo, inicio)
    return {**cierre, "premios": premios, "ya_existia": False}


def listar_gastos_periodo(tipo: str, inicio: Optional[date] = None) -> List[Dict[str, Any]]:
    """Gastos reales registrados dentro del período (para editar/borrar)."""
    desde, hasta = rango_periodo(tipo, inicio)
    return gasto_repo.execute_query(
        "SELECT * FROM gastos WHERE fecha >= ? AND fecha <= ? "
        "ORDER BY fecha DESC, id DESC",
        (desde, hasta),
    )
