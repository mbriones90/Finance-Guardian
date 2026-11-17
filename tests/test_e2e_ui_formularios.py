"""Prueba E2E de la capa UI: el usuario juega D1→D13 dando CLICS reales.

A diferencia de test_fase11 (que ejercita los servicios), esta prueba simula
los clics en los formularios de cada dimensión (botones Guardar/Simular/
Activar/Exportar y "Completar Dimensión"), que es donde vivían los bugs de
la Dimensión 3 (dropdown sin preselección) y de las imágenes.

También verifica que **todas** las imágenes referenciadas por la UI existan
en disco bajo ``assets/`` (regresión del bug de assets_dir).

Se ejecuta como script:  uv run python tests/test_e2e_ui_formularios.py
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_e2e_ui.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import flet as ft

from src.database import init_db
from src.services import (
    estado_progresion,
    listar_badges,
    obtener_puntos,
    progreso,
)
from src.services.cofres import info_dimension
from src.services.inventario import FONDOS
from src.ui import components as ui
from src.ui.views import dimensiones, distribucion, mision, personaje, resumen

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


class MockPage:
    """Page mínima para ejercitar handlers de la UI fuera de Flet."""

    def __init__(self):
        self.overlay = []
        self.dialogos = []
        self.agregados = []
        self.updates = 0

    def show_dialog(self, dlg):
        self.dialogos.append(dlg)

    def add(self, control):
        self.agregados.append(control)

    def update(self):
        self.updates += 1

    def run_task(self, handler, *args):
        import asyncio
        return asyncio.run(handler(*args))


def _hijos(control):
    """Todos los controles hijos directos de un control Flet."""
    for attr in ("controls",):
        if hasattr(control, attr) and getattr(control, attr):
            yield from getattr(control, attr)
    contenido = getattr(control, "content", None)
    if contenido is not None and isinstance(contenido, ft.Control):
        yield contenido


def caminar(raiz):
    """Generador que recorre todo el árbol de controles."""
    pila = [raiz]
    while pila:
        c = pila.pop()
        yield c
        pila.extend(_hijos(c))


def _texto_boton(btn):
    for attr in ("content", "text", "label"):
        valor = getattr(btn, attr, None)
        if isinstance(valor, str) and valor:
            return valor
    return ""


def botones(vista):
    return [c for c in caminar(vista) if isinstance(c, ft.Button)]


def boton(vista, texto):
    for b in botones(vista):
        if _texto_boton(b).startswith(texto):
            return b
    raise AssertionError(f"Botón no encontrado: {texto!r} en "
                         f"{[_texto_boton(b) for b in botones(vista)]}")


def campo(vista, etiqueta):
    for c in caminar(vista):
        if isinstance(c, (ft.TextField, ft.Dropdown)) and c.label == etiqueta:
            return c
    raise AssertionError(f"Campo no encontrado: {etiqueta!r}")


class Evt:
    """Evento falso para invocar handlers on_click."""

    def __init__(self, control=None):
        self.control = control


def clic(btn):
    btn.on_click(Evt())


def imagenes_referenciadas(vista):
    """src de todas las imágenes (ft.Image y fondos de Container)."""
    srcs = []
    for c in caminar(vista):
        if isinstance(c, ft.Image) and isinstance(c.src, str):
            srcs.append(c.src)
        img = getattr(c, "image", None)
        if isinstance(img, ft.DecorationImage) and img.src:
            srcs.append(img.src)
    return srcs


def existe_asset(src):
    """El src de la UI es relativo a assets/ (ver components.ruta_asset)."""
    return os.path.exists(os.path.join(RAIZ, "assets", src.replace("/", os.sep)))


def main():
    init_db()
    page = MockPage()
    refrescos = []  # destinos registrados por refresh()

    def refresh(destino=None):
        refrescos.append(destino or "actual")

    todas_las_imagenes = []

    def jugar_dimension(n, preparar=None, boton_guardar=None, clics=1):
        """Construye la vista de misión, llena el form, guarda y completa."""
        estado_local = {}
        vista = mision.build(page, refresh, n, estado_local)
        todas_las_imagenes.extend(imagenes_referenciadas(vista))

        req_texto, req_ok = mision.REQUISITOS[n]
        btn_completar = boton(vista, f"✅ Completar Dimensión {n}")
        check(f"D{n}: botón completar deshabilitado antes de cumplir "
              f"requisito" if not req_ok() else
              f"D{n}: requisito ya cumplido al entrar",
              btn_completar.disabled == (not req_ok()))

        if boton_guardar:
            for _ in range(clics):
                if preparar:
                    preparar(vista)
                clic(boton(vista, boton_guardar))

        check(f"D{n}: requisito cumplido tras usar el formulario", req_ok(),
              req_texto)

        # Reconstruir (como hace refresh) para que el botón se habilite
        vista = mision.build(page, refresh, n, estado_local)
        todas_las_imagenes.extend(imagenes_referenciadas(vista))
        btn = boton(vista, f"✅ Completar Dimensión {n}")
        check(f"D{n}: botón completar habilitado", not btn.disabled)
        n_dialogos = len(page.dialogos)
        clic(btn)
        prog = progreso()
        check(f"D{n}: subió a nivel {min(n + 1, 13)}",
              prog["nivel"] == min(n + 1, 13), f"nivel={prog['nivel']}")
        check(f"D{n}: cofre mostrado con sonido/animación",
              len(page.dialogos) == n_dialogos + 1)
        check(f"D{n}: refresh volvió al mapa",
              refrescos[-1] == "dimensiones")
        return estado_local

    # ================= D1: El Despertar =================
    jugar_dimension(1,
                    preparar=lambda v: setattr(
                        campo(v, "Saldo inicial"), "value", "2000"),
                    boton_guardar="Guardar cuenta")

    # ================= D2: El Camino del Oro =================
    def prep_d2(v):
        campo(v, "Monto").value = "8000"
    jugar_dimension(2, preparar=prep_d2, boton_guardar="Guardar ingreso")

    # ================= D3: Bosque de Gastos =================
    # Regresión: el dropdown de cuenta debe venir preseleccionado.
    estado_local = {}
    vista3 = mision.build(page, refresh, 3, estado_local)
    dd_cuenta = campo(vista3, "Cuenta")
    check("D3: dropdown de cuenta preseleccionado (regresión int(None))",
          dd_cuenta.value is not None and dd_cuenta.value != "",
          f"value={dd_cuenta.value!r}")

    # Caso negativo: sin cuenta seleccionada → mensaje amigable, no crash
    dd_cuenta.value = None
    n_dialogos = len(page.dialogos)
    clic(boton(vista3, "Guardar gasto"))
    check("D3: sin cuenta muestra alerta amigable",
          len(page.dialogos) == n_dialogos + 1
          and "Selecciona la cuenta" in str(
              page.dialogos[-1].content.value))

    # Caso negativo: monto 0
    dd_cuenta.value = dd_cuenta.options[0].key
    campo(vista3, "Monto").value = "0"
    n_dialogos = len(page.dialogos)
    clic(boton(vista3, "Guardar gasto"))
    check("D3: monto 0 muestra error de validación",
          len(page.dialogos) == n_dialogos + 1
          and "mayor que cero" in str(page.dialogos[-1].content.value))

    # Caso feliz: 3 gastos dando clic 3 veces (el formulario conserva valores)
    campo(vista3, "Monto").value = "100"
    for _ in range(3):
        clic(boton(vista3, "Guardar gasto"))
    req_ok = mision.REQUISITOS[3][1]
    check("D3: 3 gastos registrados con clics", req_ok())

    vista3 = mision.build(page, refresh, 3, estado_local)
    btn = boton(vista3, "✅ Completar Dimensión 3")
    check("D3: botón completar habilitado", not btn.disabled)
    clic(btn)
    check("D3: subió a nivel 4", progreso()["nivel"] == 4)

    # ================= D4: Puerta del Crédito =================
    jugar_dimension(4, boton_guardar="Guardar tarjeta")

    # ================= D5: Cámara de Reglas =================
    def prep_d5(v):
        campo(v, "Tasa de interés mensual %").value = "3.5"
        campo(v, "Límite de crédito").value = "10000"
        campo(v, "Mínimo de uso mensual (ej. 2000)").value = "2000"
        campo(v, "Cargo por no alcanzar mínimo (ej. 300)").value = "300"
    jugar_dimension(5, preparar=prep_d5, boton_guardar="Guardar reglas")

    # ================= D6: Llanura del Presupuesto =================
    # Nuevo flujo: 1) presupuesto general, 2) reparto por categorías.
    estado_local = {}
    vista6 = mision.build(page, refresh, 6, estado_local)
    check("D6: botón completar deshabilitado sin general",
          boton(vista6, "✅ Completar Dimensión 6").disabled)
    clic(boton(vista6, "Guardar general"))  # 4000 mensual por defecto
    vista6 = mision.build(page, refresh, 6, estado_local)
    check("D6: aún falta repartir categorías",
          boton(vista6, "✅ Completar Dimensión 6").disabled)
    clic(boton(vista6, "Guardar categoría"))  # dropdown + 200 semanales
    check("D6: general + categoría cumplen requisito",
          mision.REQUISITOS[6][1]())
    # Caso negativo: repartir más del límite semanal general (~923)
    vista6 = mision.build(page, refresh, 6, estado_local)
    campo(vista6, "Límite semanal de la categoría").value = "9999"
    n_dialogos = len(page.dialogos)
    clic(boton(vista6, "Guardar categoría"))
    check("D6: no deja pasarse del presupuesto general",
          len(page.dialogos) == n_dialogos + 1
          and "Te pasas del presupuesto" in str(
              page.dialogos[-1].content.value))
    vista6 = mision.build(page, refresh, 6, estado_local)
    clic(boton(vista6, "✅ Completar Dimensión 6"))
    check("D6: subió a nivel 7", progreso()["nivel"] == 7)

    # ================= D7: Mercado de Suscripciones =================
    jugar_dimension(7, boton_guardar="Guardar suscripción")

    # ================= D8: Salón de Estrategas =================
    estado_local = {}
    vista8 = mision.build(page, refresh, 8, estado_local)
    clic(boton(vista8, "Activar"))  # primer perfil de la lista
    check("D8: perfil activado con clic", mision.REQUISITOS[8][1]())
    vista8 = mision.build(page, refresh, 8, estado_local)
    clic(boton(vista8, "✅ Completar Dimensión 8"))
    check("D8: nivel 8 y juego completado", progreso()["nivel"] == 8
          and progreso()["juego_completado"])

    # ================= Iteración: rejugar D3 con premio =================
    puntos_antes = obtener_puntos()
    vista3r = mision.build(page, refresh, 3, {})
    btn_rejugar = boton(vista3r, "🔁 Rejugar Dimensión 3 · +150 pts")
    check("D3 ya completada muestra botón de rejugar", not btn_rejugar.disabled)
    clic(btn_rejugar)
    check("Rejugar D3 suma 150 pts y mantiene nivel 8",
          obtener_puntos() == puntos_antes + 150
          and progreso()["nivel"] == 8)

    # ================= Estado final =================
    prog = progreso()
    check("Final: 8/8, nivel 8, juego completado",
          prog["dimensiones_completadas"] == 8 and prog["nivel"] == 8
          and prog["juego_completado"])
    check("Final: 3750 puntos (3600 + 150) y 1875 XP",
          obtener_puntos() == 3750
          and prog["puntos_experiencia"] == 1875,
          f"{obtener_puntos()} pts / {prog['puntos_experiencia']} XP")
    badges = [b for b in listar_badges() if b["desbloqueado"]]
    check("Final: 6 badges desbloqueados", len(badges) == 6,
          ", ".join(b["nombre"] for b in badges))

    # ================= Imágenes: todas las referencias existen =================
    mapa = dimensiones.build(page, refresh, lambda n: None)
    todas_las_imagenes.extend(imagenes_referenciadas(mapa))
    todas_las_imagenes.extend(imagenes_referenciadas(resumen.build(page, refresh)))
    todas_las_imagenes.extend(imagenes_referenciadas(personaje.build(page, refresh)))
    v_dist = distribucion.build(page, refresh)
    check("Vista Distribución construye con la partida completa",
          isinstance(v_dist, ft.Column) and len(v_dist.controls) > 3)
    for d in range(1, 9):
        vista_d = mision.build(page, refresh, d, {})
        todas_las_imagenes.extend(imagenes_referenciadas(vista_d))
        # Regresión: al entrar a la dimensión se ve su fondo (paisaje).
        info = info_dimension(d)
        src_esperado = ui.ruta_asset(FONDOS[info["fondo"]])
        fondos_en_vista = [
            c.image.src for c in caminar(vista_d)
            if getattr(c, "image", None) is not None
            and isinstance(c.image, ft.DecorationImage)
        ]
        check(f"D{d}: la misión muestra su fondo al entrar",
              src_esperado in fondos_en_vista,
              src_esperado)
        todas_las_imagenes.append(ui.ruta_asset(info["cofre_imagen"]))
        fondo = FONDOS.get(info["fondo"])
        if fondo:
            todas_las_imagenes.append(ui.ruta_asset(fondo))
    for b in listar_badges():
        if b["imagen"]:
            todas_las_imagenes.append(ui.ruta_asset(b["imagen"]))

    faltantes = sorted({s for s in todas_las_imagenes if not existe_asset(s)})
    check("Todas las imágenes referenciadas existen en assets/",
          not faltantes, ", ".join(faltantes) if faltantes else
          f"{len(set(todas_las_imagenes))} imágenes verificadas")

    # ================= main() arranca y navega =================
    import src.main as app_main
    page2 = MockPage()
    app_main.main(page2)
    check("main() construye la app sin errores", bool(page2.agregados))
    check("Ventana tamaño smartphone (390x844)",
          page2.window_width == 390 and page2.window_height == 844)
    nav = next(c for c in caminar(page2.agregados[0])
               if isinstance(c, ft.NavigationBar))
    check("Navegación inferior con las 8 secciones",
          len(nav.destinations) == 8)
    for idx, nombre in ((1, "resumen"), (2, "personaje"), (3, "calendario"),
                        (4, "distribucion"), (5, "deuda"), (6, "presupuesto"),
                        (7, "config"), (0, "dimensiones")):
        antes = page2.updates
        nav.on_change(Evt(control=type("C", (), {"selected_index": idx})()))
        check(f"Navegación a '{nombre}' sin errores y refresca la vista",
              page2.updates > antes)

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
