"""Vista Presupuesto: planea tu semana/mes y confirma el cierre.

- **Semanal o mensual**: mismo panel, cambia con el selector y navega
  con las flechas a períodos pasados/futuros.
- **Gastos planeados**: añade o quita compras que piensas hacer; el
  disponible descuenta lo gastado y lo planeado pendiente.
- **Cierre del período**: cuando acaba, confirmas qué compras sí se
  hicieron (se registran como gasto real) y cuáles no; el resumen dice
  cuánto se gastó en cosas nuevas y si hubo ahorro o te pasaste.
- **Movimientos**: los gastos e ingresos reales del período se pueden
  editar o eliminar (el balance de la cuenta se corrige solo).
"""

from datetime import date

import flet as ft

from src.services import (
    CATEGORIAS_GASTO,
    CATEGORIA_DEFAULT,
    agregar_planeado,
    avanzar_periodo,
    cerrar_periodo,
    eliminar_gasto,
    eliminar_ingreso,
    inicio_periodo,
    listar_cuentas,
    listar_gastos_periodo,
    listar_ingresos,
    listar_planeados,
    marcar_planeado_gastado,
    marcar_planeado_omitido,
    obtener_cierre,
    quitar_planeado,
    rango_periodo,
    resumen_periodo,
)
from src.ui import components as ui, edicion

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre",
         "diciembre"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cerrar_dialogo(page, dlg):
    """Cierra el diálogo (compatible con el MockPage de las pruebas)."""
    edicion.cerrar_dialogo(page, dlg)


def _etiqueta_periodo(tipo: str, inicio: date) -> str:
    desde, hasta = rango_periodo(tipo, inicio)
    d, h = date.fromisoformat(desde), date.fromisoformat(hasta)
    if tipo == "semanal":
        return f"Semana {d.day} {MESES[d.month]} – {h.day} {MESES[h.month]}"
    return f"{MESES[d.month].capitalize()} {d.year}"


def _dropdown_cuentas() -> ft.Dropdown:
    cuentas = listar_cuentas()
    opciones = [ft.dropdown.Option(str(c["id"]), c["nombre"]) for c in cuentas]
    valor = str(cuentas[0]["id"]) if cuentas else None
    return ft.Dropdown(label="Cuenta", options=opciones or
                       [ft.dropdown.Option("", "— crea una cuenta en la D1 —")],
                       value=valor, width=260)


def _dropdown_categorias(valor: str = CATEGORIA_DEFAULT) -> ft.Dropdown:
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


def _panel(contenido, fondo=ft.Colors.WHITE) -> ft.Container:
    return ft.Container(
        content=ft.Column(contenido, spacing=6),
        bgcolor=fondo, border=ui._borde(), border_radius=12, padding=12,
    )


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------

