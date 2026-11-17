"""Pruebas de edición/eliminación de registros y del presupuesto con cierre.

Verifica:
- Editar o eliminar un gasto/ingreso corrige el balance de su cuenta
  (en tarjeta de crédito corrige la deuda).
- Gastos planeados: añadir, quitar, marcar "se gastó" / "no se hizo".
- Resumen del período: disponible = límite - gastado - planeado.
- Cierre del período: solo cuando terminó, una sola vez, calcula ahorro,
  gastos nuevos y reclama el premio de la masmorra en semanas.
- La sección Resumen ya no permite cambiar el perfil (solo Personaje).
- La vista Presupuesto funciona con clics (añadir, confirmar, cerrar,
  editar y eliminar movimientos).

Se ejecuta como script:  uv run python tests/test_presupuesto_registros.py
"""

import os
import sys
import tempfile
from datetime import date, timedelta

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_presupuesto.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import flet as ft

from src.database import init_db
from src.repositories import cuenta_repo, gasto_repo, ingreso_repo
from src.services import (
    agregar_planeado,
    avanzar_periodo,
    cerrar_periodo,
    configurar_tarjeta,
    crear_cuenta,
    definir_presupuesto_base,
    definir_presupuesto_general,
    editar_gasto,
    editar_ingreso,
    eliminar_gasto,
    eliminar_ingreso,
    inicio_periodo,
    listar_planeados,
    marcar_planeado_gastado,
    marcar_planeado_omitido,
    obtener_cierre,
    obtener_cuenta,
    obtener_puntos,
    quitar_planeado,
    registrar_gasto,
    registrar_ingreso,
    resumen_periodo,
)
from src.ui.views import configuracion, presupuesto, resumen

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    # La consola de Windows (cp1252) no imprime emojis ni flechas.
    seguro = str(detalle).encode("ascii", "replace").decode()
    nombre_seguro = str(nombre).encode("ascii", "replace").decode()
    print(f"[{estado}] {nombre_seguro}" + (f" -> {seguro}" if detalle else ""))


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


class Evt:
    def __init__(self, control=None):
        self.control = control


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


def _texto_boton(btn):
    for attr in ("content", "text", "label"):
        valor = getattr(btn, attr, None)
        if isinstance(valor, str) and valor:
            return valor
    return ""


def botones(raiz, texto):
    return [b for b in caminar(raiz)
            if isinstance(b, ft.Button) and _texto_boton(b) == texto]


