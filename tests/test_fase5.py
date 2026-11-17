"""Pruebas de la Fase 5: lógica financiera avanzada.

Se ejecuta como script:  uv run python tests/test_fase5.py
Usa una base de datos temporal aislada (variable FINANZAS_DB).
"""

import os
import sys
import tempfile
from datetime import date

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase5.db")
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
    proyectar,
    proyectar_desde_saldo,
    obtener_proyeccion_guardada,
    uso_del_mes,
    evaluar_minimo_uso,
    cargo_ya_aplicado,
    simular_compra,
    listar_simulaciones,
    evaluar_riesgos,
    riesgo_deuda_creciente,
)
from src.repositories import suscripcion_repo

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def balance(cuenta_id):
    from src.services import obtener_cuenta
    return float(obtener_cuenta(cuenta_id)["balance_actual"])


def main():
    init_db()

    # ---------- A. Setup ----------
    cuenta_id = crear_cuenta("Banorte", "cuenta", "MXN", 5000.0)
    tarjeta_id = crear_cuenta("Invex Sams", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(
        tarjeta_id, dia_corte=15, dia_pago=5, dias_para_pagar=20,
        tasa_interes_mensual=3.5, limite_credito_maximo=10000.0,
        minimo_uso_monto=2000.0, costo_admin_si_no_alcance=300.0,
    )
    registrar_ingreso("Sueldo", 5000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", cuenta_id=cuenta_id)
    registrar_gasto(tarjeta_id, "Supermercado", 5000.0)
    check("Setup: deuda tarjeta = 5000", balance(tarjeta_id) == 5000.0)

    # ---------- B. Proyección (5000 deuda, 3.5%, pago 1000) ----------
    p = proyectar(tarjeta_id, pago_mensual=1000.0, meses=12)
    check("Proyección liquida en 6 meses", p["meses_para_liquidar"] == 6,
          str(p["meses_para_liquidar"]))
    check("Proyección fecha liquidación", p["fecha_estimada_liquidacion"] is not None,
          str(p["fecha_estimada_liquidacion"]))
    check("Interés total = 596.13", abs(p["interes_total"] - 596.13) < 0.01,
          str(p["interes_total"]))
    check("Saldo a 1 mes = 4175", p["saldos_por_horizonte"]["mes_1"] == 4175.0,
          str(p["saldos_por_horizonte"]["mes_1"]))
    check("Saldo a 6 meses = 0 (liquidada)", p["saldos_por_horizonte"]["mes_6"] == 0.0)
    check("Horizontes 9 y 12 en cero", p["saldos_por_horizonte"]["mes_9"] == 0.0
          and p["saldos_por_horizonte"]["mes_12"] == 0.0)
    guardada = obtener_proyeccion_guardada(tarjeta_id)
    check("Proyección guardada con 6 filas", len(guardada) == 6, str(len(guardada)))
    check("Filas guardadas sin perfil", all(g["perfil_id"] is None for g in guardada))

    # ---------- C. Proyección pura con deuda cero ----------
    pz = proyectar_desde_saldo(0, 3.5, 1000)
    check("Deuda 0 se liquida en el mes 1", pz["meses_para_liquidar"] == 1)

    # ---------- D. Simulación compra cara con cuenta ----------
    s1 = simular_compra(1000.0, cuenta_id)
    check("Compra 1000 con saldo 10000 = verde", s1["semaforo"] == "verde")
    check("Compra deja saldo 9000", s1["despues"] == 9000.0)
    s2 = simular_compra(20000.0, cuenta_id)
    check("Compra 20000 sin saldo = rojo", s2["semaforo"] == "rojo")
    check("Compra imposible deja saldo negativo", s2["despues"] == -10000.0)

    # ---------- E. Simulación compra cara con tarjeta ----------
    s3 = simular_compra(2000.0, tarjeta_id, pago_mensual_estimado=1000.0)
    check("Compra tarjeta: deuda nueva = 7000", s3["despues"] == 7000.0,
          str(s3["despues"]))
    check("Compra tarjeta: impacto deuda = 2000", s3["impacto_deuda"] == 2000.0)
    check("Compra tarjeta: semáforo amarillo (70%+compra sube uso)", s3["semaforo"] in ("verde", "amarillo"),
          s3["semaforo"])
    check("Meses extra para liquidar = 3", s3["meses_extra_para_liquidar"] == 3,
          str(s3["meses_extra_para_liquidar"]))
    check("Interés extra > 0", s3["interes_extra"] is not None and s3["interes_extra"] > 0,
          str(s3["interes_extra"]))

    # ---------- F. Mínimo de uso (mes de enero sin gastos) ----------
    enero = (2026, 1)
    check("Uso de enero = 0", uso_del_mes(tarjeta_id, *enero) == 0.0)
    e1 = evaluar_minimo_uso(tarjeta_id, enero[0], enero[1], aplicar=False)
    check("Enero no alcanza mínimo (simulación)", e1["alcanza_minimo"] is False
          and e1["cargo_aplicado"] is False)
    e2 = evaluar_minimo_uso(tarjeta_id, enero[0], enero[1], aplicar=True)
    check("Cargo de administración aplicado", e2["cargo_aplicado"] is True)
    check("Deuda tras cargo = 5300 (5000+300)", e2["deuda_nueva"] == 5300.0,
          str(e2["deuda_nueva"]))
    check("Cargo registrado en BD", cargo_ya_aplicado(tarjeta_id, *enero) is True)
    e3 = evaluar_minimo_uso(tarjeta_id, enero[0], enero[1], aplicar=True)
    check("Cargo no se duplica (idempotente)", e3["cargo_aplicado"] is False
          and "ya fue aplicado" in e3["mensaje"])

    # ---------- G. Mes actual alcanza el mínimo ----------
    hoy = date.today()
    uso_actual = uso_del_mes(tarjeta_id, hoy.year, hoy.month)
    g = evaluar_minimo_uso(tarjeta_id, hoy.year, hoy.month, aplicar=True)
    check("Mes actual alcanza el mínimo (5000 gastados)", g["alcanza_minimo"] is True,
          f"uso={uso_actual}")

    # ---------- H. Detección de riesgos ----------
    registrar_gasto(tarjeta_id, "Electrónica", 5000.0)  # deuda 10300 -> límite excedido
    suscripcion_repo.create({
        "nombre": "Luz", "monto": 800.0, "moneda": "MXN",
        "dia_cobro": 10, "periodo": "mensual", "cuenta_id": cuenta_id, "activa": 1,
    })
    suscripcion_repo.create({
        "nombre": "Netflix", "monto": 2000.0, "moneda": "MXN",
        "dia_cobro": 15, "periodo": "mensual", "cuenta_id": cuenta_id, "activa": 1,
    })
    alertas = evaluar_riesgos()
    niveles = {a["nivel"] for a in alertas}
    tipos = {a["tipo"] for a in alertas}
    check("Hay alerta roja por límite excedido", "rojo" in niveles, str(niveles))
    check("Hay alerta amarilla de suscripciones", "amarillo" in niveles
          and "suscripciones" in tipos, str(tipos))
    check("Alertas incluyen mínimo_uso o límite", "limite_credito" in tipos,
          str(tipos))

    # ---------- I. Deuda creciente ----------
    check("Pago 30 < interés 35 => deuda crece", riesgo_deuda_creciente(1000, 3.5, 30) is True)
    check("Pago 40 > interés 35 => deuda baja", riesgo_deuda_creciente(1000, 3.5, 40) is False)
    check("Deuda 0 nunca crece", riesgo_deuda_creciente(0, 3.5, 10) is False)

    # ---------- J. Historial de simulaciones ----------
    sims = listar_simulaciones()
    check("Historial de simulaciones >= 3", len(sims) >= 3, str(len(sims)))

    total = len(PASADAS)
    ok = sum(PASADAS)
    print(f"\nResultado: {ok}/{total} pruebas pasadas")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