def build(page: ft.Page, refresh, estado: dict) -> ft.Column:
    tipo = estado.get("tipo") or "semanal"
    inicio = date.fromisoformat(estado["inicio"]) if estado.get("inicio") \
        else inicio_periodo(tipo)
    estado["tipo"], estado["inicio"] = tipo, inicio.isoformat()

    resumen = resumen_periodo(tipo, inicio)
    planeados = listar_planeados(tipo, inicio)
    cierre = obtener_cierre(tipo, inicio)

    # ---------- Selector de período ----------
    def cambiar_tipo(e):
        elegido = e.control.selected
        if elegido:
            estado["tipo"] = elegido[0]
            estado["inicio"] = None  # vuelve al período actual del nuevo tipo
        refresh()

    def mover(n):
        def fn(e):
            estado["inicio"] = avanzar_periodo(tipo, inicio, n).isoformat()
            refresh()
        return fn

    selector = ft.SegmentedButton(
        segments=[ft.Segment(value="semanal", label="Semanal"),
                  ft.Segment(value="mensual", label="Mensual")],
        selected=[tipo],
        on_change=cambiar_tipo,
    )
    navegacion = ft.Row([
        ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Período anterior",
                      on_click=mover(-1)),
        ft.Text(_etiqueta_periodo(tipo, inicio), size=14, weight="bold"),
        ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Período siguiente",
                      on_click=mover(1)),
        ft.Text("(actual)" if inicio == inicio_periodo(tipo) else "",
                size=11, color=ft.Colors.GREY_600),
    ], spacing=4)

    # ---------- Panel de estado ----------
    icono_sem, color_sem = ui.SEMAFORO_ESTILO.get(
        resumen["semaforo"], ("ℹ️", ft.Colors.BLUE_600))
    pct = min(1.0, (resumen["gastado"] + resumen["planeado"])
              / resumen["limite"]) if resumen["limite"] > 0 else 0.0
    color_disponible = ft.Colors.GREEN_700 if resumen["disponible"] >= 0 \
        else ft.Colors.RED_600
    panel_estado = _panel([
        ft.Row([
            ui.stat_card("🎯 Límite", f"${resumen['limite']:,.2f}"),
            ui.stat_card("💸 Gastado", f"${resumen['gastado']:,.2f}"),
            ui.stat_card("📝 Planeado", f"${resumen['planeado']:,.2f}"),
            ui.stat_card("✨ Disponible", f"${resumen['disponible']:,.2f}",
                         color_disponible),
        ], spacing=12, wrap=True),
        ft.Row([
            ft.ProgressBar(value=pct, expand=True,
                           color=color_sem, bgcolor=ft.Colors.GREY_200),
            ft.Text(f"{icono_sem} {resumen['porcentaje']:.0f}%"
                    if resumen["porcentaje"] is not None else icono_sem,
                    size=12, color=color_sem),
        ], spacing=8),
        ft.Text("Disponible = límite − gastado − planeado pendiente.",
                size=11, italic=True, color=ft.Colors.GREY_600),
    ])

    # ---------- Gastos planeados ----------
    cat_nuevo = _dropdown_categorias()
    monto_nuevo = ft.TextField(label="Monto", value="0",
                               keyboard_type=ft.KeyboardType.NUMBER, width=130)
    desc_nuevo = ft.TextField(label="Descripción (opcional)", width=240)

    def anadir(e):
        try:
            agregar_planeado(tipo, cat_nuevo.value or CATEGORIA_DEFAULT,
                             float(monto_nuevo.value or 0),
                             descripcion=desc_nuevo.value or "",
                             inicio=inicio)
            refresh()
        except (ValueError, TypeError) as err:
            ui.mostrar_alerta_error(page, ValueError(str(err)))

    def dialogo_se_gasto(planeado):
        def fn(e):
            cuenta = _dropdown_cuentas()
            moneda = _dropdown_moneda()

            def confirmar(ev):
                try:
                    if not cuenta.value:
                        raise ValueError("Selecciona la cuenta del gasto.")
                    marcar_planeado_gastado(planeado["id"], int(cuenta.value),
                                            moneda.value or "MXN")
                    _cerrar_dialogo(page, dlg)
                    refresh()
                except (ValueError, TypeError) as err:
                    _cerrar_dialogo(page, dlg)
                    ui.mostrar_alerta_error(page, ValueError(str(err)))

            def cancelar(ev):
                _cerrar_dialogo(page, dlg)

            dlg = ft.AlertDialog(
                title=ft.Text(f"✓ Se gastó: {planeado['categoria']}"),
                content=ft.Column([
                    ft.Text(f"Se registrará un gasto real de "
                            f"${planeado['monto']:,.2f}.", size=13),
                    cuenta, moneda,
                    ft.Row([ft.Button("Confirmar gasto",
                                      icon=ft.Icons.CHECK, on_click=confirmar),
                            ft.TextButton("Cancelar", on_click=cancelar)],
                           spacing=8),
                ], tight=True, width=320, spacing=8),
            )
            page.show_dialog(dlg)
        return fn

    def omitir(planeado_id):
        def fn(e):
            try:
                marcar_planeado_omitido(planeado_id)
                refresh()
            except ValueError as err:
                ui.mostrar_alerta_error(page, err)
        return fn

    def quitar(planeado_id):
        def fn(e):
            try:
                quitar_planeado(planeado_id)
                refresh()
            except ValueError as err:
                ui.mostrar_alerta_error(page, err)
        return fn

    filas_planeados = []
    for p in planeados:
        if p["estado"] == "planeado":
            fila = ft.Row([
                ft.Text(f"• {p['categoria']}"
                        + (f" — {p['descripcion']}" if p["descripcion"] else ""),
                        size=13, expand=True),
                ft.Text(f"${p['monto']:,.2f}", size=13, weight="bold"),
                ft.Button("Se gastó", icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                          on_click=dialogo_se_gasto(p), height=32),
                ft.IconButton(ft.Icons.CANCEL_OUTLINED, icon_size=18,
                              tooltip="No se hizo",
                              on_click=omitir(p["id"])),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18,
                              tooltip="Quitar del plan",
                              icon_color=ft.Colors.RED_400,
                              on_click=quitar(p["id"])),
            ], spacing=4)
        else:
            marca = ("✅ se gastó" if p["estado"] == "gastado"
                     else "➖ no se hizo")
            fila = ft.Row([
                ft.Text(f"• {p['categoria']}", size=13, expand=True,
                        color=ft.Colors.GREY_600),
                ft.Text(f"${p['monto']:,.2f} · {marca}", size=12,
                        color=ft.Colors.GREY_600),
            ], spacing=4)
        filas_planeados.append(fila)

    panel_planeados = _panel([
        ui.subtitulo("📝 Gastos planeados"),
        ft.Row([cat_nuevo, monto_nuevo, desc_nuevo,
                ft.Button("Añadir", icon=ft.Icons.ADD, on_click=anadir,
                          height=40)],
               wrap=True, spacing=10),
        *(filas_planeados or [ft.Text("Nada planeado todavía. Añade las "
                                      "compras que piensas hacer.", size=13,
                                      color=ft.Colors.GREY_600)]),
    ])

    # ---------- Cierre del período ----------
    def confirmar_cierre(e):
        def hacer_cierre(ev):
            try:
                resultado = cerrar_periodo(tipo, inicio)
            except ValueError as err:
                _cerrar_dialogo(page, dlg)
                ui.mostrar_alerta_error(page, err)
                return
            _cerrar_dialogo(page, dlg)
            _dialogo_resultado_cierre(resultado)
            refresh()

        def cancelar(ev):
            _cerrar_dialogo(page, dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("🔒 Cerrar el período"),
            content=ft.Column([
                ft.Text(f"Límite ${resumen['limite']:,.2f} · "
                        f"gastado ${resumen['gastado']:,.2f} · "
                        f"planeado pendiente ${resumen['planeado']:,.2f}",
                        size=13),
                ft.Text("Los planeados pendientes quedarán como "
                        "«no se hizo». El cierre es definitivo.",
                        size=12, color=ft.Colors.GREY_600),
                ft.Row([ft.Button("Confirmar cierre", icon=ft.Icons.LOCK,
                                  on_click=hacer_cierre),
                        ft.TextButton("Todavía no", on_click=cancelar)],
                       spacing=8),
            ], tight=True, width=360, spacing=8),
        )
        page.show_dialog(dlg)

    def _dialogo_resultado_cierre(c):
        if c["resultado"] == "ahorro":
            titulo_txt = f"🎉 Ahorraste ${c['ahorro']:,.2f}"
            color = ft.Colors.GREEN_700
        elif c["resultado"] == "excedido":
            titulo_txt = f"🚨 Te pasaste por ${-c['ahorro']:,.2f}"
            color = ft.Colors.RED_600
        else:
            titulo_txt = "🎯 Gastaste justo el límite"
            color = ft.Colors.BLUE_700
        lineas = [
            ft.Text(f"Gastado ${c['gastado']:,.2f} de "
                    f"${c['limite']:,.2f}", size=13),
            ft.Text(f"• De lo planeado: ${c['planeados_total']:,.2f}", size=13),
            ft.Text(f"• Gastos nuevos (no planeados): "
                    f"${c['nuevos_total']:,.2f}", size=13),
        ]
        for premio in c.get("premios", []):
            lineas.append(ft.Text(
                f"🏰 ¡Masmorra derrotada! +{premio['puntos']} puntos.",
                size=13, weight="bold", color=ft.Colors.PURPLE_400))
        dlg = ft.AlertDialog(
            title=ft.Text(titulo_txt, color=color),
            content=ft.Column([*lineas,
                               ft.TextButton("Entendido",
                                             on_click=lambda ev:
                                             _cerrar_dialogo(page, dlg))],
                              tight=True, width=340, spacing=6),
        )
        page.show_dialog(dlg)

    if cierre:
        if cierre["resultado"] == "ahorro":
            resumen_cierre = (f"🎉 Cerrado con ahorro de "
                              f"${cierre['ahorro']:,.2f}")
        elif cierre["resultado"] == "excedido":
            resumen_cierre = (f"🚨 Cerrado excedido por "
                              f"${-cierre['ahorro']:,.2f}")
        else:
            resumen_cierre = "🎯 Cerrado justo en el límite"
        panel_cierre = _panel([
            ui.subtitulo("🔒 Cierre del período"),
            ft.Text(resumen_cierre, size=14, weight="bold"),
            ft.Text(f"Gastado ${cierre['gastado']:,.2f} de "
                    f"${cierre['limite']:,.2f} · planeado "
                    f"${cierre['planeados_total']:,.2f} · nuevos "
                    f"${cierre['nuevos_total']:,.2f}", size=12,
                    color=ft.Colors.GREY_700),
        ], fondo=ft.Colors.GREY_50)
    elif resumen["terminado"]:
        panel_cierre = _panel([
            ui.subtitulo("🔒 Cierre del período"),
            ft.Text("Este período ya terminó. Confirma qué se gastó, "
                    "qué salió de nuevo y cuánto ahorraste.", size=13),
            ft.Button("Cerrar y confirmar", icon=ft.Icons.LOCK,
                      on_click=confirmar_cierre),
        ], fondo=ft.Colors.AMBER_50)
    else:
        panel_cierre = _panel([
            ui.subtitulo("🔒 Cierre del período"),
            ft.Text(f"Podrás confirmar el cierre cuando termine "
                    f"({resumen['fin']}). Marca antes tus planeados con "
                    "«Se gastó» o «No se hizo».", size=13,
                    color=ft.Colors.GREY_700),
        ])

    panel_movimientos = _panel_movimientos(page, refresh, tipo, inicio)

    return ft.Column(
        [
            ui.titulo("🎯 Presupuesto"),
            ft.Row([selector, navegacion], spacing=16, wrap=True),
            panel_estado,
            panel_planeados,
            panel_cierre,
            panel_movimientos,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )


# ---------------------------------------------------------------------------
# Movimientos reales del período (editar / eliminar registros)
# ---------------------------------------------------------------------------

def _panel_movimientos(page, refresh, tipo, inicio) -> ft.Container:
    desde, hasta = rango_periodo(tipo, inicio)
    gastos = listar_gastos_periodo(tipo, inicio)
    ingresos = listar_ingresos(desde=desde, hasta=hasta)
    cuentas = {c["id"]: c["nombre"] for c in listar_cuentas()}

    filas_gastos = []
    for g in gastos:
        filas_gastos.append(ft.Row([
            ft.Text(f"{g['fecha']} · {g['categoria']}"
                    + (f" — {g['descripcion']}" if g["descripcion"] else ""),
                    size=12, expand=True),
            ft.Text(cuentas.get(g["cuenta_id"], "?"), size=11,
                    color=ft.Colors.GREY_600),
            ft.Text(f"-${g['convertido_a_pesos']:,.2f}", size=12,
                    color=ft.Colors.RED_600),
            *edicion.botones_edicion(
                edicion.dialogo_editar_gasto(page, refresh, g),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar el gasto «{g['categoria']}» de "
                    f"${g['convertido_a_pesos']:,.2f}?",
                    lambda gid=g["id"]: eliminar_gasto(gid))),
        ], spacing=2))

    filas_ingresos = []
    for i in ingresos:
        filas_ingresos.append(ft.Row([
            ft.Text(f"{i['fecha']} · {i['categoria']}", size=12, expand=True),
            ft.Text(cuentas.get(i.get("cuenta_id"), "—"), size=11,
                    color=ft.Colors.GREY_600),
            ft.Text(f"+${i['convertido_a_pesos']:,.2f}", size=12,
                    color=ft.Colors.GREEN_700),
            *edicion.botones_edicion(
                edicion.dialogo_editar_ingreso(page, refresh, i),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar el ingreso «{i['categoria']}» de "
                    f"${i['convertido_a_pesos']:,.2f}?",
                    lambda iid=i["id"]: eliminar_ingreso(iid))),
        ], spacing=2))

    return _panel([
        ui.subtitulo("🧾 Movimientos del período (edita o elimina)"),
        ft.Text("Gastos:", size=12, weight="bold"),
        *(filas_gastos or [ft.Text("Sin gastos en este período.", size=12,
                                   color=ft.Colors.GREY_600)]),
        ft.Text("Ingresos:", size=12, weight="bold"),
        *(filas_ingresos or [ft.Text("Sin ingresos en este período.", size=12,
                                     color=ft.Colors.GREY_600)]),
    ])
