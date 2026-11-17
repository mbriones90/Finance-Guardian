"""Diálogos compartidos para editar/eliminar registros.

Los usan la sección Presupuesto (movimientos del período) y todas las
dimensiones: cualquier registro previo se puede corregir o borrar, y el
balance de la cuenta se ajusta solo en los servicios.
"""

import flet as ft

from src.services import (
    CATEGORIAS_GASTO,
    CATEGORIA_DEFAULT,
    editar_cuenta,
    editar_gasto,
    editar_ingreso,
    editar_suscripcion,
)
from src.ui import components as ui


def cerrar_dialogo(page, dlg):
    """Cierra el diálogo (compatible con el MockPage de las pruebas)."""
    if hasattr(page, "pop_dialog"):
        page.pop_dialog()
    else:
        dlg.open = False
        page.update()


def botones_edicion(on_edit, on_delete) -> list:
    """Par de iconos ✏️/🗑 estándar para las listas de registros."""
    return [
        ft.IconButton(ft.Icons.EDIT, icon_size=16, tooltip="Editar",
                      on_click=on_edit),
        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16,
                      tooltip="Eliminar", icon_color=ft.Colors.RED_400,
                      on_click=on_delete),
    ]


def dialogo_confirmar_borrado(page, refresh, texto, on_confirmar):
    """Abre un diálogo de confirmación de borrado (factory para on_click)."""
    def fn(e):
        def confirmar(ev):
            try:
                on_confirmar()
                cerrar_dialogo(page, dlg)
                refresh()
            except ValueError as err:
                cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, err)

        dlg = ft.AlertDialog(
            title=ft.Text("🗑 Eliminar registro"),
            content=ft.Column([
                ft.Text(texto, size=13),
                ft.Text("El balance de la cuenta se corrige solo.",
                        size=12, color=ft.Colors.GREY_600),
                ft.Row([ft.Button("Eliminar", icon=ft.Icons.DELETE,
                                  color=ft.Colors.RED_600,
                                  on_click=confirmar),
                        ft.TextButton("Cancelar", on_click=lambda ev2:
                                      cerrar_dialogo(page, dlg))],
                       spacing=8),
            ], tight=True, width=340, spacing=8),
        )
        page.show_dialog(dlg)
    return fn


def _dropdown_categorias(valor: str) -> ft.Dropdown:
    return ft.Dropdown(
        label="Categoría",
        options=[ft.dropdown.Option(c, c) for c in CATEGORIAS_GASTO],
        value=valor if valor in CATEGORIAS_GASTO else CATEGORIA_DEFAULT,
        width=260,
    )


def _dropdown_moneda(valor: str = "MXN") -> ft.Dropdown:
    return ft.Dropdown(
        label="Moneda",
        options=[ft.dropdown.Option("MXN", "MXN"),
                 ft.dropdown.Option("USD", "USD")],
        value=valor, width=110,
    )


def dialogo_editar_gasto(page, refresh, g):
    """Diálogo para editar un gasto previo (factory para on_click)."""
    def fn(e):
        cat = _dropdown_categorias(g["categoria"])
        monto = ft.TextField(label="Monto", value=str(g["monto"]),
                             keyboard_type=ft.KeyboardType.NUMBER, width=130)
        moneda = _dropdown_moneda(g["moneda"])
        desc = ft.TextField(label="Descripción",
                            value=g["descripcion"] or "", width=260)
        fecha = ft.TextField(label="Fecha (AAAA-MM-DD)", value=g["fecha"],
                             width=160)

        def guardar(ev):
            try:
                editar_gasto(g["id"], categoria=cat.value,
                             monto=float(monto.value or 0),
                             moneda=moneda.value,
                             descripcion=desc.value or "",
                             fecha=fecha.value or g["fecha"])
                cerrar_dialogo(page, dlg)
                refresh()
            except (ValueError, TypeError) as err:
                cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, ValueError(str(err)))

        dlg = ft.AlertDialog(
            title=ft.Text("✏️ Editar gasto"),
            content=ft.Column([
                cat, ft.Row([monto, moneda], spacing=8), desc, fecha,
                ft.Row([ft.Button("Guardar cambios", icon=ft.Icons.SAVE,
                                  on_click=guardar),
                        ft.TextButton("Cancelar", on_click=lambda ev2:
                                      cerrar_dialogo(page, dlg))],
                       spacing=8),
            ], tight=True, width=340, spacing=8),
        )
        page.show_dialog(dlg)
    return fn


