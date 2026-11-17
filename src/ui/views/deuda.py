"""Vista Deuda: proyección mes a mes estilo Gantt según la estrategia.

Para cada tarjeta con deuda muestra cómo va bajando el saldo en los
próximos 12 meses con el pago mensual que dicta el perfil de pago
seleccionado (Mínimo, Optimizado, Agresivo o Custom).

Cada barra es un mes: la longitud es proporcional al saldo restante y el
color va de rojo (deuda alta) a verde (casi liquidada).
"""

from datetime import date

import flet as ft

from src.services import (
    calcular_pago_mensual,
    fecha_liquidacion_por_perfil,
    listar_perfiles,
    listar_tarjetas,
    obtener_perfil_activo,
    proyectar,
)
from src.ui import components as ui

MESES_CORTOS = ["", "ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic"]

# Ancho pensado para pantalla de smartphone (~340 px útiles por tarjeta).
ANCHO_MAX_BARRA = 120


def _color_barra(ratio: float) -> str:
    """Rojo → ámbar → verde según cuánto queda de la deuda inicial."""
    if ratio > 0.66:
        return ft.Colors.RED_400
    if ratio > 0.33:
        return ft.Colors.AMBER_400
    return ft.Colors.GREEN_400


def _fila_mes(mes: int, fecha_iso: str, saldo: float, deuda_inicial: float,
              pago: float) -> ft.Row:
    ancho = max(4, ANCHO_MAX_BARRA * saldo / deuda_inicial) if saldo > 0 else 4
    ratio = saldo / deuda_inicial if deuda_inicial > 0 else 0
    f = date.fromisoformat(fecha_iso)
    etiqueta = f"M{mes:>2} {MESES_CORTOS[f.month]} {f.year}"
    barra = ft.Container(
        width=ancho,
        height=16,
        bgcolor=_color_barra(ratio) if saldo > 0 else ft.Colors.GREEN_600,
        border_radius=4,
        tooltip=f"Pago del mes: ${pago:,.2f}",
    )
    monto = (f"${saldo:,.0f}" if saldo > 0
             else "✅ liquidada")
    return ft.Row(
        [ft.Text(etiqueta, size=10, width=88, color=ft.Colors.GREY_700),
         barra,
         ft.Text(monto, size=10, width=96)],
        spacing=8,
    )


def _tarjeta_gantt(tarjeta: dict, perfil: dict) -> ft.Control:
    cuenta_id = tarjeta["cuenta_id"]
    deuda = float(tarjeta["balance_deuda"])
    if deuda <= 0:
        return ft.Container(
            content=ft.Text(f"🎉 {tarjeta['nombre']}: sin deuda.", size=13),
            padding=8,
        )

    calc = calcular_pago_mensual(cuenta_id, perfil["id"])
    pago = calc["pago_mensual"]
    liq = fecha_liquidacion_por_perfil(perfil["id"], cuenta_id, guardar=False)

    encabezado = ft.Row(
        [ft.Icon(ft.Icons.CREDIT_CARD, color=ft.Colors.AMBER_700),
         ft.Text(tarjeta["nombre"], size=14, weight="bold"),
         ft.Text(f"deuda ${deuda:,.2f}", size=12, color=ft.Colors.RED_600),
         ft.Text(f"tasa {calc['tasa_interes_mensual']:.1f}%", size=12,
                 color=ft.Colors.GREY_600),
         ft.Text(f"pago ${pago:,.2f}/mes", size=12, weight="bold",
                 color=ft.Colors.GREEN_700)],
        spacing=10,
        wrap=True,
    )

    if pago <= 0:
        return ft.Container(
            content=ft.Column([encabezado, ft.Text(
                "El pago mensual de esta estrategia es $0: la deuda no baja.",
                size=12, color=ft.Colors.RED_600)]),
            bgcolor=ft.Colors.WHITE, border=ui._borde(), border_radius=12,
            padding=12,
        )

    proy = proyectar(cuenta_id, pago_mensual=pago, meses=12, guardar=False)
    filas = [_fila_mes(f["mes_proyectado"], f["fecha"], f["saldo_final"],
                       deuda, f["pago_aplicado"])
             for f in proy["filas"]]

    if liq["meses_para_liquidar"]:
        cierre = (f"🏁 Liquidas en {liq['meses_para_liquidar']} meses "
                  f"(~{liq['fecha_estimada_liquidacion']}) · interés total "
                  f"${liq['interes_total']:,.2f}")
        color_cierre = ft.Colors.GREEN_700
    else:
        cierre = ("⚠️ Con este pago no se liquida en el horizonte "
                  f"(interés acumulado: ${liq['interes_total']:,.2f})")
        color_cierre = ft.Colors.RED_600

    return ft.Container(
        content=ft.Column(
            [encabezado, *filas,
             ft.Text(cierre, size=12, weight="bold", color=color_cierre)],
            spacing=3,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ui._borde(),
        border_radius=12,
        padding=12,
    )


def build(page: ft.Page, refresh, estado: dict) -> ft.Column:
    perfiles = listar_perfiles()
    activo = obtener_perfil_activo()
    tarjetas = listar_tarjetas()

    # Estrategia seleccionada para proyectar (por defecto la activa)
    if not estado.get("perfil_id"):
        estado["perfil_id"] = activo["id"] if activo else (
            perfiles[0]["id"] if perfiles else None)
    perfil = next((p for p in perfiles if p["id"] == estado["perfil_id"]),
                  activo or (perfiles[0] if perfiles else None))

    def cambiar_estrategia(e):
        elegido = e.control.selected
        if elegido:
            estado["perfil_id"] = int(elegido[0])
        refresh()

    selector = ft.SegmentedButton(
        segments=[ft.Segment(value=str(p["id"]), label=p["nombre"])
                  for p in perfiles],
        selected=[str(perfil["id"])] if perfil else [],
        on_change=cambiar_estrategia,
    )

    cuerpo = []
    if not tarjetas:
        cuerpo.append(ft.Text(
            "Aún no tienes tarjetas. Crea una en la Dimensión 4 y "
            "configúrala en la 5.", size=14))
    else:
        cuerpo.append(ft.Text(
            f"Estrategia: {perfil['nombre']} "
            f"({perfil['tipo_perfil']}) — así baja tu deuda:",
            size=13, color=ft.Colors.GREY_700))
        for t in tarjetas:
            cuerpo.append(_tarjeta_gantt(t, perfil))

    nota = ft.Text(
        "Las barras son el saldo al final de cada mes con el pago de la "
        "estrategia elegida. Cambia la estrategia activa en Personaje o "
        "Resumen.",
        size=11, italic=True, color=ft.Colors.GREY_600)

    return ft.Column(
        [ui.titulo("📉 Proyección de deuda"),
         ft.Row([ft.Text("Estrategia:", size=13), selector], spacing=10),
         *cuerpo,
         nota],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )
