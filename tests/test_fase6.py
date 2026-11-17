"""Pruebas de la Fase 6: perfiles de pago y dashboard compartible.

Se ejecuta como script:  uv run python tests/test_fase6.py
Usa una base de datos temporal aislada (variable FINANZAS_DB).
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase6.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.services import (
    listar_perfiles,
    obtener_perfil_activo,
    activar_perfil,
    actualizar_perfil,
    crear_cuenta,
    configurar_tarjeta,
    registrar_ingreso,
    registrar_gasto,
    pago_minimo_tarjeta,
    calcular_pago_mensual,
    comparar_perfiles,
    distribuir_pago_total,
    listar_modulos,
    modulos_visibles,
    asignar_modulos,
    copiar_dashboard,
)
from src.repositories import suscripcion_repo

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def main():
    init_db()

    # ---------- A. Setup ----------
    perfiles = listar_perfiles()
    check("4 perfiles sembrados (Mínimo/Optimizado/Agresivo/Custom)",
          len(perfiles) == 4 and {p["tipo_perfil"] for p in perfiles} ==
          {"minimo", "optimizado", "agresivo", "custom"})
    activo = obtener_perfil_activo()
    check("Perfil activo por defecto = Mínimo", activo["tipo_perfil"] == "minimo")

    id_min = next(p["id"] for p in perfiles if p["tipo_perfil"] == "minimo")
    id_opt = next(p["id"] for p in perfiles if p["tipo_perfil"] == "optimizado")
    id_agr = next(p["id"] for p in perfiles if p["tipo_perfil"] == "agresivo")
    id_cus = next(p["id"] for p in perfiles if p["tipo_perfil"] == "custom")

    cuenta_id = crear_cuenta("Banorte", "cuenta", "MXN", 2000.0)  # +8000 ingreso = 10000 efectivo
    tarjeta_a = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    tarjeta_b = crear_cuenta("Oro", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_a, 15, 5, 20, tasa_interes_mensual=3.5,
                       limite_credito_maximo=10000.0)
    configurar_tarjeta(tarjeta_b, 20, 10, 25, tasa_interes_mensual=5.0)
    registrar_ingreso("Sueldo", 8000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", cuenta_id=cuenta_id)
    registrar_gasto(tarjeta_a, "Super", 5000.0)
    registrar_gasto(tarjeta_b, "Viaje", 3000.0)
    suscripcion_repo.create({"nombre": "Luz", "monto": 800.0, "moneda": "MXN",
                             "dia_cobro": 10, "periodo": "mensual",
                             "cuenta_id": cuenta_id, "activa": 1})
    suscripcion_repo.create({"nombre": "Netflix", "monto": 2000.0, "moneda": "MXN",
                             "dia_cobro": 15, "periodo": "mensual",
                             "cuenta_id": cuenta_id, "activa": 1})

    # ---------- B. Pago mínimo ----------
    p = obtener_perfil_activo()
    check("Mínimo tarjeta A = max(200, 5% de 5000) = 250",
          pago_minimo_tarjeta(5000.0, p) == 250.0)
    check("Mínimo tarjeta B = max(200, 5% de 3000) = 200",
          pago_minimo_tarjeta(3000.0, p) == 200.0)
    calc_min = calcular_pago_mensual(tarjeta_a, id_min)
    check("Pago mensual mínimo A = 250", calc_min["pago_mensual"] == 250.0)

    # ---------- C. Optimizado (protege liquidez y suscripciones) ----------
    calc_opt = calcular_pago_mensual(tarjeta_a, id_opt)
    # excedente = 8000 ingresos - 2800 subs - 450 mínimos = 4750; extra = 50% = 2375
    check("Optimizado extra = 2375", calc_opt["pago_extra"] == 2375.0,
          str(calc_opt["pago_extra"]))
    check("Optimizado pago = 2625", calc_opt["pago_mensual"] == 2625.0,
          str(calc_opt["pago_mensual"]))

    # ---------- D. Agresivo (reserva de flujo + suscripciones protegidas) ----------
    calc_agr = calcular_pago_mensual(tarjeta_a, id_agr)
    # disponible = 10000 efectivo - 5000 reserva - 2800 subs = 2200
    check("Agresivo extra = 2200 (mantiene reserva de 5000)",
          calc_agr["pago_extra"] == 2200.0, str(calc_agr["pago_extra"]))
    check("Agresivo pago = 2450 (mínimo 250 + extra 2200)",
          calc_agr["pago_mensual"] == 2450.0, str(calc_agr["pago_mensual"]))

    # ---------- E. Custom con parámetros propios ----------
    actualizar_perfil(id_cus, {"pago_minimo_porcentaje": 10.0, "pago_minimo_monto_fijo": 500.0})
    calc_cus = calcular_pago_mensual(tarjeta_a, id_cus)
    check("Custom pago = max(500, 10% de 5000) = 500",
          calc_cus["pago_mensual"] == 500.0, str(calc_cus["pago_mensual"]))

    # ---------- F. Un solo perfil activo a la vez ----------
    activar_perfil(id_cus)
    check("Custom activo tras activar", obtener_perfil_activo()["id"] == id_cus)
    activar_perfil(id_min)
    check("Mínimo activo tras reactivar", obtener_perfil_activo()["id"] == id_min)
    otros = [p2 for p2 in listar_perfiles() if p2["id"] != id_min]
    check("Ningún otro perfil activo", all(p2["activo"] == 0 for p2 in otros))

    # ---------- G. Comparación lado a lado ----------
    comp = comparar_perfiles(tarjeta_a, horizonte=120)
    check("Comparación devuelve 4 perfiles", len(comp) == 4, str(len(comp)))
    por_tipo = {c["tipo_perfil"]: c for c in comp}
    check("Agresivo liquida en 3 meses", por_tipo["agresivo"]["meses_para_liquidar"] == 3,
          str(por_tipo["agresivo"]["meses_para_liquidar"]))
    check("Optimizado liquida en 3 meses", por_tipo["optimizado"]["meses_para_liquidar"] == 3,
          str(por_tipo["optimizado"]["meses_para_liquidar"]))
    check("Agresivo paga menos intereses que Mínimo",
          por_tipo["agresivo"]["interes_total"] < por_tipo["minimo"]["interes_total"],
          f"agr={por_tipo['agresivo']['interes_total']} min={por_tipo['minimo']['interes_total']}")
    m = por_tipo["minimo"]
    check("Mínimo tiene fecha de último pago o no liquida en horizonte",
          (m["meses_para_liquidar"] is None and m["fecha_estimada_liquidacion"] is None)
          or (m["meses_para_liquidar"] is not None and m["fecha_estimada_liquidacion"]),
          f"meses={m['meses_para_liquidar']} fecha={m['fecha_estimada_liquidacion']}")

    # ---------- H. Distribución de presupuesto entre tarjetas ----------
    dist = distribuir_pago_total(id_agr, 4000.0)
    por_cuenta = {a["cuenta_id"]: a for a in dist["asignaciones"]}
    check("Tarjeta B (mayor tasa) recibe su deuda completa: 3150",
          por_cuenta[tarjeta_b]["pago_total"] == 3150.0,
          str(por_cuenta[tarjeta_b]["pago_total"]))
    check("Tarjeta A recibe el restante: 850",
          por_cuenta[tarjeta_a]["pago_total"] == 850.0,
          str(por_cuenta[tarjeta_a]["pago_total"]))
    check("Total asignado = 4000, sobrante 0",
          dist["total_asignado"] == 4000.0 and dist["sobrante"] == 0.0,
          f"total={dist['total_asignado']} sobrante={dist['sobrante']}")

    # ---------- I. Módulos de dashboard y compartimiento ----------
    check("5 módulos de dashboard sembrados", len(listar_modulos()) == 5,
          str(len(listar_modulos())))
    asignar_modulos(id_cus, [1, 3])
    vis = modulos_visibles(id_cus)
    check("Custom con 2 módulos visibles", len(vis) == 2, str(len(vis)))
    check("Orden respetado (resumen primero)", vis[0]["nombre_modulo"] == "resumen_financiero")
    asignar_modulos(id_agr, [2, 4, 5])
    copiar_dashboard(id_agr, id_cus)
    vis_cus = modulos_visibles(id_cus)
    vis_agr = modulos_visibles(id_agr)
    check("Custom hereda dashboard del Agresivo",
          [m["id"] for m in vis_cus] == [m["id"] for m in vis_agr] == [2, 4, 5],
          str([m["nombre_modulo"] for m in vis_cus]))

    total = len(PASADAS)
    ok = sum(PASADAS)
    print(f"\nResultado: {ok}/{total} pruebas pasadas")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
