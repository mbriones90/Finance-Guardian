"""Pruebas del calendario de pagos (servicio + vista).

Se ejecuta como script:  uv run python tests/test_calendario.py
"""

import os
import sys
import tempfile
from datetime import date, timedelta

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_calendario.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import flet as ft

from src.database import init_db
from src.services import (
    agregar_suscripcion,
    configurar_tarjeta,
    crear_cuenta,
    definir_presupuesto_base,
    definir_presupuesto_general,
    distribucion_gastos,
    eventos_de_semana,
    eventos_del_mes,
    obtener_presupuesto_general,
    obtener_puntos,
    reclamar_puntos_semanales,
    registrar_gasto,
    registrar_ingreso,
    resumen_mes,
    CATEGORIAS_GASTO,
    PUNTOS_SEMANA_DERROTADA,
)
from src.ui.views import calendario

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


class MockPage:
    def __init__(self):
        self.overlay = []
        self.dialogos = []

    def show_dialog(self, dlg):
        self.dialogos.append(dlg)

    def update(self):
        pass

    def run_task(self, handler, *args):
        import asyncio
        return asyncio.run(handler(*args))


def _hijos(control):
    if hasattr(control, "controls") and control.controls:
        yield from control.controls
    contenido = getattr(control, "content", None)
    if contenido is not None and isinstance(contenido, ft.Control):
        yield contenido


def caminar(raiz):
    pila = [raiz]
    while pila:
        c = pila.pop()
        yield c
        pila.extend(_hijos(c))


def textos(raiz):
    return [c.value for c in caminar(raiz)
            if isinstance(c, ft.Text) and isinstance(c.value, str)]


class Evt:
    def __init__(self, control=None):
        self.control = control