def dialogo_editar_ingreso(page, refresh, i):
    """Diálogo para editar un ingreso previo (factory para on_click)."""
    def fn(e):
        cat = ft.TextField(label="Categoría", value=i["categoria"], width=260)
        monto = ft.TextField(label="Monto", value=str(i["monto"]),
                             keyboard_type=ft.KeyboardType.NUMBER, width=130)
        moneda = _dropdown_moneda(i["moneda"])
        desc = ft.TextField(label="Descripción",
                            value=i["descripcion"] or "", width=260)
        fecha = ft.TextField(label="Fecha (AAAA-MM-DD)", value=i["fecha"],
                             width=160)
        extra = []
        if i["tipo"] == "sueldo_recurrente":
            dia = ft.TextField(label="Día de cobro (1-31)",
                               value=str(i.get("dia_cobro") or ""),
                               keyboard_type=ft.KeyboardType.NUMBER, width=150)
            frec = ft.Dropdown(
                label="Frecuencia",
                options=[ft.dropdown.Option("mensual", "Mensual"),
                         ft.dropdown.Option("quincenal", "Quincenal"),
                         ft.dropdown.Option("semanal", "Semanal")],
                value=i.get("frecuencia") or "mensual", width=150)
            extra = [ft.Row([dia, frec], spacing=8)]

        def guardar(ev):
            try:
                kwargs = {}
                if i["tipo"] == "sueldo_recurrente":
                    kwargs = {
                        "dia_cobro": int(dia.value) if dia.value else None,
                        "frecuencia": frec.value,
                    }
                editar_ingreso(i["id"], categoria=cat.value,
                               monto=float(monto.value or 0),
                               moneda=moneda.value,
                               descripcion=desc.value or "",
                               fecha=fecha.value or i["fecha"], **kwargs)
                cerrar_dialogo(page, dlg)
                refresh()
            except (ValueError, TypeError) as err:
                cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, ValueError(str(err)))

        dlg = ft.AlertDialog(
            title=ft.Text("✏️ Editar ingreso"),
            content=ft.Column([
                cat, ft.Row([monto, moneda], spacing=8), desc, fecha,
                *extra,
                ft.Row([ft.Button("Guardar cambios", icon=ft.Icons.SAVE,
                                  on_click=guardar),
                        ft.TextButton("Cancelar", on_click=lambda ev2:
                                      cerrar_dialogo(page, dlg))],
                       spacing=8),
            ], tight=True, width=340, spacing=8),
        )
        page.show_dialog(dlg)
    return fn


def dialogo_editar_cuenta(page, refresh, c):
    """Diálogo para editar nombre y saldo/deuda de una cuenta o tarjeta."""
    def fn(e):
        nombre = ft.TextField(label="Nombre", value=c["nombre"], width=240)
        etiqueta_balance = ("Saldo" if c["tipo"] == "cuenta"
                            else "Deuda actual")
        balance = ft.TextField(label=etiqueta_balance,
                               value=str(c["balance_actual"]),
                               keyboard_type=ft.KeyboardType.NUMBER, width=160)

        def guardar(ev):
            try:
                editar_cuenta(c["id"], nombre=nombre.value,
                              balance=float(balance.value or 0))
                cerrar_dialogo(page, dlg)
                refresh()
            except (ValueError, TypeError) as err:
                cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, ValueError(str(err)))

        dlg = ft.AlertDialog(
            title=ft.Text("✏️ Editar cuenta"),
            content=ft.Column([
                nombre, balance,
                ft.Row([ft.Button("Guardar cambios", icon=ft.Icons.SAVE,
                                  on_click=guardar),
                        ft.TextButton("Cancelar", on_click=lambda ev2:
                                      cerrar_dialogo(page, dlg))],
                       spacing=8),
            ], tight=True, width=320, spacing=8),
        )
        page.show_dialog(dlg)
    return fn


def dialogo_editar_suscripcion(page, refresh, s):
    """Diálogo para editar una suscripción previa."""
    def fn(e):
        nombre = ft.TextField(label="Servicio", value=s["nombre"], width=240)
        monto = ft.TextField(label="Monto", value=str(s["monto"]),
                             keyboard_type=ft.KeyboardType.NUMBER, width=130)
        moneda = _dropdown_moneda(s["moneda"])
        dia = ft.TextField(label="Día de cobro (1-31)",
                           value=str(s["dia_cobro"]),
                           keyboard_type=ft.KeyboardType.NUMBER, width=150)
        periodo = ft.Dropdown(
            label="Periodo",
            options=[ft.dropdown.Option("mensual", "Mensual"),
                     ft.dropdown.Option("anual", "Anual")],
            value=s["periodo"], width=140)

        def guardar(ev):
            try:
                editar_suscripcion(s["id"], {
                    "nombre": nombre.value or s["nombre"],
                    "monto": float(monto.value or 0),
                    "moneda": moneda.value,
                    "dia_cobro": int(dia.value or s["dia_cobro"]),
                    "periodo": periodo.value,
                })
                cerrar_dialogo(page, dlg)
                refresh()
            except (ValueError, TypeError) as err:
                cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, ValueError(str(err)))

        dlg = ft.AlertDialog(
            title=ft.Text("✏️ Editar suscripción"),
            content=ft.Column([
                nombre, ft.Row([monto, moneda], spacing=8),
                ft.Row([dia, periodo], spacing=8),
                ft.Row([ft.Button("Guardar cambios", icon=ft.Icons.SAVE,
                                  on_click=guardar),
                        ft.TextButton("Cancelar", on_click=lambda ev2:
                                      cerrar_dialogo(page, dlg))],
                       spacing=8),
            ], tight=True, width=340, spacing=8),
        )
        page.show_dialog(dlg)
    return fn
