"""Componentes reutilizables de UI (Flet)."""

import asyncio

import flet as ft

from src.ui.sonido import reproducir
from src.ui.theme import COLORS, PIXEL_FONT


def ruta_asset(ruta: str | None) -> str | None:
    """Convierte rutas guardadas como ``assets/...`` al src que Flet espera.

    ``ft.run`` sirve el directorio ``assets`` (assets_dir por defecto), así
    que el src debe ser relativo a esa carpeta: ``assets/fondos/x.png`` →
    ``fondos/x.png``. Sin esta conversión la imagen no carga (cuadro gris).
    """
    if ruta and ruta.startswith("assets/"):
        return ruta[len("assets/"):]
    return ruta


def titulo(texto: str) -> ft.Text:
    return ft.Text(texto, size=15, weight="bold", color=COLORS["primary"],
                   font_family=PIXEL_FONT)


def subtitulo(texto: str) -> ft.Text:
    return ft.Text(texto, size=10, weight="bold", color=COLORS["ink"],
                   font_family=PIXEL_FONT)


def separador() -> ft.Divider:
    return ft.Divider()


def _borde(color=None, ancho: int = 2) -> ft.Border:
    """Borde grueso estilo cuadro de diálogo de 8 bits."""
    lado = ft.BorderSide(ancho, color or COLORS["ink"])
    return ft.Border(top=lado, right=lado, bottom=lado, left=lado)


def stat_card(titulo_card: str, valor: str, color=None) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [ft.Text(titulo_card, size=11, color=COLORS["secondary"]),
             ft.Text(valor, size=13, weight="bold", color=COLORS["ink"],
                     font_family=PIXEL_FONT)],
            spacing=4,
        ),
        bgcolor=COLORS["surface"],
        border_radius=4,
        padding=12,
        border=_borde(),
    )


SEMAFORO_ESTILO = {
    "verde": ("✅", ft.Colors.GREEN_600),
    "amarillo": ("⚠️", ft.Colors.AMBER_700),
    "rojo": ("🚨", ft.Colors.RED_600),
}


def fila_alerta(nivel: str, mensaje: str) -> ft.Row:
    icono, color = SEMAFORO_ESTILO.get(nivel, ("ℹ️", ft.Colors.BLUE_600))
    return ft.Row([ft.Text(icono, size=14), ft.Text(mensaje, size=13, color=color)])


def mostrar_alerta_error(page: ft.Page, error: ValueError) -> None:
    reproducir("error", page)
    dlg = ft.AlertDialog(
        title=ft.Text("No se pudo completar", color=ft.Colors.RED_600),
        content=ft.Text(str(error)),
    )
    page.show_dialog(dlg)


def dialogo_cofre(page: ft.Page, payload: dict) -> None:
    """Diálogo de celebración al abrir un cofre (estilo Zelda).

    - El cofre entra con animación de escala (rebote).
    - Suena el arpégio del cofre y, medio segundo después, la fanfarria
      de nivel (ambos sintetizados, ver scripts/generar_sonidos.py).
    """
    badge = payload.get("badge")

    cofre = ft.Container(
        content=ft.Image(src=ruta_asset(payload["cofre_imagen"]), width=180, height=180,
                         fit=ft.BoxFit.CONTAIN),
        scale=0.2,
        animate_scale=ft.Animation(750, ft.AnimationCurve.BOUNCE_OUT),
    )

    contenido = [
        ft.Row([ft.Text("✨", size=22), cofre, ft.Text("🎉", size=22)],
               alignment=ft.MainAxisAlignment.CENTER),
        ft.Text(f"Dimensión {payload['dimension']}: {payload['nombre_dimension']}",
                size=16, weight="bold"),
        ft.Text(f"🪙 +{payload['puntos_ganados']} puntos   ⭐ +{payload['xp_ganada']} XP",
                size=14),
    ]
    if badge and badge.get("nuevo"):
        b = badge["badge"]
        contenido.append(
            ft.Row([ft.Image(src=ruta_asset(b["imagen"]), width=48, height=48,
                             fit=ft.BoxFit.CONTAIN),
                    ft.Text(f"Badge nuevo: {b['nombre']}", size=13)])
        )
    contenido.append(ft.Text(payload["mensaje"], size=14, weight="bold",
                             color=COLORS["primary"]))

    dlg = ft.AlertDialog(
        title=ft.Text("🎉 ¡Cofre conseguido!", size=18, weight="bold"),
        content=ft.Column(contenido, tight=True, width=360),
    )

    async def _animar_y_sonar():
        await asyncio.sleep(0.05)
        cofre.scale = 1.0
        try:
            cofre.update()
        except Exception:  # noqa: BLE001 (control aún no renderizado)
            pass
        reproducir("cofre", page)
        await asyncio.sleep(0.65)
        reproducir("nivel", page)

    if hasattr(page, "run_task"):
        page.run_task(_animar_y_sonar)
    else:
        reproducir("cofre", page)

    page.show_dialog(dlg)
