"""Presupuesto semanal: "¿me alcanza para salir / comer afuera?".

Reglas:
- La semana inicia **lunes** y termina domingo.
- Hay un **presupuesto base** por categorías (ej. salidas, comida afuera,
  transporte) que se **repite** en cada semana nueva.
- Cada semana se puede **editar individualmente** sin afectar el base
  (ej. "esta semana tendré evento, subo salidas").
- Se puede **navegar** a semanas pasadas y futuras (todo se calcula desde
  los gastos reales registrados en ese rango de fechas).
- Semáforo por categoría y total:
    verde  <= 70 % del límite
    amarillo  70–100 %
    rojo   > 100 %
"""

import calendar
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.database import get_connection
from src.repositories import BaseRepository, gasto_repo

_repo = BaseRepository("presupuestos_semanales")
_base = BaseRepository("presupuestos_base")
_general = BaseRepository("presupuesto_general")
_premios = BaseRepository("premios_semana")

# Equivalencias de periodo: un año = 52 semanas = 12 meses = 24 quincenas.
SEMANAS_POR_MES = 52 / 12
SEMANAS_POR_QUINCENA = 52 / 24
PERIODOS_GENERAL = ("mensual", "quincenal", "semanal")

# Premio semanal por "derrotar la masmorra": cerrar la semana sin salirse
# del presupuesto.
PUNTOS_SEMANA_DERROTADA = 50


# ---------------------------------------------------------------------------
# Utilidades de semana
# ---------------------------------------------------------------------------

def lunes_de(fecha: Optional[date] = None) -> date:
    """Devuelve el lunes de la semana a la que pertenece `fecha`."""
    if fecha is None:
        fecha = date.today()
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    return fecha - timedelta(days=fecha.weekday())


def rango_semana(lunes: Optional[date] = None) -> tuple:
    """Rango (inicio ISO, fin ISO) de la semana del lunes indicado."""
    lunes = lunes_de(lunes)
    fin = lunes + timedelta(days=6)
    return lunes.isoformat(), fin.isoformat()


def avanzar_semanas(lunes: Optional[date] = None, n: int = 1) -> date:
    """Se desplaza n semanas (negativo = semanas pasadas)."""
    return lunes_de(lunes) + timedelta(weeks=int(n))


def listar_semanas(cantidad: int = 5, desplazamiento: int = -2) -> List[Dict[str, Any]]:
    """Lista de semanas alrededor de la actual (para navegación atrás/adelante)."""
    semanas = []
    for i in range(int(desplazamiento), int(desplazamiento) + int(cantidad)):
        lunes = avanzar_semanas(None, i)
        inicio, fin = rango_semana(lunes)
        etiqueta = "actual" if i == 0 else ("pasada" if i < 0 else "futura")
        semanas.append({
            "lunes": lunes.isoformat(),
            "inicio": inicio,
            "fin": fin,
            "tipo": etiqueta,
            "desplazamiento": i,
        })
    return semanas


# ---------------------------------------------------------------------------
# Presupuesto general (mensual/quincenal/semanal — todos equivalentes)
# ---------------------------------------------------------------------------

def definir_presupuesto_general(monto: float, periodo: str = "mensual") -> Dict[str, Any]:
    """Define el presupuesto general y devuelve sus equivalencias.

    El usuario puede iniciar desde un presupuesto mensual, quincenal o
    semanal: internamente todos coinciden (año = 52 semanas = 12 meses
    = 24 quincenas) y las categorías no pueden pasarse del semanal.
    """
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El presupuesto general debe ser mayor que cero.")
    periodo = (periodo or "").strip().lower()
    if periodo not in PERIODOS_GENERAL:
        raise ValueError(f"Periodo inválido: {periodo!r}. Usa {list(PERIODOS_GENERAL)}.")

    from datetime import datetime
    existente = _general.get_by_id(1)
    datos = {"periodo": periodo, "monto": round(monto, 2),
             "fecha_actualizacion": datetime.now().isoformat()}
    if existente:
        _general.update(1, datos)
    else:
        _general.create({"id": 1, **datos})
    return obtener_presupuesto_general()


def obtener_presupuesto_general() -> Optional[Dict[str, Any]]:
    """Presupuesto general con sus equivalencias semanal/quincenal/mensual."""
    fila = _general.get_by_id(1)
    if not fila:
        return None
    monto = float(fila["monto"])
    periodo = fila["periodo"]
    if periodo == "mensual":
        semanal = monto / SEMANAS_POR_MES
    elif periodo == "quincenal":
        semanal = monto / SEMANAS_POR_QUINCENA
    else:
        semanal = monto
    return {
        "periodo": periodo,
        "monto": round(monto, 2),
        "semanal": round(semanal, 2),
        "quincenal": round(semanal * SEMANAS_POR_QUINCENA, 2),
        "mensual": round(semanal * SEMANAS_POR_MES, 2),
    }