def main():
    init_db()
    hoy = date.today()
    lunes_actual = inicio_periodo("semanal", hoy)
    lunes_pasado = avanzar_periodo("semanal", lunes_actual, -1)
    domingo_pasado = lunes_pasado + timedelta(days=6)

    # ---------- Datos base ----------
    cuenta_id = crear_cuenta("Débito", "cuenta", "MXN", 5000.0)
    tarjeta_id = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20, tasa_interes_mensual=3.5,
                       limite_credito_maximo=20000.0)
    definir_presupuesto_general(400.0, "semanal")
    definir_presupuesto_base("Comida Fuera", 400.0)

    # ---------- Editar / eliminar gastos ----------
    g = registrar_gasto(cuenta_id, "Comida Fuera", 200.0)
    check("Gasto en cuenta resta del saldo",
          obtener_cuenta(cuenta_id)["balance_actual"] == 4800.0)
    editar_gasto(g["id"], monto=350.0, descripcion="comida cara")
    gasto_editado = gasto_repo.get_by_id(g["id"])
    check("Editar gasto ajusta el saldo (200 -> 350)",
          obtener_cuenta(cuenta_id)["balance_actual"] == 4650.0
          and gasto_editado["monto"] == 350.0
          and gasto_editado["descripcion"] == "comida cara")
    editar_gasto(g["id"], categoria="Supermercado")
    check("Editar solo la categoría conserva el monto",
          gasto_repo.get_by_id(g["id"])["categoria"] == "Supermercado"
          and gasto_repo.get_by_id(g["id"])["monto"] == 350.0)
    eliminar_gasto(g["id"])
    check("Eliminar gasto devuelve el saldo",
          obtener_cuenta(cuenta_id)["balance_actual"] == 5000.0
          and gasto_repo.get_by_id(g["id"]) is None)

    gt = registrar_gasto(tarjeta_id, "Tecnología", 500.0)
    check("Gasto en tarjeta sube la deuda",
          obtener_cuenta(tarjeta_id)["balance_actual"] == 500.0)
    editar_gasto(gt["id"], monto=300.0)
    check("Editar gasto de tarjeta corrige la deuda (500 -> 300)",
          obtener_cuenta(tarjeta_id)["balance_actual"] == 300.0)
    eliminar_gasto(gt["id"])
    check("Eliminar gasto de tarjeta baja la deuda a 0",
          obtener_cuenta(tarjeta_id)["balance_actual"] == 0.0)

    try:
        editar_gasto(9999, monto=10.0)
        check("Editar gasto inexistente lanza error", False)
    except ValueError:
        check("Editar gasto inexistente lanza error", True)
    try:
        g2 = registrar_gasto(cuenta_id, "Personal", 100.0)
        editar_gasto(g2["id"], monto=-5)
        check("Editar con monto <= 0 lanza error", False)
    except ValueError:
        check("Editar con monto <= 0 lanza error", True)
    eliminar_gasto(g2["id"])

    # ---------- Editar / eliminar ingresos ----------
    ing = registrar_ingreso("Sueldo", 1000.0, tipo="sueldo_recurrente",
                            frecuencia="quincenal", dia_cobro=15,
                            cuenta_id=cuenta_id)
    check("Ingreso suma al saldo",
          obtener_cuenta(cuenta_id)["balance_actual"] == 6000.0)
    editar_ingreso(ing["id"], monto=800.0, dia_cobro=20)
    ing_editado = ingreso_repo.get_by_id(ing["id"])
    check("Editar ingreso ajusta saldo y día de cobro",
          obtener_cuenta(cuenta_id)["balance_actual"] == 5800.0
          and ing_editado["dia_cobro"] == 20
          and ing_editado["frecuencia"] == "quincenal")
    eliminar_ingreso(ing["id"])
    check("Eliminar ingreso revierte la suma",
          obtener_cuenta(cuenta_id)["balance_actual"] == 5000.0
          and ingreso_repo.get_by_id(ing["id"]) is None)

    ing2 = registrar_ingreso("Venta", 300.0)  # sin cuenta
    editar_ingreso(ing2["id"], monto=450.0)
    check("Editar ingreso sin cuenta no rompe nada",
          ingreso_repo.get_by_id(ing2["id"])["monto"] == 450.0)
    eliminar_ingreso(ing2["id"])

    # ---------- Gastos planeados ----------
    p1 = agregar_planeado("semanal", "Comida Fuera", 120.0, "tacos viernes")
    p2 = agregar_planeado("semanal", "Supermercado", 200.0)
    agregar_planeado("mensual", "Tecnología", 999.0)  # otro período
    pendientes = listar_planeados("semanal", lunes_actual, estado="planeado")
    check("Planeados: se listan solo los del período semanal",
          len(pendientes) == 2, f"{len(pendientes)} planeados")

    r = resumen_periodo("semanal", lunes_actual)
    check("Resumen: disponible = límite - gastado - planeado",
          r["limite"] == 400.0 and r["planeado"] == 320.0
          and r["disponible"] == 80.0,
          f"limite={r['limite']} planeado={r['planeado']} "
          f"disponible={r['disponible']}")

    quitar_planeado(p2["id"])
    check("Quitar planeado libera el disponible",
          resumen_periodo("semanal", lunes_actual)["disponible"] == 280.0)

    try:
        agregar_planeado("semanal", "Personal", 0)
        check("Planeado con monto 0 lanza error", False)
    except ValueError:
        check("Planeado con monto 0 lanza error", True)

    # Confirmar "se gastó": registra gasto real y descuenta del saldo
    saldo_antes = obtener_cuenta(cuenta_id)["balance_actual"]
    hecho = marcar_planeado_gastado(p1["id"], cuenta_id)
    check("'Se gastó' registra el gasto real y baja el saldo",
          obtener_cuenta(cuenta_id)["balance_actual"] == saldo_antes - 120.0
          and hecho["gasto"]["categoria"] == "Comida Fuera")
    check("El planeado queda confirmado",
          listar_planeados("semanal", lunes_actual,
                           estado="gastado")[0]["id"] == p1["id"])
    try:
        marcar_planeado_gastado(p1["id"], cuenta_id)
        check("No se puede confirmar dos veces el mismo planeado", False)
    except ValueError:
        check("No se puede confirmar dos veces el mismo planeado", True)
    eliminar_gasto(hecho["gasto"]["id"])  # limpieza para el cierre de abajo

    # ---------- Cierre del período ----------
    try:
        cerrar_periodo("semanal", lunes_actual)
        check("No se puede cerrar un período que no ha terminado", False)
    except ValueError as err:
        check("No se puede cerrar un período que no ha terminado", True,
              str(err)[:40])

    # Semana pasada: gasto de 300 (250 planeado + 50 nuevo) con límite 400
    g_plan = agregar_planeado("semanal", "Comida Fuera", 250.0,
                              inicio=lunes_pasado)
    marcar_planeado_gastado(g_plan["id"], cuenta_id)  # fecha = domingo pasado
    registrar_gasto(cuenta_id, "Comida Fuera", 50.0,  # gasto no planeado
                    fecha=domingo_pasado.isoformat())
    p_omitido = agregar_planeado("semanal", "Personal", 80.0,
                                 inicio=lunes_pasado)

    puntos_antes = obtener_puntos()
    cierre = cerrar_periodo("semanal", lunes_pasado)
    check("Cierre: resultado ahorro (300 gastado de 400)",
          cierre["resultado"] == "ahorro" and cierre["ahorro"] == 100.0,
          f"ahorro={cierre['ahorro']}")
    check("Cierre: distingue planeado de gastos nuevos",
          cierre["planeados_total"] == 250.0
          and cierre["nuevos_total"] == 50.0,
          f"planeado={cierre['planeados_total']} nuevos={cierre['nuevos_total']}")
    check("Cierre: el planeado pendiente quedó como 'no se hizo'",
          listar_planeados("semanal", lunes_pasado,
                           estado="omitido")[0]["id"] == p_omitido["id"])
    check("Cierre semanal derrotada reclama el premio de la masmorra",
          len(cierre["premios"]) == 1
          and obtener_puntos() == puntos_antes + 50,
          f"+{obtener_puntos() - puntos_antes} pts")

    repetido = cerrar_periodo("semanal", lunes_pasado)
    check("El cierre es idempotente (no duplica ni da puntos otra vez)",
          repetido["ya_existia"] and repetido["premios"] == []
          and obtener_puntos() == puntos_antes + 50)

    # Mes pasado excedido: límite mensual = 400*52/12 ≈ 1733.33
    mes_pasado = avanzar_periodo("mensual", inicio_periodo("mensual", hoy), -1)
    registrar_gasto(tarjeta_id, "Tecnología", 2000.0,
                    fecha=mes_pasado.replace(day=10).isoformat())
    cierre_mes = cerrar_periodo("mensual", mes_pasado)
    check("Cierre mensual excedido no da premio ni rompe",
          cierre_mes["resultado"] == "excedido"
          and cierre_mes["premios"] == []
          and cierre_mes["nuevos_total"] == 2000.0,
          f"ahorro={cierre_mes['ahorro']}")
    eliminar_gasto(gasto_repo.execute_query(
        "SELECT id FROM gastos WHERE monto = 2000")[0]["id"])

    # ---------- Resumen ya no cambia el perfil ----------
    page = MockPage()
    refrescos = []

    def refresh(destino=None):
        refrescos.append(destino or "actual")

    v_res = resumen.build(page, refresh)
    txt_res = textos(v_res)
    check("Resumen sigue mostrando el dashboard del perfil activo",
          any("Dashboard del perfil" in t for t in txt_res))
    check("Resumen ya NO tiene botones para cambiar el perfil",
          not botones(v_res, "Activar")
          and any("Configuración" in t for t in txt_res))
    v_cfg = configuracion.build(page, refresh)
    check("El perfil solo se cambia en Configuración (3 inactivos)",
          len(botones(v_cfg, "Activar")) == 3,
          f"{len(botones(v_cfg, 'Activar'))} botones")

    # ---------- Vista Presupuesto (clics UI) ----------
    estado = {}
    vista = presupuesto.build(page, refresh, estado)
    txt = textos(vista)
    check("Presupuesto muestra límite/gastado/planeado/disponible",
          all(any(k in t for t in txt)
              for k in ("Límite", "Gastado", "Planeado", "Disponible")))
    check("Presupuesto inicia en la semana actual",
          estado["tipo"] == "semanal"
          and estado["inicio"] == lunes_actual.isoformat())

    # Añadir planeado con clic
    campos = [c for c in caminar(vista) if isinstance(c, ft.TextField)]
    monto_field = next(c for c in campos if c.label == "Monto")
    monto_field.value = "60"
    botones(vista, "Añadir")[0].on_click(Evt())
    nuevos = listar_planeados("semanal", lunes_actual, estado="planeado")
    check("Clic en 'Añadir' crea el gasto planeado",
          len(nuevos) == 1 and nuevos[0]["monto"] == 60.0)

    # Navegar a la semana pasada con la flecha
    atras = next(b for b in caminar(vista)
                 if isinstance(b, ft.IconButton)
                 and b.tooltip == "Período anterior")
    atras.on_click(Evt())
    check("Flecha atrás navega a la semana pasada",
          estado["inicio"] == lunes_pasado.isoformat())

    # Cerrar la semana siguiente (ya cerrada arriba) muestra el resultado
    vista_pasada = presupuesto.build(page, refresh, estado)
    txt_pasada = textos(vista_pasada)
    check("Semana cerrada muestra su resultado",
          any("Cerrado con ahorro" in t for t in txt_pasada),
          str([t for t in txt_pasada if "Cerrado" in t]))

    # Semana actual (sin cerrar): movimientos editables/eliminables
    estado["inicio"] = lunes_actual.isoformat()
    g_ui = registrar_gasto(cuenta_id, "Personal", 90.0,
                           descripcion="farmacia")
    vista2 = presupuesto.build(page, refresh, estado)
    txt2 = textos(vista2)
    check("Movimientos lista el gasto real de la semana",
          any("farmacia" in t for t in txt2))
    edits = [b for b in caminar(vista2)
             if isinstance(b, ft.IconButton) and b.tooltip == "Editar"]
    n_dialogos = len(page.dialogos)
    edits[0].on_click(Evt())
    check("Lápiz abre el diálogo de edición",
          len(page.dialogos) == n_dialogos + 1)
    dlg_edit = page.dialogos[-1]
    monto_edit = next(c for c in caminar(dlg_edit)
                      if isinstance(c, ft.TextField) and c.label == "Monto")
    monto_edit.value = "45"
    botones(dlg_edit, "Guardar cambios")[0].on_click(Evt())
    # Saldo: 5000 - 250 (planeado sem. pasada) - 50 (nuevo) - 45 (este) = 4655
    check("Guardar edición corrige monto y saldo",
          gasto_repo.get_by_id(g_ui["id"])["monto"] == 45.0
          and obtener_cuenta(cuenta_id)["balance_actual"] == 4655.0,
          f"saldo={obtener_cuenta(cuenta_id)['balance_actual']}")

    eliminar = [b for b in caminar(vista2)
                if isinstance(b, ft.IconButton) and b.tooltip == "Eliminar"]
    eliminar[0].on_click(Evt())
    dlg_del = page.dialogos[-1]
    botones(dlg_del, "Eliminar")[0].on_click(Evt())
    # Saldo: 4655 + 45 (se repone el gasto eliminado) = 4700
    check("Eliminar desde la UI borra el gasto y repone el saldo",
          gasto_repo.get_by_id(g_ui["id"]) is None
          and obtener_cuenta(cuenta_id)["balance_actual"] == 4700.0,
          f"saldo={obtener_cuenta(cuenta_id)['balance_actual']}")

    # Cerrar período desde la UI (semana pasada ya cerrada: probar mensual)
    estado["tipo"] = "mensual"
    estado["inicio"] = avanzar_periodo(
        "mensual", inicio_periodo("mensual", hoy), -1).isoformat()
    # Ya se cerró arriba (excedido): el panel lo refleja
    vista_mes = presupuesto.build(page, refresh, estado)
    check("Mes cerrado muestra resultado excedido",
          any("excedido" in t for t in textos(vista_mes)))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
