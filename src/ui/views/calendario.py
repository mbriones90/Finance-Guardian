"""Vista del calendario de pagos: semanal o mensual.

Muestra los días de pago del Guardián:
- 💳 Cortes de tarjeta (azul)
- 💰 Pagos de tarjeta (verde)
- 📦 Cobros de suscripciones (morado)

Se puede alternar entre vista **semanal** (7 columnas, lunes a domingo) y
**mensual** (cuadrícula del mes), y navegar atrás/adelante en el tiempo.
"""

import calendar
from datetime import date, timedelta

import flet as ft

from src.services import (
    eventos_del_mes,
    eventos_de_semana,
    estado_mes,
    estado_semana,
    obtener_presupuesto_general,
    premio_reclamado,
    reclamar_puntos_semanales,
    resumen_mes,
    PUNTOS_SEMANA_DERROTADA,
)
from src.ui import components as ui

COLOR_EVENTO = {
    "corte_tarjeta": ft.Colors.BLUE_700,
    "pago_tarjeta": ft.Colors.GREEN_700,
    "suscripcion": ft.Colors.PURPLE_700,
    "cobro_sueldo": ft.Colors.TEAL_700,
}

ICONO_EVENTO = {
    "corte_tarjeta": "💳",
    "pago_tarjeta": "💰",
    "suscripcion": "📦",
    "cobro_sueldo": "💵",
}

SEMAFORO_COLOR = {
    "verde": ft.Colors.GREEN_600,
    "amarillo": ft.Colors.AMBER_700,
    "rojo": ft.Colors.RED_600,
}

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _lunes(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


# ---------------------------------------------------------------------------
# La Masmorra del Presupuesto: calendario + presupuesto son la misma batalla
# ---------------------------------------------------------------------------

def _panel_masmorra(ancla: date, modo: str) -> ft.Control:
    """Panel del presupuesto: semana visible, mes visible y premios ganados."""
    semana = estado_semana(_lunes(ancla) if modo == "semanal" else date.today())
    mes = estado_mes(ancla.year, ancla.month)
    lunes_vista = _lunes(ancla)
    semana_cerrada = lunes_vista + timedelta(days=6) < date.today()
    derrotada = (semana["limite_total"] > 0
                 and semana["gastado_total"] <= semana["limite_total"])

    color_sem = SEMAFORO_COLOR[semana["semaforo_total"]]
    color_mes = SEMAFORO_COLOR[mes["semaforo"]]

    if modo == "semanal":
        if semana_cerrada and derrotada:
            if premio_reclamado(lunes_vista):
                estado_txt = f"🏆 Semana derrotada · +{PUNTOS_SEMANA_DERROTADA} pts"
            else:
                estado_txt = "⚔️ Semana derrotada (premio al volver)"
        elif semana_cerrada:
            estado_txt = "💀 La masmorra te venció: te saliste del presupuesto"
        else:
            estado_txt = "⚔️ Batalla en curso: no te salgas del plan"
    else:
        estado_txt = ("Planifica semana a semana: cada semana cerrada dentro "
                      f"del presupuesto otorga +{PUNTOS_SEMANA_DERROTADA} pts")

    barras = ft.Column(
        [
            ft.Row(
                [ft.Text("🗓️ Semana", size=12, weight="bold", width=110),
                 ft.ProgressBar(
                     value=(min(1.0, semana["gastado_total"] / semana["limite_total"])
                            if semana["limite_total"] > 0 else 0),
                     color=color_sem, bgcolor=ft.Colors.GREY_200, expand=True),
                 ft.Text(f"${semana['gastado_total']:,.0f} / "
                         f"${semana['limite_total']:,.0f}", size=12,
                         color=color_sem)],
                spacing=8,
            ),
            ft.Row(
                [ft.Text("📆 Mes", size=12, weight="bold", width=110),
                 ft.ProgressBar(
                     value=(min(1.0, mes["gastado"] / mes["limite"])
                            if mes["limite"] > 0 else 0),
                     color=color_mes, bgcolor=ft.Colors.GREY_200, expand=True),
                 ft.Text(f"${mes['gastado']:,.0f} / ${mes['limite']:,.0f}",
                         size=12, color=color_mes)],
                spacing=8,
            ),
        ],
        spacing=4,
    )

    return ft.Container(
        content=ft.Column(
            [ft.Text("🏰 La Masmorra del Presupuesto", size=14, weight="bold"),
             ft.Text(estado_txt, size=12, color=ft.Colors.GREY_700),
             barras],
            spacing=6,
        ),
        bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.WHITE),
        border=ui._borde(ft.Colors.BROWN_200, 1),
        border_radius=12,
        padding=12,
    )