def suma_categorias_base(excluir_categoria: Optional[str] = None) -> float:
    """Suma semanal de las categorías del presupuesto base."""
    total = 0.0
    for fila in listar_presupuesto_base():
        if excluir_categoria and fila["categoria"] == excluir_categoria:
            continue
        total += float(fila["monto_limite_base"])
    return round(total, 2)


# ---------------------------------------------------------------------------
# Presupuesto base (plantilla que se repite)
# ---------------------------------------------------------------------------

def definir_presupuesto_base(categoria: str, monto_limite: float) -> None:
    """Crea o actualiza el límite base de una categoría (upsert).

    Si hay presupuesto general definido, la suma de categorías no puede
    superar el equivalente semanal (todos los periodos coinciden).
    """
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    monto_limite = float(monto_limite)
    if monto_limite < 0:
        raise ValueError("El límite no puede ser negativo.")

    general = obtener_presupuesto_general()
    if general:
        suma = suma_categorias_base(excluir_categoria=categoria) + monto_limite
        if suma > general["semanal"] + 0.01:
            raise ValueError(
                f"Te pasas del presupuesto: ${suma:,.2f} en categorías supera "
                f"el límite semanal de ${general['semanal']:,.2f} "
                f"(general {general['periodo']}: ${general['monto']:,.2f})."
            )

    existente = _base.execute_query(
        "SELECT id FROM presupuestos_base WHERE categoria = ?", (categoria,)
    )
    if existente:
        _base.update(existente[0]["id"], {"monto_limite_base": round(monto_limite, 2)})
    else:
        _base.create({"categoria": categoria, "monto_limite_base": round(monto_limite, 2)})


def listar_presupuesto_base() -> List[Dict[str, Any]]:
    return _base.execute_query("SELECT * FROM presupuestos_base ORDER BY categoria")


def eliminar_presupuesto_base(categoria: str) -> bool:
    filas = _base.execute_query(
        "SELECT id FROM presupuestos_base WHERE categoria = ?", (categoria,)
    )
    return bool(filas) and _base.delete(filas[0]["id"])


# ---------------------------------------------------------------------------
# Presupuesto por semana
# ---------------------------------------------------------------------------

def _filas_semana(lunes: date) -> List[Dict[str, Any]]:
    return _repo.execute_query(
        "SELECT * FROM presupuestos_semanales WHERE semana_inicio = ? ORDER BY categoria",
        (lunes.isoformat(),),
    )


