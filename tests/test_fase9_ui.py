"""Pruebas de la Fase 9: la UI se construye correctamente y export CSV.

Se ejecuta como script:  uv run python tests/test_fase9_ui.py
Las vistas se construyen con una página simulada (sin abrir la ventana).
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase9.db")
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
    agregar_suscripcion,
    definir_presupuesto_base,
    simular_compra,
    activar_perfil,
    exportar_tabla,
    exportar_todo,
    listar_tablas,
)

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


class MockPage:
    """Página simulada: las vistas solo la usan dentro de callbacks."""

    def show_dialog(self, dlg):
        self._dlg = dlg

    def update(self):
        pass


def main():
    init_db()

    # Datos de ejemplo para que las vistas muestren contenido
    cuenta_id = crear_cuenta("Banorte", "cuenta", "MXN", 20000.0)
    registrar_ingreso("Sueldo", 8000, tipo="sueldo_recurrente",
                      frecuencia="quincenal", cuenta_id=cuenta_id)
    registrar_gasto(cuenta_id, "Comida", 150.0)
    registrar_gasto(cuenta_id, "Transporte", 60.0)
    registrar_gasto(cuenta_id, "Salidas", 200.0)
    tarjeta_id = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20, tasa_interes_mensual=3.5,
                       limite_credito_maximo=10000.0,
                       minimo_uso_monto=2000.0, costo_admin_si_no_alcance=300.0)
    registrar_gasto(tarjeta_id, "Super", 3000.0)
    agregar_suscripcion("Netflix", 200, "MXN", 15, "mensual", cuenta_id)
    definir_presupuesto_base("Salidas", 500.0)
    definir_presupuesto_base("Comida", 400.0)
    simular_compra(5000.0, cuenta_id, guardar=True)
    activar_perfil(1)

    import flet as ft
    from src.ui.views import dimensiones, mision, personaje, resumen

    page = MockPage()

    def refresh(destino=None):
        pass

    def on_open_mision(n):
        page._mision = n

    estado_local: dict = {}

    # ---------- Vistas principales ----------
    v_dim = dimensiones.build(page, refresh, on_open_mision)
    check("Vista Dimensiones construye", isinstance(v_dim, ft.Column)
          and len(v_dim.controls) >= 4)

    v_res = resumen.build(page, refresh)
    check("Vista Resumen construye", isinstance(v_res, ft.Column)
          and len(v_res.controls) >= 6)

    v_per = personaje.build(page, refresh)
    check("Vista Personaje (avatar) construye", isinstance(v_per, ft.Column)
          and len(v_per.controls) >= 5)

    from src.ui.views import configuracion
    v_cfg = configuracion.build(page, refresh)
    check("Vista Configuración construye", isinstance(v_cfg, ft.Column)
          and len(v_cfg.controls) >= 8)

    # ---------- Misiones 1 a 8 ----------
    todas_ok = True
    for d in range(1, 9):
        try:
            v = mision.build(page, refresh, d, estado_local)
            # La misión es un Container (fondo de la dimensión) que envuelve
            # la Column de contenido, o la Column directa si no hay fondo.
            es_valida = isinstance(v, ft.Column) and v.controls \
                or isinstance(v, ft.Container) and v.content is not None
            if not es_valida:
                todas_ok = False
                print(f"   misión {d}: vacía")
        except Exception as e:  # noqa: BLE001
            todas_ok = False
            print(f"   misión {d}: {type(e).__name__}: {e}")
    check("Las 8 misiones construyen sin errores", todas_ok)

    # ---------- Navegación A->B ----------
    from src.ui.views.dimensiones import _estado_chip
    ok_chip, _, _ = _estado_chip({"n": 1, "completada": True}, 2)
    check("Chip de dimensión completada", ok_chip == "✅ Completada")
    actual_chip, _, _ = _estado_chip({"n": 2, "completada": False}, 2)
    check("Chip de dimensión actual", actual_chip == "🔥 Actual")
    bloq_chip, _, _ = _estado_chip({"n": 5, "completada": False}, 2)
    check("Chip de dimensión bloqueada", bloq_chip == "🔒 Nivel insuficiente")

    # ---------- Export CSV ----------
    check("9 tablas exportables", len(listar_tablas()) == 9, str(listar_tablas()))
    ruta = exportar_tabla("gastos")
    check("Export gastos crea archivo", os.path.exists(ruta), ruta)
    with open(ruta, encoding="utf-8") as f:
        lineas = f.read().strip().splitlines()
    check("CSV gastos con encabezado + 4 filas", len(lineas) == 5, str(len(lineas)))
    check("CSV empieza con encabezado de gastos",
          lineas[0].startswith("id,cuenta_id,categoria"))

    archivos = exportar_todo()
    check("exportar_todo genera 9 archivos", len(archivos) == 9)
    check("Todos los archivos CSV existen",
          all(os.path.exists(p) for p in archivos.values()))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