def main():
    init_db()

    # Datos: tarjeta (corte 15, pago 5) y dos suscripciones (día 10 y 31)
    cuenta_id = crear_cuenta("Nómina", "cuenta", "MXN", 5000.0)
    tarjeta_id = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20)
    agregar_suscripcion("Netflix", 200, "MXN", 10, "mensual", cuenta_id)
    agregar_suscripcion("Dominio web", 1200, "MXN", 31, "anual", cuenta_id)

    # ---------- Servicio: vista mensual ----------
    eventos = eventos_del_mes(2026, 11)
    fechas = {(e["fecha"], e["tipo"]) for e in eventos}
    check("Mes tiene corte (15) y pago (5) de tarjeta",
          ("2026-11-15", "corte_tarjeta") in fechas
          and ("2026-11-05", "pago_tarjeta") in fechas)
    check("Mes tiene cobro Netflix día 10",
          ("2026-11-10", "suscripcion") in fechas)
    check("Día 31 se ajusta al 30 en noviembre",
          ("2026-11-30", "suscripcion") in fechas,
          str(sorted(f for f, _ in fechas)))
    check("Montos en pesos de suscripciones",
          abs(sum(e["monto"] for e in eventos if e["tipo"] == "suscripcion")
              - 1400.0) < 1e-9)

    # ---------- Servicio: resumen del mes ----------
    res = resumen_mes(2026, 11)
    check("Resumen: 1 corte, 1 pago, 2 cobros, $1400",
          res["cortes"] == 1 and res["pagos_tarjeta"] == 1
          and res["cobros_suscripcion"] == 2
          and res["total_suscripciones"] == 1400.0, str(res))

    # ---------- Servicio: vista semanal (cruza de mes) ----------
    lunes = date(2026, 11, 30)  # semana 30 nov - 6 dic
    eventos_sem = eventos_de_semana(lunes)
    fechas_sem = {(e["fecha"], e["tipo"]) for e in eventos_sem}
    check("Semana que cruza mes incluye cobro ajustado (30 nov)",
          ("2026-11-30", "suscripcion") in fechas_sem)
    check("Semana que cruza mes incluye pago tarjeta (5 dic)",
          ("2026-12-05", "pago_tarjeta") in fechas_sem)
    check("Semana NO incluye eventos fuera de rango (10 dic)",
          ("2026-12-10", "suscripcion") not in fechas_sem)

    # ---------- Servicio: validación ----------
    try:
        eventos_del_mes(2026, 13)
        check("Mes 13 rechazado", False)
    except ValueError:
        check("Mes 13 rechazado", True)

    # ---------- Vista: construye en ambos modos ----------
    page = MockPage()
    refrescos = []

    def refresh(destino=None):
        refrescos.append(destino or "actual")

    estado = {}
    vista = calendario.build(page, refresh, estado)
    check("Vista mensual por defecto", estado["modo"] == "mensual")
    txt = textos(vista)
    # En móvil el mes muestra puntos de color; el detalle va en el tooltip.
    tooltips = [c.tooltip for c in caminar(vista)
                if isinstance(getattr(c, "tooltip", None), str)]
    check("Vista mensual marca los días con eventos (punto + tooltip)",
          any("Netflix" in t or "Invex" in t for t in tooltips))
    check("Vista mensual muestra leyenda",
          any("Corte de tarjeta" in t for t in txt))

    # ---------- Vista: cambiar a semanal con el SegmentedButton ----------
    seg = next(c for c in caminar(vista) if isinstance(c, ft.SegmentedButton))
    seg.selected = ["semanal"]  # el control real actualiza selected antes del handler
    seg.on_change(Evt(control=seg))
    check("Toggle a semanal dispara refresh", bool(refrescos))
    check("Estado cambió a semanal", estado["modo"] == "semanal")

    vista_sem = calendario.build(page, refresh, estado)
    txt_sem = textos(vista_sem)
    check("Vista semanal muestra la lista de días (layout móvil)",
          all(any(t.startswith(d) for t in txt_sem)
              for d in ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")))

    # ---------- Vista: navegación en el tiempo ----------
    estado2 = {"modo": "mensual", "ancla": None}
    vista2 = calendario.build(page, refresh, estado2)
    btn_next = next(c for c in caminar(vista2)
                    if isinstance(c, ft.IconButton)
                    and c.icon == ft.Icons.CHEVRON_RIGHT)
    btn_next.on_click(Evt())
    hoy = date.today()
    mes_sig = hoy.year * 12 + hoy.month  # +1 mes en meses absolutos
    esperado = f"{mes_sig // 12}-{mes_sig % 12 + 1:02d}-01"
    check("Navegar al mes siguiente", estado2["ancla"] == esperado,
          estado2["ancla"])

    btn_hoy = next(c for c in caminar(vista2)
                   if isinstance(c, ft.TextButton))
    btn_hoy.on_click(Evt())
    check("Botón Hoy regresa a la fecha actual", estado2["ancla"] is None)

    # Semanal: navegar una semana atrás
    estado3 = {"modo": "semanal", "ancla": None}
    vista3 = calendario.build(page, refresh, estado3)
    btn_prev = next(c for c in caminar(vista3)
                    if isinstance(c, ft.IconButton)
                    and c.icon == ft.Icons.CHEVRON_LEFT)
    btn_prev.on_click(Evt())
    esperado_sem = (hoy - timedelta(weeks=1)).isoformat()
    check("Navegar una semana atrás", estado3["ancla"] == esperado_sem,
          estado3["ancla"])

    # ---------- Sueldo quincenal: día inicial 15 → cobra 15 y 30 ----------
    registrar_ingreso("Sueldo", 7000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", dia_cobro=15, cuenta_id=cuenta_id)
    eventos_sueldo = [e for e in eventos_del_mes(2026, 11)
                      if e["tipo"] == "cobro_sueldo"]
    check("Sueldo quincenal cobra 15 y 30 de noviembre",
          [e["fecha"] for e in eventos_sueldo]
          == ["2026-11-15", "2026-11-30"],
          str([e["fecha"] for e in eventos_sueldo]))
    eventos_feb = [e for e in eventos_del_mes(2027, 2)
                   if e["tipo"] == "cobro_sueldo"]
    check("Febrero: segunda quincena se ajusta al último día (28)",
          [e["fecha"] for e in eventos_feb] == ["2027-02-15", "2027-02-28"],
          str([e["fecha"] for e in eventos_feb]))
    check("Cobro sueldo trae monto",
          eventos_sueldo[0]["monto"] == 7000.0)
    res = resumen_mes(2026, 11)
    check("Resumen incluye sueldos del mes (2 × 7000)",
          res["cobros_sueldo"] == 2 and res["total_sueldos"] == 14000.0)

    # ---------- Presupuesto general: equivalencias ----------
    g = definir_presupuesto_general(4000, "mensual")
    check("4000 mensual ~ 2000 quincenal y 923.08 semanal",
          g["quincenal"] == 2000.0 and abs(g["semanal"] - 923.08) < 0.01,
          str(g))
    g2 = definir_presupuesto_general(1000, "semanal")
    check("1000 semanal ~ 4333.33 mensual (todos coinciden)",
          abs(g2["mensual"] - 4333.33) < 0.01
          and abs(g2["quincenal"] - 2166.67) < 0.01, str(g2))

    # ---------- Validación: categorías sin pasarse del semanal ----------
    definir_presupuesto_base("Alimentos", 600.0)
    try:
        definir_presupuesto_base("Salidas", 500.0)  # 1100 > 1000
        check("Reparto que excede el general es rechazado", False)
    except ValueError as e:
        check("Reparto que excede el general es rechazado",
              "Te pasas del presupuesto" in str(e), str(e))
    definir_presupuesto_base("Salidas", 400.0)  # 1000 exacto: sí pasa
    check("Reparto exacto al límite sí se permite", True)

    # ---------- Masmorra: premio semanal por no salirse ----------
    hoy = date.today()
    lunes_pasado = hoy - timedelta(days=hoy.weekday() + 7)
    fecha_en_semana = (lunes_pasado + timedelta(days=2)).isoformat()
    registrar_gasto(cuenta_id, "Alimentos", 100.0, fecha=fecha_en_semana)
    puntos_antes = obtener_puntos()
    premios = reclamar_puntos_semanales(hoy=hoy)
    check("Semana derrotada otorga premio",
          len(premios) >= 1
          and premios[0]["puntos"] == PUNTOS_SEMANA_DERROTADA,
          str(premios))
    check("Puntos sumados", obtener_puntos()
          == puntos_antes + PUNTOS_SEMANA_DERROTADA * len(premios))
    check("Premio es idempotente (no se duplica)",
          reclamar_puntos_semanales(hoy=hoy) == [])

    # ---------- Distribución de gastos ----------
    dist = distribucion_gastos()
    check("Distribución incluye todas las categorías del catálogo",
          len(dist["categorias"]) == len(CATEGORIAS_GASTO))
    alimentos = next(c for c in dist["categorias"]
                     if c["categoria"] == "Alimentos")
    # El gasto fue la semana pasada: 100 repartidos en 2 semanas = 50/sem.
    check("Alimentos: real mes = 100, proyección semana = 50 (promedio 2 sem)",
          alimentos["real_mes"] == 100.0
          and alimentos["proy_semana"] == 50.0, str(alimentos))
    check("Proyecciones 1 año = 52× y 10 años = 520× la semanal",
          alimentos["proy_ano"] == round(alimentos["proy_semana"] * 52, 2)
          and alimentos["proy_diez_anos"] == round(alimentos["proy_semana"] * 520, 2))
    check("Categoría sin gastos usa presupuesto base (Salidas 400)",
          next(c for c in dist["categorias"] if c["categoria"] == "Salidas")
          ["proy_semana"] == 400.0)

    # ---------- Vista: panel de la masmorra + leyenda con sueldo ----------
    estado_v = {"modo": "semanal", "ancla": None}
    vista_m = calendario.build(page, refresh, estado_v)
    txt_m = textos(vista_m)
    check("Panel 'La Masmorra del Presupuesto' visible",
          any("Masmorra" in t for t in txt_m))
    check("Leyenda incluye cobro de sueldo",
          any("Cobro de sueldo" in t for t in txt_m))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
