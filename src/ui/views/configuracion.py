"""Vista Configuración: todo lo ajustable del Guardián y de la app.

Aquí vive lo que antes estaba en la sección Personaje:
- Configuración general (nombre del Guardián y tipo de cambio USD→MXN).
- Perfil de pago activo (la estrategia; solo se cambia aquí).
- Inventario de armaduras, fondos y badges.

La sección Personaje queda solo para el avatar y su estado financiero.
"""

import flet as ft

from src.services import (
    activar_perfil,
    configurar_personaje,
    desbloquear_armadura,
    equipar_armadura,
    get_tipo_cambio,
    listar_armaduras,
    listar_badges,
    listar_perfiles,
    obtener_perfil_activo,
    obtener_puntos,
    progreso,
)
from src.services.inventario import listar_fondos
from src.ui import components as ui


def build(page: ft.Page, refresh) -> ft.Column:
    prog = progreso()
    puntos = obtener_puntos()

    # ---------- Configuración general ----------
    nombre = ft.TextField(label="Nombre del Guardián", value=prog["nombre"],
                          width=240)
    tc = ft.TextField(label="Tipo de cambio USD→MXN",
                      value=str(get_tipo_cambio()),
                      width=180, keyboard_type=ft.KeyboardType.NUMBER)

    def guardar_config(e):
        try:
            configurar_personaje(
                nombre=nombre.value,
                tipo_cambio=float(tc.value or 18.63),
            )
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    config = ft.Column([
        ui.subtitulo("⚙️ General"),
        ft.Row([nombre, tc,
                ft.Button("Guardar", icon=ft.Icons.SAVE, on_click=guardar_config)],
               wrap=True, spacing=10),
    ], spacing=8)

    # ---------- Perfil de pago (estrategia; solo se cambia aquí) ----------
    DESCRIPCION = {
        "minimo": "Paga solo el mínimo de cada tarjeta.",
        "optimizado": "Protege tu liquidez y las suscripciones.",
        "agresivo": "Liquida rápido manteniendo una reserva de flujo.",
        "custom": "Tu dashboard a la medida.",
    }
    activo = obtener_perfil_activo()

    def cambiar_perfil(perfil_id):
        def fn(e):
            activar_perfil(perfil_id)
            refresh()
        return fn

    filas_perfiles = []
    for p in listar_perfiles():
        es_activo = activo and p["id"] == activo["id"]
        filas_perfiles.append(ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if es_activo
                        else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        color=ft.Colors.GREEN_700 if es_activo
                        else ft.Colors.GREY_500),
                ft.Column([
                    ft.Text(p["nombre"], size=13, weight="bold"),
                    ft.Text(DESCRIPCION.get(p["tipo_perfil"], ""), size=11,
                            color=ft.Colors.GREY_600),
                ], spacing=1, expand=True),
                ft.Text("Activo ✅", size=12, color=ft.Colors.GREEN_700)
                if es_activo else
                ft.Button("Activar", on_click=cambiar_perfil(p["id"]),
                          width=110),
            ]),
            bgcolor=ft.Colors.GREEN_50 if es_activo else ft.Colors.GREY_50,
            border_radius=10, padding=8,
        ))

    panel_perfil = ft.Column([
        ui.subtitulo("⚔️ Perfil de pago (tu estrategia)"),
        ft.Text("Define cómo atacas la deuda cada mes. El dashboard del "
                "Resumen se arma con los módulos del perfil activo. Sus "
                "parámetros se ajustan en la Dimensión 8.",
                size=12, color=ft.Colors.GREY_600),
        *filas_perfiles,
    ], spacing=6)

    # ---------- Inventario de armaduras ----------
    def boton_armadura(a):
        if a["equipada"]:
            return ft.Text("Equipada ✅", size=12, color=ft.Colors.GREEN_700)
        if a["desbloqueada"]:
            return ft.Button("Equipar", on_click=lambda e, c=a["calidad"]: (
                equipar_armadura(c), refresh()), width=100)
        if a["costo"] <= puntos:
            return ft.Button(f"Desbloquear {a['costo']} pts",
                             on_click=lambda e, c=a["calidad"]: _desbloquear(c),
                             width=150)
        return ft.Text(f"🔒 {a['costo']} pts", size=12, color=ft.Colors.GREY_600)

    def _desbloquear(calidad):
        try:
            desbloquear_armadura(calidad)
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    filas_armadura = []
    for a in listar_armaduras():
        filas_armadura.append(ft.Row([
            ft.Text(a["nombre"], size=13, width=170),
            ft.Text(a["calidad"], size=12, width=80,
                    color=ft.Colors.AMBER_700),
            ft.Container(boton_armadura(a), width=160),
        ]))

    inventario = ft.Column([
        ui.subtitulo("🛡️ Armaduras"),
        ft.Text(f"Puntos: {puntos}", size=13),
        *filas_armadura,
    ], spacing=6)

    # ---------- Fondos ----------
    fondo_sel = ft.Dropdown(
        label="Fondo",
        options=[ft.dropdown.Option(f["nombre"]) for f in listar_fondos()],
        value=prog["fondo"],
        width=240,
    )

    def cambiar_fondo(e):
        try:
            configurar_personaje(fondo=fondo_sel.value)
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    fondos = ft.Column([
        ui.subtitulo("🖼️ Fondo"),
        ft.Row([fondo_sel,
                ft.Button("Cambiar", icon=ft.Icons.WALLPAPER, on_click=cambiar_fondo)],
               wrap=True),
    ], spacing=8)

    # ---------- Badges ----------
    badges = listar_badges()
    badges_fila = []
    for b in badges:
        opacidad = 1.0 if b["desbloqueado"] else 0.25
        badges_fila.append(ft.Container(
            content=ft.Column([
                ft.Image(src=ui.ruta_asset(b["imagen"]), width=64, height=64,
                         fit=ft.BoxFit.CONTAIN, opacity=opacidad),
                ft.Text(b["nombre"], size=10),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            tooltip=b["descripcion"],
        ))

    panel_badges = ft.Column([
        ui.subtitulo("🏅 Badges"),
        ft.Row(badges_fila, wrap=True, spacing=6, run_spacing=6),
    ], spacing=8)

    return ft.Column(
        [ui.titulo("⚙️ Configuración"), config, ft.Divider(), panel_perfil,
         ft.Divider(), inventario, ft.Divider(), fondos,
         ft.Divider(), panel_badges],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )
