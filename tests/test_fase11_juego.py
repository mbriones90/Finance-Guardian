"""Pruebas de la Fase 11: integración end-to-end (partida completa).

Simula a un usuario real: inicia en la Dimensión 1, completa cada misión
hasta la Dimensión Maestra, editando datos en cualquier momento sin
obstáculos, y verifica toda la app conectada (servicios + UI).

Se ejecuta como script:  uv run python tests/test_fase11_juego.py
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase11.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.repositories import cuenta_repo
from src.services import (
    # progresión RPG
    progreso, obtener_puntos, obtener_personaje, completar_dimension,
    estado_progresion, configurar_personaje,
    desbloquear_armadura, equipar_armadura, equipar_fondo,
    # finanzas
    crear_cuenta, configurar_tarjeta, registrar_ingreso, registrar_gasto,
    definir_presupuesto_base, agregar_suscripcion, simular_compra,
    activar_perfil, asignar_modulos, exportar_todo, ajustar_balance,
    # dashboards
    comparar_perfiles, evaluar_riesgos, estado_semana,
    simular_compra_semanal, listar_perfiles, listar_tablas,
    get_tipo_cambio,
)

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def esperar_error(fn, fragmento):
    try:
        fn()
        return False, "no lanzó error"
    except ValueError as e:
        return fragmento.lower() in str(e).lower(), str(e)
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def completar(n, nivel_esperado):
    payload = completar_dimension(n)
    check(f"D{n} completada -> nivel {nivel_esperado}",
          payload["nivel_nuevo"] == nivel_esperado,
          payload["mensaje"][:60])
    return payload


def main():
    init_db()

    # ================= INICIO =================
    prog = progreso()
    check("Inicio: Guardián nivel 1, Dimensión 1", prog["nivel"] == 1
          and prog["dimension_actual"] == 1)

    ok, det = esperar_error(lambda: completar_dimension(3), "primero completa")
    check("No se puede adelantar al inicio", ok, det)

    # ================= D1: primera cuenta =================
    cuenta_id = crear_cuenta("Cuenta nómina", "cuenta", "MXN", 2000.0)
    check("D1: cuenta creada", cuenta_id > 0)
    completar(1, 2)

    # ================= D2: ingresos =================
    registrar_ingreso("Sueldo", 8000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", cuenta_id=cuenta_id)
    completar(2, 3)

    # ================= D3: gastos =================
    registrar_gasto(cuenta_id, "Comida", 150.0)
    registrar_gasto(cuenta_id, "Transporte", 60.0)
    registrar_gasto(cuenta_id, "Salidas", 200.0)
    completar(3, 4)

    # ---- Edición libre sin obstáculos (datos del D1) ----
    ajustar_balance(cuenta_id, 500.0)  # ajuste manual
    cuenta_repo.update(cuenta_id, {"nombre": "Nómina Banorte"})
    prog = progreso()
    c = cuenta_repo.get_by_id(cuenta_id)
    check("Editar en cualquier momento: cuenta renombrada y ajustada",
          c["nombre"] == "Nómina Banorte" and c["balance_actual"] == 10090.0,
          f"{c['nombre']} {c['balance_actual']}")
    check("La edición NO afecta la progresión", prog["nivel"] == 4,
          f"nivel={prog['nivel']}")

    # ================= D4: primera tarjeta =================
    tarjeta_id = crear_cuenta("Invex Sams", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20)
    completar(4, 5)

    # ================= D5: reglas de tarjetas =================
    configurar_tarjeta(tarjeta_id, 15, 5, 20, tasa_interes_mensual=3.5,
                       limite_credito_maximo=10000.0,
                       minimo_uso_monto=2000.0,
                       costo_admin_si_no_alcance=300.0)
    completar(5, 6)

    # ================= D6: presupuesto =================
    definir_presupuesto_base("Salidas", 600.0)
    definir_presupuesto_base("Comida", 400.0)
    completar(6, 7)

    # ================= D7: suscripciones =================
    agregar_suscripcion("Luz", 800, "MXN", 10, "mensual", cuenta_id)
    agregar_suscripcion("Netflix", 2000, "MXN", 15, "mensual", cuenta_id)
    completar(7, 8)

    # ================= D8: perfil de pago =================
    opt = next(p for p in listar_perfiles() if p["tipo_perfil"] == "optimizado")
    activar_perfil(opt["id"])
    ultimo = completar(8, 8)
    check("D8: Guardián Supremo al completar las 8 dimensiones",
          ultimo["juego_completado"] is True
          and "Guardián Supremo" in ultimo["mensaje"])

    # ================= Iteración: rejugar dimensiones con premio =================
    puntos_antes = obtener_puntos()
    rep = completar_dimension(3)  # repetición: 50*3 pts, 25*3 XP
    check("Rejugar D3 da premio de repetición sin cambiar el nivel",
          rep["repeticion"] and rep["puntos_ganados"] == 150
          and rep["xp_ganada"] == 75 and rep["nivel_nuevo"] == 8)
    rep2 = completar_dimension(3)
    check("Se puede rejugar una y otra vez (iterativo)",
          rep2["repeticion"] and obtener_puntos() == puntos_antes + 300,
          str(obtener_puntos()))

    # Exportar CSV sigue disponible como utilidad
    archivos = exportar_todo()
    check("Exportar 9 CSV funciona", len(archivos) == 9)

    # ================= Estado final RPG =================
    prog = progreso()
    check("8/8 dimensiones, nivel 8",
          prog["dimensiones_completadas"] == 8 and prog["nivel"] == 8
          and prog["juego_completado"])
    check("Puntos = 3600 + 300 (2 repeticiones D3)", obtener_puntos() == 3900,
          str(obtener_puntos()))
    check("XP = 1800 + 150 (repeticiones)", prog["puntos_experiencia"] == 1950)

    # Inventario con puntos ganados
    desbloquear_armadura("verde")
    desbloquear_armadura("azul")
    equipar_armadura("azul")
    equipar_fondo("d13_dimension_maestra")
    configurar_personaje(nombre="Miguel", tipo_cambio=19.50)
    check("Armadura azul equipada y fondo maestro",
          obtener_personaje()["armadura_actual"] == "azul"
          and obtener_personaje()["fondo_actual"] == "d13_dimension_maestra")
    check("Tipo de cambio configurable (19.50)",
          abs(get_tipo_cambio() - 19.50) < 1e-9)
    configurar_personaje(tipo_cambio=18.63)

    # ================= Funciones financieras integradas =================
    comp = comparar_perfiles(tarjeta_id, horizonte=120)
    check("Comparación de perfiles funciona", len(comp) == 4)
    alertas = evaluar_riesgos()
    check("Detección de riesgos funciona", len(alertas) >= 1,
          str([a["tipo"] for a in alertas]))
    semana = estado_semana()
    # Solo cuentan categorías con presupuesto: Comida 150 + Salidas 200 = 350
    check("Presupuesto semanal con gastos reales (solo categorías con presupuesto)",
          semana["gastado_total"] == 350.0, str(semana["gastado_total"]))
    sim_sem = simular_compra_semanal(None, 300.0, cuenta_id)
    check("Simulación semanal integrada", sim_sem["semaforo_final"] in
          ("verde", "amarillo", "rojo"))

    # ================= UI construye con la partida completa =================
    import flet as ft
    from src.ui.views import dimensiones, mision, personaje, resumen

    class MockPage:
        overlay = []

        def show_dialog(self, dlg):
            pass

        def update(self):
            pass

        def run_task(self, handler, *args):
            import asyncio
            asyncio.run(handler(*args))

    from src.ui.views import configuracion

    page = MockPage()
    vistas_ok = True
    for constructor in [
        lambda: dimensiones.build(page, lambda d=None: None, lambda n: None),
        lambda: resumen.build(page, lambda d=None: None),
        lambda: personaje.build(page, lambda d=None: None),
        lambda: configuracion.build(page, lambda d=None: None),
    ] + [lambda d=d: mision.build(page, lambda x=None: None, d, {})
         for d in range(1, 9)]:
        try:
            v = constructor()
            if not isinstance(v, ft.Control):
                vistas_ok = False
        except Exception as e:  # noqa: BLE001
            vistas_ok = False
            print(f"   UI error: {type(e).__name__}: {e}")
    check("Toda la UI construye con la partida completa", vistas_ok)

    mapa = estado_progresion()
    check("Mapa final: 8/8 completadas",
          all(d["completada"] for d in mapa["dimensiones"]))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
