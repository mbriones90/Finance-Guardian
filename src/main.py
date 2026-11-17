"""Punto de entrada de la aplicación.

Shell de navegación: Dimensiones (mapa del camino A→B), Resumen financiero
y Personaje. La progresión son los niveles del personaje (completar cada
dimensión sube un nivel y abre el siguiente portal).
"""

import os
import sys

# Permite ejecutar como `python src/main.py` (el directorio raíz del
# proyecto debe estar en sys.path para los imports `src.*`).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import flet as ft

from src.database import init_db
from src.ui.theme import COLORS, PIXEL_FONT, get_theme
from src.ui.views import (
    calendario,
    configuracion,
    dimensiones,
    distribucion,
    deuda,
    mision,
    personaje,
    presupuesto,
    resumen,
)

VISTAS = {"dimensiones", "resumen", "personaje", "calendario", "distribucion",
          "deuda", "presupuesto", "config"}


def main(page: ft.Page):
    init_db()

    page.title = "Finanzas - Dimensiones del Guardián"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = get_theme()
    # Estilo retro 8 bits: fuente pixel para títulos y fondo pergamino.
    page.fonts = {PIXEL_FONT: "fuentes/PressStart2P-Regular.ttf"}
    page.bgcolor = COLORS["background"]
    page.padding = 0
    # Ventana tamaño smartphone: la UI ya nace pensada para móvil
    # (navegación inferior, tarjetas apiladas, tablas con scroll lateral).
    page.window_width = 390
    page.window_height = 844

    state = {"vista": "dimensiones", "mision": None}
    estado_local: dict = {}
    estado_calendario: dict = {}  # modo y fecha persisten al navegar
    estado_deuda: dict = {}       # estrategia seleccionada para proyectar
    estado_presupuesto: dict = {} # tipo (semanal/mensual) y período vistos

    content = ft.Column(expand=True)

    def refresh(destino: str | None = None):
        if destino in VISTAS:
            state["vista"] = destino
        content.controls.clear()
        if state["vista"] == "mision" and state["mision"]:
            content.controls.append(
                mision.build(page, refresh, state["mision"], estado_local))
        elif state["vista"] == "personaje":
            content.controls.append(personaje.build(page, refresh))
        elif state["vista"] == "resumen":
            content.controls.append(resumen.build(page, refresh))
        elif state["vista"] == "calendario":
            content.controls.append(
                calendario.build(page, refresh, estado_calendario))
        elif state["vista"] == "distribucion":
            content.controls.append(distribucion.build(page, refresh))
        elif state["vista"] == "deuda":
            content.controls.append(deuda.build(page, refresh, estado_deuda))
        elif state["vista"] == "presupuesto":
            content.controls.append(
                presupuesto.build(page, refresh, estado_presupuesto))
        elif state["vista"] == "config":
            content.controls.append(configuracion.build(page, refresh))
        else:
            content.controls.append(dimensiones.build(page, refresh, abrir_mision))
        page.update()

    def abrir_mision(n: int):
        state["vista"] = "mision"
        state["mision"] = n
        refresh()

    def navegar(e):
        idx = e.control.selected_index
        destino = {0: "dimensiones", 1: "resumen", 2: "personaje",
                   3: "calendario", 4: "distribucion", 5: "deuda",
                   6: "presupuesto", 7: "config"}.get(idx)
        state["mision"] = None
        refresh(destino)

    # Barra de navegación inferior (patrón móvil). La etiqueta solo se
    # muestra en el destino activo para que quepan las 7 secciones.
    nav = ft.NavigationBar(
        selected_index=0,
        label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.MAP, label="Dimensiones"),
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD, label="Resumen"),
            ft.NavigationBarDestination(icon=ft.Icons.PERSON, label="Personaje"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH,
                                        label="Calendario"),
            ft.NavigationBarDestination(icon=ft.Icons.PIE_CHART,
                                        label="Gastos"),
            ft.NavigationBarDestination(icon=ft.Icons.TRENDING_DOWN,
                                        label="Deuda"),
            ft.NavigationBarDestination(icon=ft.Icons.SAVINGS,
                                        label="Presupuesto"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS,
                                        label="Config"),
        ],
        on_change=navegar,
    )

    page.add(
        ft.Column(
            [
                ft.Container(content, padding=14, expand=True),
                nav,
            ],
            spacing=0,
            expand=True,
        )
    )
    refresh()


if __name__ == "__main__":
    # Ruta absoluta a los assets: Flet resuelve "assets" relativo al
    # directorio del script (src/), no a la raíz del proyecto, así que
    # sin esta ruta explícita las imágenes no cargan (cuadros grises).
    ft.run(main, assets_dir=os.path.join(BASE_DIR, "assets"))
