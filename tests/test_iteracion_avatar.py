"""Pruebas de dimensiones iterativas, avatar financiero y estilo retro.

Verifica:
- El juego tiene 8 dimensiones y se pueden rejugar con premio de
  repetición (la mitad), sin perder el nivel alcanzado.
- Los registros de las dimensiones se pueden editar y eliminar
  (cuentas, gastos, ingresos) también desde la propia misión.
- El avatar del Guardián refleja el estado financiero y sus imágenes
  pixel-art existen.
- La configuración vive en su propia sección y el estilo es retro 8 bits
  (fuente pixel registrada, bordes gruesos).

Se ejecuta como script:  uv run python tests/test_iteracion_avatar.py
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_iteracion.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import flet as ft

from src.database import init_db
from src.repositories import cuenta_repo
from src.services import (
    completar_dimension,
    crear_cuenta,
    definir_presupuesto_base,
    editar_cuenta,
    eliminar_cuenta,
    estado_guardian,
    estado_progresion,
    obtener_cuenta,
    obtener_puntos,
    progreso,
    registrar_gasto,
    TOTAL_DIMENSIONES,
)
from src.ui import components as ui
from src.ui.theme import PIXEL_FONT
from src.ui.views import configuracion, mision, personaje

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    seguro = str(detalle).encode("ascii", "replace").decode()
    nombre_seguro = str(nombre).encode("ascii", "replace").decode()
    print(f"[{estado}] {nombre_seguro}" + (f" -> {seguro}" if detalle else ""))


class MockPage:
    def __init__(self):
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
    page = MockPage()
    refrescos = []

    def refresh(destino=None):
        refrescos.append(destino or "actual")

    # ---------- 8 dimensiones ----------
    check("El juego tiene 8 dimensiones",
          TOTAL_DIMENSIONES == 8
          and len(estado_progresion()["dimensiones"]) == 8)
    check("La última es el Salón de Estrategas (perfiles de pago)",
          estado_progresion()["dimensiones"][-1]["nombre"]
          == "Salón de Estrategas")

    # ---------- Iteración con premio ----------
    cuenta_id = crear_cuenta("Débito", "cuenta", "MXN", 1000.0)
    c1 = completar_dimension(1)
    check("Primera vez: cofre completo (100 pts, nivel 2)",
          c1["puntos_ganados"] == 100 and c1["nivel_nuevo"] == 2)
    rep = completar_dimension(1)
    check("Repetición: +50 pts, +25 XP, nivel se mantiene",
          rep["repeticion"] and rep["puntos_ganados"] == 50
          and rep["xp_ganada"] == 25 and rep["nivel_nuevo"] == 2
          and obtener_puntos() == 150)
    try:
        completar_dimension(5)
        check("Sigue sin poder adelantarse a dimensiones bloqueadas", False)
    except ValueError:
        check("Sigue sin poder adelantarse a dimensiones bloqueadas", True)

    vista1 = mision.build(page, refresh, 1, {})
    check("La misión ya completada ofrece rejugar con su premio",
          botones(vista1, "🔁 Rejugar Dimensión 1 · +50 pts")
          and any("iterativa" in t for t in textos(vista1)))

    # ---------- Editar / eliminar registros desde la misión ----------
    edits = [b for b in caminar(vista1)
             if isinstance(b, ft.IconButton) and b.tooltip == "Editar"]
    check("D1 lista las cuentas con botón de editar", len(edits) >= 1)
    edits[0].on_click(Evt())
    dlg = page.dialogos[-1]
    nombre_field = next(c for c in caminar(dlg)
                        if isinstance(c, ft.TextField) and c.label == "Nombre")
    nombre_field.value = "Débito BBVA"
    botones(dlg, "Guardar cambios")[0].on_click(Evt())
    check("Editar cuenta desde la D1 guarda el nuevo nombre",
          obtener_cuenta(cuenta_id)["nombre"] == "Débito BBVA")

    editar_cuenta(cuenta_id, balance=2222.0)
    check("Editar balance directo (saldo inicial corregido)",
          obtener_cuenta(cuenta_id)["balance_actual"] == 2222.0)

    suelta_id = crear_cuenta("Suelta", "cuenta", "MXN", 10.0)
    eliminar_cuenta(suelta_id)
    check("Cuenta sin registros se puede eliminar",
          cuenta_repo.get_by_id(suelta_id) is None)
    registrar_gasto(cuenta_id, "Personal", 50.0)
    try:
        eliminar_cuenta(cuenta_id)
        check("Cuenta con gastos NO se puede eliminar (protege historial)",
              False)
    except ValueError:
        check("Cuenta con gastos NO se puede eliminar (protege historial)",
              True)

    # ---------- Avatar según estado financiero ----------
    est = estado_guardian()
    check("El avatar tiene estado, título e imagen",
          est["estado"] in ("legendario", "fuerte", "herido", "critico")
          and est["imagen"].startswith("assets/personaje/guardian_"))
    faltan = [e for e in ("legendario", "fuerte", "herido", "critico")
              if not os.path.exists(
                  os.path.join(RAIZ, f"assets/personaje/guardian_{e}.png"))]
    check("Los 4 avatares pixel-art existen", not faltan, ", ".join(faltan))

    definir_presupuesto_base("Personal", 100.0)
    registrar_gasto(cuenta_id, "Personal", 500.0)  # semana reventada
    est_rojo = estado_guardian()
    check("Semana en rojo -> Guardián en peligro (crítico)",
          est_rojo["estado"] == "critico", est_rojo["titulo"])

    v_per = personaje.build(page, refresh)
    imagenes = [c.src for c in caminar(v_per) if isinstance(c, ft.Image)]
    check("Personaje muestra el avatar crítico",
          any("guardian_critico" in (s or "") for s in imagenes),
          str(imagenes))

    # ---------- Configuración ----------
    v_cfg = configuracion.build(page, refresh)
    txt_cfg = textos(v_cfg)
    check("Configuración tiene general, perfil, armaduras y badges",
          all(any(k in t for t in txt_cfg)
              for k in ("General", "Perfil de pago", "Armaduras", "Badges")))

    # ---------- Estilo retro 8 bits ----------
    t = ui.titulo("Prueba")
    check("Títulos usan la fuente pixel 8 bits", t.font_family == PIXEL_FONT)
    check("La fuente Press Start 2P está en assets",
          os.path.exists(os.path.join(
              RAIZ, "assets", "fuentes", "PressStart2P-Regular.ttf")))
    borde = ui._borde()
    check("Bordes gruesos retro (2 px tinta oscura)",
          borde.top.width == 2)
    card = ui.stat_card("Saldo", "$100")
    check("Tarjetas estilo 8 bits (esquinas casi cuadradas)",
          card.border_radius == 4)

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
