"""Tema visual retro 8 bits de la app.

Inspirado en los RPG de NES/Game Boy:
- Fuente pixel "Press Start 2P" en títulos y cifras (assets/fuentes).
- Texto general monoespaciado (legible en pantalla de teléfono).
- Paleta pergamino + tinta oscura, bordes gruesos de 2 px y esquinas
  casi cuadradas, como los cuadros de diálogo de 8 bits.
"""

import flet as ft

PIXEL_FONT = "PressStart2P"

COLORS = {
    "primary": "#8C5A0A",        # ámbar oscuro RPG
    "secondary": "#7A6A4F",      # café pergamino
    "background": "#EFE3C2",     # pergamino claro (pantalla de juego)
    "surface": "#FFF6DC",        # cuadros de diálogo
    "ink": "#2B2320",            # tinta oscura para bordes/texto
    "risk_red": "#C0392B",
    "risk_amber": "#D8910F",
    "risk_green": "#2E8B57",
}


def get_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=COLORS["primary"],
        font_family="monospace",
        scaffold_bgcolor=COLORS["background"],
    )
