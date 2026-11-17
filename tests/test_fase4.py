"""Pruebas de la Fase 4: lógica financiera base.

Se ejecuta como script:  uv run python tests/test_fase4.py
Usa una base de datos temporal aislada (variable FINANZAS_DB).
"""

import os
import sys
import tempfile
from datetime import date

# Base de datos aislada para la prueba
TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase4.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

# Asegura que el paquete src sea importable al ejecutar desde la raíz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.services import (
    get_tipo_cambio,
    set_tipo_cambio,
    convertir_a_pesos,
    convertir_desde_pesos,
    crear_cuenta,
    listar_cuentas,
    obtener_cuenta,
    efectivo_total_pesos,
    deuda_total_pesos,
    patrimonio_neto_pesos,
    configurar_tarjeta,
    info_tarjeta,
    proxima_fecha_mes,
    dias_hasta,
    registrar_gasto,
    registrar_ingreso,
    listar_gastos,
    listar_ingresos,
)

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def main():
    init_db()

    # 1. Tipo de cambio por defecto
    check("Tipo de cambio default es 18.63", abs(get_tipo_cambio() - 18.63) < 1e-9,
          f"{get_tipo_cambio()}")

    # 2. Conversión de moneda
    check("100 USD -> 1863 MXN", abs(convertir_a_pesos(100, "USD") - 1863.00) < 0.01,
          f"{convertir_a_pesos(100, 'USD')}")
    check("500 MXN -> 500 MXN", convertir_a_pesos(500, "MXN") == 500.0)
    check("1863 MXN -> 100 USD", abs(convertir_desde_pesos(1863, "USD") - 100.0) < 0.01)

    # 3. Cambio de tipo de cambio
    set_tipo_cambio(20.0)
    check("Tipo de cambio actualizado a 20", get_tipo_cambio() == 20.0)
    check("100 USD -> 2000 MXN con TC 20", convertir_a_pesos(100, "USD") == 2000.0)
    set_tipo_cambio(18.63)

    # 4. Crear cuentas
    cuenta_id = crear_cuenta("Cuenta Banorte", "cuenta", "MXN", 5000.0)
    tarjeta_id = crear_cuenta("Tarjeta Invex Sams", "tarjeta_credito", "MXN", 0.0)
    check("Cuenta creada", cuenta_id > 0, f"id={cuenta_id}")
    check("Tarjeta creada", tarjeta_id > 0, f"id={tarjeta_id}")

    # 5. Ingreso suma al saldo
    ing = registrar_ingreso("Sueldo", 12000, tipo="sueldo_recurrente",
                            frecuencia="quincenal", cuenta_id=cuenta_id)
    check("Ingreso suma al saldo (5000+12000)", obtener_balance(cuenta_id) == 17000.0,
          f"{obtener_balance(cuenta_id)}")
    check("Ingreso convertido a pesos", ing["convertido_a_pesos"] == 12000.0)

    # 6. Gasto en cuenta resta del saldo
    gasto = registrar_gasto(cuenta_id, "Comida", 350.0)
    check("Gasto resta del saldo (17000-350)", obtener_balance(cuenta_id) == 16650.0,
          f"{obtener_balance(cuenta_id)}")
    check("Gasto registrado", gasto["id"] > 0)

    # 7. Gasto en dólares
    gasto_usd = registrar_gasto(cuenta_id, "Suscripción", 10.0, moneda="USD")
    check("Gasto USD convertido (10*18.63)", gasto_usd["convertido_a_pesos"] == 186.3,
          f"{gasto_usd['convertido_a_pesos']}")

    # 8. Configurar tarjeta y gastar en ella (sube deuda)
    configurar_tarjeta(
        tarjeta_id, dia_corte=15, dia_pago=5, dias_para_pagar=20,
        tasa_interes_mensual=3.5, limite_credito_maximo=10000.0,
        minimo_uso_monto=2000.0, costo_admin_si_no_alcance=300.0,
    )
    gasto_tarjeta = registrar_gasto(tarjeta_id, "Supermercado", 2500.0)
    check("Gasto en tarjeta sube deuda (0+2500)", gasto_tarjeta["balance_nuevo"] == 2500.0,
          f"{gasto_tarjeta['balance_nuevo']}")

    # 9. Alerta de límite (gastar hasta pasar 90%)
    registrar_gasto(tarjeta_id, "Electrónica", 7000.0)
    alertas = registrar_gasto(tarjeta_id, "Varios", 100.0)["alertas"]
    check("Alerta por uso alto del límite", any("% del" in a or "excedido" in a for a in alertas),
          str(alertas))

    # 10. Info de tarjeta (fechas)
    info = info_tarjeta(tarjeta_id, desde=date(2026, 11, 11))
    check("Próximo corte calculado", info["proximo_corte"] == "2026-11-15",
          info["proximo_corte"])
    check("Días hasta corte = 4", info["dias_hasta_corte"] == 4,
          str(info["dias_hasta_corte"]))
    check("Próximo pago calculado", info["proximo_pago"] == "2026-12-05",
          info["proximo_pago"])
    check("Pago por corte = corte + 20 días", info["pago_por_corte"] == "2026-12-05",
          info["pago_por_corte"])

    # 11. Días hasta con día ya pasado este mes
    check("proxima_fecha_mes(5) desde 11 nov -> 5 dic",
          proxima_fecha_mes(5, date(2026, 11, 11)) == date(2026, 12, 5))
    check("dias_hasta(15) desde 11 nov = 4", dias_hasta(15, date(2026, 11, 11)) == 4)

    # 12. Totales
    efectivo = efectivo_total_pesos()
    deuda = deuda_total_pesos()
    check("Efectivo total refleja cuentas", abs(efectivo - obtener_balance(cuenta_id)) < 0.01,
          f"{efectivo}")
    check("Deuda total refleja tarjeta", abs(deuda - obtener_balance(tarjeta_id)) < 0.01,
          f"{deuda}")
    check("Patrimonio = efectivo - deuda",
          abs(patrimonio_neto_pesos() - (efectivo - deuda)) < 0.01,
          f"{patrimonio_neto_pesos()}")

    # 13. Listados
    check("Listado de cuentas = 2", len(listar_cuentas()) == 2,
          str(len(listar_cuentas())))
    check("Listado de gastos >= 5", len(listar_gastos()) >= 5,
          str(len(listar_gastos())))
    check("Listado de ingresos = 1", len(listar_ingresos()) == 1,
          str(len(listar_ingresos())))

    # Resultado
    total = len(PASADAS)
    ok = sum(PASADAS)
    print(f"\nResultado: {ok}/{total} pruebas pasadas")
    if ok != total:
        sys.exit(1)


def obtener_balance(cuenta_id):
    return float(obtener_cuenta(cuenta_id)["balance_actual"])


if __name__ == "__main__":
    main()
