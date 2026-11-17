"""Pruebas de la Fase 7: presupuesto semanal y suscripciones.

Se ejecuta como script:  uv run python tests/test_fase7.py
Usa una base de datos temporal aislada (variable FINANZAS_DB).
"""

import os
import sys
import tempfile
from datetime import date, timedelta

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase7.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.services import (
    crear_cuenta,
    configurar_tarjeta,
    registrar_ingreso,
    registrar_gasto,
    lunes_de_semana,
    rango_semana,
    avanzar_semanas,
    listar_semanas,
    definir_presupuesto_base,
    listar_presupuesto_base,
    editar_limite_semana,
    estado_semana,
    puedo_gastar,
    simular_compra_semanal,
    agregar_suscripcion,
    editar_suscripcion,
    set_activa_suscripcion,
    eliminar_suscripcion,
    listar_suscripciones,
    costo_mensual_pesos,
    total_mensual_pesos,
    cobros_del_mes,
    impacto_en_semana,
)

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def cat(estado, nombre):
    return next(c for c in estado["categorias"] if c["categoria"] == nombre)


def main():
    init_db()

    # ---------- A. Utilidades de semana ----------
    lunes = lunes_de_semana(date(2026, 11, 11))  # miércoles
    check("Lunes de la semana del 11 nov = 9 nov", lunes == date(2026, 11, 9),
          str(lunes))
    inicio, fin = rango_semana(lunes)
    check("Rango semanal lun-dom", inicio == "2026-11-09" and fin == "2026-11-15",
          f"{inicio}..{fin}")
    check("Avanzar 1 semana", avanzar_semanas(lunes, 1) == date(2026, 11, 16))
    check("Retroceder 2 semanas", avanzar_semanas(lunes, -2) == date(2026, 10, 26))
    sem = listar_semanas(cantidad=5, desplazamiento=-2)
    check("Navegación de semanas incluye pasada, actual y futura",
          {s["tipo"] for s in sem} == {"pasada", "actual", "futura"})

    # ---------- B. Presupuesto base ----------
    definir_presupuesto_base("Salidas", 600.0)
    definir_presupuesto_base("Comida", 300.0)
    definir_presupuesto_base("Transporte", 150.0)
    check("Base con 3 categorías", len(listar_presupuesto_base()) == 3)
    definir_presupuesto_base("Salidas", 700.0)  # upsert
    base = listar_presupuesto_base()
    check("Upsert base: Salidas = 700 y sigue habiendo 3",
          len(base) == 3 and cat({"categorias": base}, "Salidas")["monto_limite_base"] == 700.0)
    definir_presupuesto_base("Salidas", 600.0)  # restaurar

    # ---------- C. Semana actual: la base se repite ----------
    estado = estado_semana(lunes)  # auto-inicializa
    check("Semana actual inicializada con 3 categorías",
          len(estado["categorias"]) == 3)
    check("Límite comida = 300 (base)", cat(estado, "Comida")["limite"] == 300.0)
    check("Semanas futuras también inicializan (base se repite)",
          len(estado_semana(avanzar_semanas(lunes, 1))["categorias"]) == 3)

    # ---------- D. Gastos reales y semáforo ----------
    cuenta_id = crear_cuenta("Banorte", "cuenta", "MXN", 20000.0)
    registrar_ingreso("Sueldo", 5000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", cuenta_id=cuenta_id)
    registrar_gasto(cuenta_id, "Comida", 100.0)   # hoy (en semana actual)
    registrar_gasto(cuenta_id, "Salidas", 80.0)
    estado = estado_semana(lunes)
    check("Comida gastado = 100 (verde)", cat(estado, "Comida")["gastado"] == 100.0
          and cat(estado, "Comida")["semaforo"] == "verde")
    registrar_gasto(cuenta_id, "Comida", 250.0)   # total 350 > 300 -> rojo
    estado = estado_semana(lunes)
    check("Comida 350/300 = rojo", cat(estado, "Comida")["semaforo"] == "rojo",
          f"{cat(estado, 'Comida')}")

    # ---------- E. Edición solo de la semana actual ----------
    editar_limite_semana(lunes, "Comida", 400.0)
    estado = estado_semana(lunes)
    check("Semana actual comida = 400 (editada)", cat(estado, "Comida")["limite"] == 400.0)
    check("350/400 = amarillo", cat(estado, "Comida")["semaforo"] == "amarillo")
    check("Base sigue en 300", cat({"categorias": listar_presupuesto_base()}, "Comida")["monto_limite_base"] == 300.0)

    # ---------- F. Semana pasada independiente ----------
    lunes_pasado = avanzar_semanas(lunes, -1)
    estado_pasado = estado_semana(lunes_pasado)
    check("Semana pasada usa base (comida 300)",
          cat(estado_pasado, "Comida")["limite"] == 300.0)
    fecha_pasada = (lunes_pasado + timedelta(days=2)).isoformat()
    registrar_gasto(cuenta_id, "Transporte", 50.0, fecha=fecha_pasada)
    estado_pasado = estado_semana(lunes_pasado)
    check("Gasto histórico cae en su semana (transporte 50)",
          cat(estado_pasado, "Transporte")["gastado"] == 50.0)
    check("Semana actual no se ve afectada",
          cat(estado_semana(lunes), "Transporte")["gastado"] == 0.0)

    # ---------- G. ¿Me alcanza para salir? ----------
    # límites actuales: salidas 600 + comida 400 + transporte 150 = 1150
    # gastado: 80 + 350 + 0 = 430 -> restante 720
    g1 = puedo_gastar(lunes, 400.0)
    check("Gastar 400 de 720 = verde", g1["semaforo"] == "verde", g1["mensaje"])
    g2 = puedo_gastar(lunes, 600.0)
    check("Gastar 600 deja 120 (<20%) = amarillo", g2["semaforo"] == "amarillo",
          g2["mensaje"])
    g3 = puedo_gastar(lunes, 800.0)
    check("Gastar 800 > 720 = rojo", g3["semaforo"] == "rojo", g3["mensaje"])

    # ---------- H. Suscripciones generales ----------
    luz = agregar_suscripcion("Luz", 800.0, "MXN", dia_cobro=10,
                              cuenta_id=cuenta_id, periodo="mensual")
    netflix = agregar_suscripcion("Netflix", 2000.0, "MXN", dia_cobro=15,
                                  cuenta_id=cuenta_id, periodo="mensual")
    seguro = agregar_suscripcion("Seguro auto", 2400.0, "MXN", dia_cobro=5,
                                 cuenta_id=cuenta_id, periodo="anual")
    check("Total mensual = 800+2000+200 = 3000", total_mensual_pesos() == 3000.0,
          str(total_mensual_pesos()))
    check("Costo mensual anual = 200", costo_mensual_pesos(
        {"monto": 2400.0, "moneda": "MXN", "periodo": "anual"}) == 200.0)

    editar_suscripcion(netflix, {"monto": 2500.0})
    check("Netflix editado: total = 3500", total_mensual_pesos() == 3500.0,
          str(total_mensual_pesos()))
    set_activa_suscripcion(luz, False)
    check("Luz desactivada: total = 2700", total_mensual_pesos() == 2700.0,
          str(total_mensual_pesos()))
    set_activa_suscripcion(luz, True)
    check("Luz reactivada: total = 3500", total_mensual_pesos() == 3500.0,
          str(total_mensual_pesos()))

    cobros = cobros_del_mes(2026, 11)
    check("Cobros de noviembre: 3, ordenados por día",
          len(cobros) == 3 and [c["dia_cobro"] for c in cobros] == [5, 10, 15],
          str([c["nombre"] for c in cobros]))

    impacto = impacto_en_semana(lunes)  # semana 9-15 nov
    check("Impacto semanal: luz (10) y netflix (15), no el seguro (5)",
          {i["nombre"] for i in impacto} == {"Luz", "Netflix"},
          str([i["nombre"] for i in impacto]))

    # ---------- I. Simulación compra cara con impacto semanal ----------
    tarjeta_id = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20, tasa_interes_mensual=3.5)
    registrar_gasto(tarjeta_id, "Super", 1000.0)

    s1 = simular_compra_semanal(lunes, 500.0, cuenta_id)
    check("Compra 500 con cuenta: compra verde", s1["compra"]["semaforo"] == "verde")
    check("Compra deja semana amarilla (220 restante < 20%)",
          s1["restante_semana_despues"] == 220.0 and s1["semaforo_final"] == "amarillo",
          f"{s1['restante_semana_despues']} {s1['semaforo_final']}")
    s2 = simular_compra_semanal(lunes, 500.0, tarjeta_id)
    check("Compra con tarjeta: no golpea la semana (restante 720)",
          s2["restante_semana_despues"] == 720.0, str(s2["restante_semana_despues"]))
    check("Semáforo final combina semana y deuda", s2["semaforo_final"] in ("verde", "amarillo"))

    # ---------- J. Eliminación ----------
    check("Eliminar suscripción", eliminar_suscripcion(seguro) is True)
    check("Tras eliminar: 2 activas", len(listar_suscripciones()) == 2)

    total = len(PASADAS)
    ok = sum(PASADAS)
    print(f"\nResultado: {ok}/{total} pruebas pasadas")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
