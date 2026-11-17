"""Vista Personaje: el avatar del Guardián según tu estado financiero.

El pixel-art del Guardián cambia con tus finanzas (ver ``estado_guardian``):
- 🌟 Legendario: sin alertas, semana verde y sin deuda.
- 🛡️ Fuerte: todo en orden, con deuda bajo control.
- 🩹 Herido: alertas amarillas o semana cerca del límite.
- 🔥 En peligro: alertas rojas o presupuesto reventado.

Los ajustes (nombre, tipo de cambio, perfil, armaduras, fondos, badges)
viven en la sección Configuración.
"""

import flet as ft

from src.services import (
    deuda_total_pesos,
    efectivo_total_pesos,
    estado_guardian,
    obtener_puntos,
    progreso,
    TOTAL_DIMENSIONES,
)
from src.ui import components as ui


def build(page: ft.Page, refresh) -> ft.Column:
    prog = progreso()
    puntos = obtener_puntos()
    estado = estado_guardian()

    avatar = ft.Container(
        content=ft.Image(src=ui.ruta_asset(estado["imagen"]),
                         width=192, height=192, fit=ft.BoxFit.CONTAIN),
        alignment=ft.Alignment(0, 0),
    )

    tarjeta_estado = ft.Container(
        content=ft.Column([
            ft.Text(estado["titulo"], size=16, weight="bold"),
            ft.Text(estado["consejo"], size=13),
            ft.Text(f"Alertas: {estado['alertas_rojas']} rojas · "
                    f"{estado['alertas_amarillas']} amarillas · semana "
                    f"{estado['semaforo_semana']}", size=12,
                    color=ft.Colors.GREY_700),
        ], spacing=4),
        bgcolor=ft.Colors.WHITE,
        border=ui._borde(),
        border_radius=12,
        padding=12,
    )

    progreso_panel = ft.Column([
        ui.subtitulo("📈 Progresión"),
        ft.Text(f"Nivel {prog['nivel']} · "
                f"{prog['dimensiones_completadas']}/{TOTAL_DIMENSIONES} "
                f"dimensiones · {prog['puntos_experiencia']} XP · "
                f"🪙 {puntos} pts", size=14),
        ft.ProgressBar(value=min(
            1.0, prog["dimensiones_completadas"] / TOTAL_DIMENSIONES)),
        ft.Text("Rejuega cualquier dimensión para seguir ganando cofres.",
                size=11, italic=True, color=ft.Colors.GREY_600),
    ], spacing=6)

    finanzas = ft.Row([
        ui.stat_card("💵 Efectivo", f"${efectivo_total_pesos():,.2f}"),
        ui.stat_card("💳 Deuda", f"${deuda_total_pesos():,.2f}",
                     ft.Colors.RED_600),
    ], spacing=12, wrap=True)

    return ft.Column(
        [
            ui.titulo(f"👤 {prog['nombre']}"),
            avatar,
            tarjeta_estado,
            finanzas,
            progreso_panel,
            ft.Text("⚙️ Nombre, tipo de cambio, perfil, armaduras y fondos "
                    "se ajustan en Configuración.", size=11, italic=True,
                    color=ft.Colors.GREY_600),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