def inicializar_semana(lunes: Optional[date] = None) -> bool:
    """Copia el presupuesto base a la semana si aún no tiene filas.

    Devuelve True si se inicializó (había base y la semana estaba vacía).
    """
    lunes = lunes_de(lunes)
    if _filas_semana(lunes):
        return False
    base = listar_presupuesto_base()
    if not base:
        return False
    conn = get_connection()
    try:
        cur = conn.cursor()
        for fila in base:
            cur.execute(
                """INSERT INTO presupuestos_semanales
                   (semana_inicio, semana_fin, categoria, monto_limite_semana, monto_gastado)
                   VALUES (?, ?, ?, ?, 0)""",
                (lunes.isoformat(), (lunes + timedelta(days=6)).isoformat(),
                 fila["categoria"], round(float(fila["monto_limite_base"]), 2)),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def editar_limite_semana(lunes: Optional[date], categoria: str, nuevo_limite: float) -> None:
    """Edita (o crea) el límite de una categoría SOLO para esa semana."""
    lunes = lunes_de(lunes)
    categoria = (categoria or "").strip()
    nuevo_limite = float(nuevo_limite)
    if nuevo_limite < 0:
        raise ValueError("El límite no puede ser negativo.")
    inicio, fin = rango_semana(lunes)

    filas = [f for f in _filas_semana(lunes) if f["categoria"] == categoria]
    if filas:
        _repo.update(filas[0]["id"], {"monto_limite_semana": round(nuevo_limite, 2)})
    else:
        _repo.create({
            "semana_inicio": lunes.isoformat(),
            "semana_fin": fin,
            "categoria": categoria,
            "monto_limite_semana": round(nuevo_limite, 2),
            "monto_gastado": 0.0,
        })


def _gastos_por_categoria(inicio: str, fin: str) -> Dict[str, float]:
    filas = gasto_repo.execute_query(
        """SELECT categoria, COALESCE(SUM(convertido_a_pesos), 0) AS total
           FROM gastos WHERE fecha >= ? AND fecha <= ? GROUP BY categoria""",
        (inicio, fin),
    )
    return {f["categoria"]: round(float(f["total"]), 2) for f in filas}


def _semaforo(gastado: float, limite: float) -> str:
    if limite <= 0:
        return "verde" if gastado <= 0 else "rojo"
    pct = gastado / limite
    if pct > 1.0:
        return "rojo"
    if pct > 0.7:
        return "amarillo"
    return "verde"


def estado_semana(lunes: Optional[date] = None) -> Dict[str, Any]:
    """Estado completo de la semana: límites, gasto real, restante y semáforo.

    Si la semana no tiene filas y existe presupuesto base, se inicializa
    automáticamente (la base se repite). Los montos gastados se recalculan
    desde los gastos reales registrados en el rango de la semana.
    """
    lunes = lunes_de(lunes)
    inicializar_semana(lunes)
    inicio, fin = rango_semana(lunes)
    gastos = _gastos_por_categoria(inicio, fin)

    categorias: List[Dict[str, Any]] = []
    limite_total = gastado_total = 0.0
    filas = _filas_semana(lunes)

    conn = get_connection()
    try:
        cur = conn.cursor()
        for f in filas:
            limite = round(float(f["monto_limite_semana"]), 2)
            gastado = round(gastos.get(f["categoria"], 0.0), 2)
            restante = round(limite - gastado, 2)
            limite_total += limite
            gastado_total += gastado
            categorias.append({
                "categoria": f["categoria"],
                "limite": limite,
                "gastado": gastado,
                "restante": restante,
                "porcentaje": round(gastado / limite * 100, 1) if limite > 0 else None,
                "semaforo": _semaforo(gastado, limite),
            })
            # Persiste el gasto calculado como snapshot de reporte
            cur.execute(
                "UPDATE presupuestos_semanales SET monto_gastado = ? WHERE id = ?",
                (gastado, f["id"]),
            )
        conn.commit()
    finally:
        conn.close()

    restante_total = round(limite_total - gastado_total, 2)
    return {
        "lunes": lunes.isoformat(),
        "inicio": inicio,
        "fin": fin,
        "categorias": categorias,
        "limite_total": round(limite_total, 2),
        "gastado_total": round(gastado_total, 2),
        "restante_total": restante_total,
        "porcentaje_total": round(gastado_total / limite_total * 100, 1) if limite_total > 0 else None,
        "semaforo_total": _semaforo(gastado_total, limite_total),
    }


def puedo_gastar(lunes: Optional[date] = None, monto: float = 0.0) -> Dict[str, Any]:
    """Responde "¿me alcanza para salir/comer afuera esta semana?".

    Compara el monto contra lo que queda de presupuesto semanal:
    - verde: sí alcanza y deja colchón (>= 20 % del límite total).
    - amarillo: alcanza, pero dejaría menos del 20 %.
    - rojo: no alcanza (superaría lo que queda de la semana).
    """
    monto = float(monto)
    estado = estado_semana(lunes)
    restante = estado["restante_total"]
    limite = estado["limite_total"]

    despues = round(restante - monto, 2)
    if limite <= 0:
        semaforo, mensaje = "amarillo", "Aún no defines presupuesto para esta semana."
    elif monto > restante:
        semaforo, mensaje = "rojo", (
            f"No alcanza: quedan ${restante:,.2f} y quieres gastar ${monto:,.2f}."
        )
    elif despues < limite * 0.2:
        semaforo, mensaje = "amarillo", (
            f"Alcanza, pero quedarían solo ${despues:,.2f} de ${limite:,.2f}."
        )
    else:
        semaforo, mensaje = "verde", (
            f"Sí alcanza: quedarían ${despues:,.2f} de ${limite:,.2f}."
        )

    return {
        "monto": monto,
        "restante_antes": restante,
        "restante_despues": despues,
        "limite_total": limite,
        "semaforo": semaforo,
        "mensaje": mensaje,
    }


def simular_compra_semanal(
    lunes: Optional[date] = None,
    monto: float = 0.0,
    cuenta_usada_id: int = None,
    pago_mensual_estimado: Optional[float] = None,
) -> Dict[str, Any]:
    """Simulación completa de compra cara con impacto semanal y de deuda.

    Combina:
    - ``puedo_gastar``: impacto en el presupuesto de la semana.
    - ``simular_compra`` (Fase 5): impacto en saldo o deuda de la cuenta,
      con semáforo propio y meses/intereses extra si es tarjeta.

    El semáforo final es el peor de los dos.
    """
    from src.services.simulacion_compra_cara import simular_compra
    from src.repositories import cuenta_repo

    monto = float(monto)
    cuenta = cuenta_repo.get_by_id(cuenta_usada_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_usada_id}.")

    semana = puedo_gastar(lunes, monto)
    compra = simular_compra(
        monto=monto,
        cuenta_usada_id=cuenta_usada_id,
        pago_mensual_estimado=pago_mensual_estimado,
    )

    if cuenta["tipo"] == "cuenta":
        restante_semana_despues = semana["restante_despues"]
    else:
        # Con tarjeta el gasto no sale del bolsillo esta semana.
        restante_semana_despues = semana["restante_antes"]

    orden = {"verde": 0, "amarillo": 1, "rojo": 2}
    semaforo_final = max(semana["semaforo"], compra["semaforo"], key=lambda s: orden[s])
    inicio_semana, _ = rango_semana(lunes)

    return {
        "monto": monto,
        "semana": inicio_semana,
        "presupuesto": semana,
        "compra": compra,
        "restante_semana_despues": restante_semana_despues,
        "semaforo_final": semaforo_final,
        "mensajes": semana["mensaje"] + " " + " ".join(compra["mensajes"]),
    }


# ---------------------------------------------------------------------------
# La Masmorra del Presupuesto: premio semanal por no salirse del plan
# ---------------------------------------------------------------------------

def semana_derrotada(lunes: Optional[date] = None) -> bool:
    """True si la semana tiene presupuesto y el gasto no lo superó."""
    estado = estado_semana(lunes)
    return estado["limite_total"] > 0 and estado["gastado_total"] <= estado["limite_total"]


def premio_reclamado(lunes: Optional[date] = None) -> bool:
    lunes = lunes_de(lunes)
    return bool(_premios.execute_query(
        "SELECT 1 FROM premios_semana WHERE semana_inicio = ?",
        (lunes.isoformat(),),
    ))


def reclamar_puntos_semanales(ultimas: int = 1, hoy: Optional[date] = None) -> List[Dict[str, Any]]:
    """Otorga el premio de las semanas ya cerradas que se derrotaron.

    Por defecto solo se evalúa la semana inmediatamente anterior
    (``ultimas=1``): la masmorra se pelea semana a semana, no se
    regalan puntos retroactivos de semanas viejas. Es idempotente:
    cada semana derrotada se premia una sola vez.
    """
    from src.services import puntos as puntos_svc

    hoy = hoy or date.today()
    lunes_actual = lunes_de(hoy)
    premios: List[Dict[str, Any]] = []
    for i in range(1, ultimas + 1):
        lunes = lunes_actual - timedelta(weeks=i)
        domingo = lunes + timedelta(days=6)
        if domingo >= hoy:
            continue  # la semana aún no termina
        if premio_reclamado(lunes):
            continue
        if not semana_derrotada(lunes):
            continue
        saldo = puntos_svc.ganar_puntos(PUNTOS_SEMANA_DERROTADA)
        _premios.create({
            "semana_inicio": lunes.isoformat(),
            "puntos": PUNTOS_SEMANA_DERROTADA,
            "fecha_otorgado": hoy.isoformat(),
        })
        premios.append({
            "semana_inicio": lunes.isoformat(),
            "puntos": PUNTOS_SEMANA_DERROTADA,
            "puntos_totales": saldo,
        })
    return premios


def estado_mes(year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """Presupuesto mensual: gasto real del mes vs. límite mensual general."""
    hoy = date.today()
    year, month = int(year or hoy.year), int(month or hoy.month)
    ultimo = calendar.monthrange(year, month)[1]
    desde = date(year, month, 1).isoformat()
    hasta = date(year, month, ultimo).isoformat()

    filas = gasto_repo.execute_query(
        "SELECT COALESCE(SUM(convertido_a_pesos), 0) AS total FROM gastos "
        "WHERE fecha >= ? AND fecha <= ?",
        (desde, hasta),
    )
    gastado = round(float(filas[0]["total"]), 2)

    general = obtener_presupuesto_general()
    limite = round(general["mensual"], 2) if general else 0.0
    restante = round(limite - gastado, 2)
    return {
        "year": year,
        "month": month,
        "limite": limite,
        "gastado": gastado,
        "restante": restante,
        "porcentaje": round(gastado / limite * 100, 1) if limite > 0 else None,
        "semaforo": _semaforo(gastado, limite),
    }