def _banner_premios(nuevos: list) -> ft.Control:
    """Aviso de puntos semanales ganados por derrotar la masmorra."""
    if not nuevos:
        return ft.Container()
    total = sum(p["puntos"] for p in nuevos)
    semanas = ", ".join(p["semana_inicio"] for p in nuevos)
    return ft.Container(
        content=ft.Text(
            f"🏆 ¡Masmorra derrotada! +{total} pts por {len(nuevos)} "
            f"semana(s) cumplida(s): {semanas}",
            size=13, weight="bold", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
        border_radius=10,
        padding=10,
    )


def _ancla(estado: dict) -> date:
    """Fecha de referencia guardada en el estado (hoy por defecto)."""
    guardada = estado.get("ancla")
    if guardada:
        try:
            return date.fromisoformat(guardada)
        except ValueError:
            pass
    return date.today()


def _chip_evento(evento: dict, compacto: bool = False) -> ft.Control:
    color = COLOR_EVENTO.get(evento["tipo"], ft.Colors.GREY_700)
    icono = ICONO_EVENTO.get(evento["tipo"], "•")
    texto = evento["titulo"] if compacto else evento["detalle"]
    return ft.Text(f"{icono} {texto}", size=9 if compacto else 11,
                   color=color, tooltip=evento["detalle"])


# ---------------------------------------------------------------------------
# Vista semanal
# ---------------------------------------------------------------------------

def _vista_semanal(ancla: date) -> ft.Control:
    """Semana como lista vertical de días (patrón móvil: se lee mejor que
    7 columnas apretadas en pantalla angosta)."""
    lunes = _lunes(ancla)
    domingo = lunes + timedelta(days=6)
    eventos = eventos_de_semana(lunes)
    por_fecha = {}
    for e in eventos:
        por_fecha.setdefault(e["fecha"], []).append(e)

    hoy = date.today().isoformat()
    filas = []
    for i in range(7):
        dia = lunes + timedelta(days=i)
        iso = dia.isoformat()
        es_hoy = iso == hoy
        eventos_dia = por_fecha.get(iso, [])
        filas.append(
            ft.Container(
                content=ft.Row(
                    [ft.Container(
                        content=ft.Column(
                            [ft.Text(DIAS_SEMANA[i], size=10,
                                     color=ft.Colors.GREY_600),
                             ft.Text(str(dia.day), size=16, weight="bold",
                                     color=ft.Colors.AMBER_800 if es_hoy
                                     else ft.Colors.GREY_800)],
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        width=44,
                    ),
                     ft.Column(
                         [_chip_evento(e) for e in eventos_dia]
                         or [ft.Text("—", size=11, color=ft.Colors.GREY_400)],
                         spacing=2, expand=True)],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor=ft.Colors.AMBER_50 if es_hoy else ft.Colors.WHITE,
                border=_borde_hoy() if es_hoy else ui._borde(),
                border_radius=10,
                padding=8,
            )
        )

    return ft.Column(
        [ft.Text(f"Semana del {lunes.day} {MESES[lunes.month][:3].lower()} "
                 f"al {domingo.day} {MESES[domingo.month][:3].lower()} "
                 f"{domingo.year}", size=13, color=ft.Colors.GREY_700),
         *filas],
        spacing=6,
    )


# ---------------------------------------------------------------------------
# Vista mensual
# ---------------------------------------------------------------------------

def _borde_hoy() -> ft.Border:
    lado = ft.BorderSide(2, ft.Colors.AMBER_400)
    return ft.Border(top=lado, right=lado, bottom=lado, left=lado)


# Celdas del mes tamaño smartphone: 7 × 48 + 6 × 4 ≈ 360 px de ancho.
CELDA_MES = 48


def _punto_evento(evento: dict) -> ft.Container:
    """Puntito de color por evento (así caben en la celda de teléfono;
    el detalle completo está en el tooltip)."""
    return ft.Container(
        width=7,
        height=7,
        border_radius=4,
        bgcolor=COLOR_EVENTO.get(evento["tipo"], ft.Colors.GREY_400),
        tooltip=evento["detalle"],
    )


def _celda_dia(dia: int, es_hoy: bool, eventos: list,
               atenuado: bool) -> ft.Container:
    opacidad = 0.35 if atenuado else 1.0
    return ft.Container(
        content=ft.Column(
            [ft.Text(str(dia), size=11, weight="bold",
                     color=ft.Colors.AMBER_800 if es_hoy else ft.Colors.GREY_800),
             ft.Row([_punto_evento(e) for e in eventos[:3]], spacing=2),
             ft.Text(f"+{len(eventos) - 3}", size=8,
                     color=ft.Colors.GREY_600) if len(eventos) > 3
             else ft.Container()],
            spacing=2,
        ),
        bgcolor=ft.Colors.AMBER_50 if es_hoy else ft.Colors.WHITE,
        border=_borde_hoy() if es_hoy else ui._borde(),
        border_radius=8,
        padding=4,
        width=CELDA_MES,
        height=58,
        opacity=opacidad,
    )


def _vista_mensual(ancla: date) -> ft.Control:
    year, month = ancla.year, ancla.month
    eventos = eventos_del_mes(year, month)
    por_fecha = {}
    for e in eventos:
        por_fecha.setdefault(e["fecha"], []).append(e)

    hoy = date.today().isoformat()
    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)

    encabezado = ft.Row(
        [ft.Container(ft.Text(d[:1], size=10, weight="bold",
                              color=ft.Colors.GREY_700),
                      width=CELDA_MES, alignment=ft.Alignment(0, 0))
         for d in DIAS_SEMANA],
        spacing=4,
    )

    filas = []
    for semana in semanas:
        celdas = []
        for dia in semana:
            iso = dia.isoformat()
            celdas.append(_celda_dia(
                dia.day, iso == hoy, por_fecha.get(iso, []),
                atenuado=dia.month != month,
            ))
        filas.append(ft.Row(celdas, spacing=4))

    resumen = resumen_mes(year, month)
    pie = ft.Text(
        f"💳 {resumen['cortes']} cortes · 💰 {resumen['pagos_tarjeta']} pagos "
        f"de tarjeta · 📦 {resumen['cobros_suscripcion']} cobros de "
        f"suscripción (${resumen['total_suscripciones']:,.2f})",
        size=12, color=ft.Colors.GREY_700,
    )

    return ft.Column(
        [ft.Text(f"{MESES[month]} {year}", size=13, color=ft.Colors.GREY_700),
         encabezado, *filas, pie],
        spacing=6,
    )


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------

def build(page: ft.Page, refresh, estado: dict) -> ft.Column:
    estado.setdefault("modo", "mensual")
    ancla = _ancla(estado)
    modo = estado["modo"]

    # Reclama los premios de semanas ya cerradas (la masmorra semanal).
    nuevos_premios = reclamar_puntos_semanales()

    def cambiar_modo(e):
        elegido = e.control.selected
        if elegido:
            estado["modo"] = elegido[0]
        refresh()

    def mover(direccion: int):
        def fn(e):
            if modo == "semanal":
                nueva = ancla + timedelta(weeks=direccion)
            else:
                mes_total = ancla.year * 12 + ancla.month - 1 + direccion
                nueva = date(mes_total // 12, mes_total % 12 + 1, 1)
            estado["ancla"] = nueva.isoformat()
            refresh()
        return fn

    def ir_hoy(e):
        estado["ancla"] = None
        refresh()

    selector = ft.SegmentedButton(
        segments=[
            ft.Segment(value="semanal", label="Semanal",
                       icon=ft.Icons.VIEW_WEEK),
            ft.Segment(value="mensual", label="Mensual",
                       icon=ft.Icons.CALENDAR_MONTH),
        ],
        selected=[modo],
        on_change=cambiar_modo,
    )

    navegacion = ft.Row(
        [ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=mover(-1),
                       tooltip="Anterior"),
         ft.TextButton("Hoy", on_click=ir_hoy),
         ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=mover(1),
                       tooltip="Siguiente"),
         selector],
        spacing=6,
        wrap=True,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    cuerpo = _vista_semanal(ancla) if modo == "semanal" else _vista_mensual(ancla)

    leyenda = ft.Row(
        [ft.Text("💳 Corte de tarjeta", size=11, color=COLOR_EVENTO["corte_tarjeta"]),
         ft.Text("💰 Pago de tarjeta", size=11, color=COLOR_EVENTO["pago_tarjeta"]),
         ft.Text("📦 Suscripción", size=11, color=COLOR_EVENTO["suscripcion"]),
         ft.Text("💵 Cobro de sueldo", size=11, color=COLOR_EVENTO["cobro_sueldo"])],
        spacing=12,
        wrap=True,
    )

    return ft.Column(
        [ui.titulo("📅 Calendario y Masmorra"),
         _banner_premios(nuevos_premios),
         navegacion,
         _panel_masmorra(ancla, modo),
         cuerpo,
         ft.Divider(), leyenda],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )
