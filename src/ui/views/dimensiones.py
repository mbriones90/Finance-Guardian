"""Vista del mapa de dimensiones: el viaje del Punto A al Punto B.

El terreno y el clima cambian con el fondo de cada dimensión (Fase 3).
Cada dimensión muestra su estado: completada, actual (desbloqueada) o
bloqueada (se adelanta completando la anterior — niveles del personaje).
"""

import flet as ft

from src.services import estado_progresion, obtener_puntos
from src.services.inventario import FONDOS
from src.ui import components as ui
from src.ui.theme import COLORS


def _estado_chip(dim: dict, nivel_actual: int) -> tuple:
    if dim["completada"]:
        return "✅ Completada", ft.Colors.GREEN_50, ft.Colors.GREEN_700
    if dim["n"] == nivel_actual:
        return "🔥 Actual", ft.Colors.AMBER_100, COLORS["primary"]
    return "🔒 Nivel insuficiente", ft.Colors.GREY_100, ft.Colors.GREY_600


def build(page: ft.Page, refresh, on_open_mission) -> ft.Column:
    estado = estado_progresion()
    prog = estado["personaje"]
    dim_actual = next(
        (d for d in estado["dimensiones"] if d["n"] == prog["dimension_actual"]),
        None,
    )

    encabezado = ft.Row(
        [
            ft.Text(f"⭐ {prog['nombre']}", size=20, weight="bold"),
            ft.Text(f"Nivel {prog['nivel']}", size=18, weight="bold",
                    color=COLORS["primary"]),
            ft.Text(f"🪙 {obtener_puntos()} pts"),
            ft.Text(f"✨ {prog['puntos_experiencia']} XP"),
        ],
        spacing=16,
        wrap=True,
    )

    if dim_actual:
        etiqueta, fondo_color, texto_color = _estado_chip(dim_actual, prog["nivel"])
        fondo_img = FONDOS.get(dim_actual["fondo"])
        camino = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Text(f"Dimensión {dim_actual['n']}: "
                                    f"{dim_actual['nombre']}", size=18, weight="bold",
                                    color=ft.Colors.WHITE),
                            ft.Container(
                                ft.Text(etiqueta, size=12, color=ft.Colors.WHITE),
                                bgcolor=texto_color, border_radius=8, padding=6,
                            )],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(dim_actual["mision"], size=14, color=ft.Colors.WHITE),
                    ft.Row(
                        [
                            ft.Text("Punto A", size=12, italic=True,
                                    color=ft.Colors.WHITE70),
                            ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.WHITE),
                            ft.Text(f"Punto B · Nivel {dim_actual['n'] + 1}",
                                    size=12, italic=True, color=ft.Colors.WHITE),
                        ],
                        spacing=8,
                    ),
                    ft.Button(
                        "Entrar a la dimensión",
                        icon=ft.Icons.TRAVEL_EXPLORE,
                        on_click=lambda e, n=dim_actual["n"]: on_open_mission(n),
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            border_radius=16,
            image=ft.DecorationImage(src=ui.ruta_asset(fondo_img),
                                     fit=ft.BoxFit.COVER)
            if fondo_img else None,
            bgcolor=fondo_color,
            height=210,
            expand=True,
        )
    else:
        camino = ft.Container(
            content=ft.Text("🏆 ¡Guardián Supremo! Todas las dimensiones conquistadas.",
                            size=16, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.PURPLE_700, padding=20, border_radius=16, expand=True,
        )

    chips = []
    for d in estado["dimensiones"]:
        etiqueta, fondo, color_texto = _estado_chip(d, prog["nivel"])
        chips.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"D{d['n']}", size=11, weight="bold"),
                        ft.Image(src=ui.ruta_asset(d["cofre_imagen"]), width=42, height=42,
                                 fit=ft.BoxFit.CONTAIN),
                        ft.Text(d["nombre"], size=10, color=ft.Colors.GREY_700),
                        ft.Text(etiqueta, size=9, color=color_texto),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                bgcolor=fondo,
                border_radius=10,
                padding=8,
                width=104,
                height=128,
                on_click=(None if d["n"] != prog["nivel"] and not d["desbloqueada"]
                          else lambda e, n=d["n"]: on_open_mission(n)),
            )
        )

    return ft.Column(
        [encabezado, ft.Divider(), camino,
         ui.subtitulo("Camino de dimensiones"),
         ft.Row(chips, wrap=True, spacing=8, run_spacing=8)],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
    )
