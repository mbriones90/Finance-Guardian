"""Vista de resumen financiero: el dashboard del perfil de pago activo.

Las secciones que se muestran dependen de los **módulos de dashboard
visibles del perfil activo** (Mínimo, Optimizado, Agresivo o Custom):
- ``resumen_financiero``: tarjetas de efectivo/deuda/patrimonio y ciclo.
- ``riesgos_alertas``: alertas con semáforo.
- ``suscripciones``: gastos fijos activos y su impacto mensual.
- ``presupuesto_semanal``: semáforo de la semana (¿me alcanza?).
- ``proyeccion_deuda``: fecha estimada de liquidación por tarjeta.

El perfil se cambia únicamente en la sección Configuración.
"""

import flet as ft

from src.services import (
    deuda_total_pesos,
    efectivo_total_pesos,
    evaluar_riesgos,
    fecha_liquidacion_por_perfil,
    listar_suscripciones,
    listar_tarjetas,
    modulos_visibles,
    obtener_perfil_activo,
    patrimonio_neto_pesos,
    total_mensual_pesos,
    estado_semana,
)
from src.ui import components as ui


def _modulo_resumen_financiero(tarjetas) -> list:
    filas_tarjetas = []
    for t in tarjetas:
        filas_tarjetas.append(ft.Row([
            ft.Icon(ft.Icons.CREDIT_CARD, color=ft.Colors.AMBER_700),
            ft.Text(t["nombre"], size=13, expand=True),
            ft.Text(f"corte en {t['dias_hasta_corte']} días", size=12,
                    color=ft.Colors.BLUE_700),
            ft.Text(f"pago en {t['dias_hasta_pago']} días", size=12,
                    color=ft.Colors.GREEN_700),
            ft.Text(f"deuda ${t['balance_deuda']:,.2f}", size=12,
                    color=ft.Colors.RED_600),
        ]))
    return [
        ft.Row(
            [
                ui.stat_card("💵 Efectivo", f"${efectivo_total_pesos():,.2f}"),
                ui.stat_card("💳 Deuda tarjetas",
                             f"${deuda_total_pesos():,.2f}", ft.Colors.RED_600),
                ui.stat_card("🛡️ Patrimonio neto",
                             f"${patrimonio_neto_pesos():,.2f}"),
            ],
            spacing=12,
            wrap=True,
        ),
        ui.subtitulo("💳 Tarjetas (próximo ciclo)"),
        *(filas_tarjetas or [ft.Text("Sin tarjetas todavía.", size=13)]),
    ]


def _modulo_riesgos(riesgos) -> list:
    alertas = [ui.fila_alerta(a["nivel"], a["mensaje"]) for a in riesgos]
    return [ui.subtitulo("⚠️ Riesgos"), *alertas]


def _modulo_suscripciones() -> list:
    suscripciones = listar_suscripciones()
    filas = [ft.Text(f"• {s['nombre']}: ${s['monto']:,.2f} {s['moneda']} "
                     f"· día {s['dia_cobro']} · {s['periodo']}", size=13)
             for s in suscripciones]
    return [
        ui.subtitulo("📦 Suscripciones"),
        ft.Text(f"Impacto mensual: ${total_mensual_pesos():,.2f}", size=13,
                weight="bold"),
        *(filas or [ft.Text("Sin suscripciones activas.", size=13)]),
    ]


def _modulo_presupuesto(semana) -> list:
    return [
        ui.subtitulo("🍽️ Presupuesto semanal (¿me alcanza para salir?)"),
        ft.Text(f"Gastado ${semana['gastado_total']:,.2f} de "
                f"${semana['limite_total']:,.2f} — quedan "
                f"${semana['restante_total']:,.2f}", size=13),
    ]


def _modulo_proyeccion(tarjetas, perfil_activo) -> list:
    filas = []
    for t in tarjetas:
        if t["balance_deuda"] <= 0:
            continue
        liq = fecha_liquidacion_por_perfil(perfil_activo["id"], t["cuenta_id"],
                                           guardar=False)
        if liq["meses_para_liquidar"]:
            texto = (f"• {t['nombre']}: pago ${liq['pago_mensual']:,.2f}/mes → "
                     f"liquidas en {liq['meses_para_liquidar']} meses "
                     f"({liq['fecha_estimada_liquidacion']})")
        else:
            texto = f"• {t['nombre']}: pago mensual insuficiente para liquidar"
        filas.append(ft.Text(texto, size=13))
    filas.append(ft.Text("📈 Detalle mes a mes en la sección Deuda.",
                         size=11, italic=True, color=ft.Colors.GREY_600))
    return [ui.subtitulo("📉 Proyección de deuda"),
            *(filas if len(filas) > 1 else
              [ft.Text("Sin deuda en tarjetas. 🎉", size=13)])]


def build(page: ft.Page, refresh) -> ft.Column:
    riesgos = evaluar_riesgos()
    tarjetas = listar_tarjetas()
    activo = obtener_perfil_activo()
    semana = estado_semana()

    # ---------- Dashboard según módulos visibles del perfil activo ----------
    secciones = []
    modulos = []
    if activo:
        modulos = [m["nombre_modulo"] for m in modulos_visibles(activo["id"])]
        secciones.append(ft.Text(
            f"Dashboard del perfil {activo['nombre']} "
            f"({len(modulos)} módulos)", size=12, color=ft.Colors.GREY_600))
    else:
        secciones.append(ft.Text(
            "Activa un perfil de pago para armar tu dashboard.",
            size=12, color=ft.Colors.GREY_600))

    if "resumen_financiero" in modulos:
        secciones += _modulo_resumen_financiero(tarjetas)
    if "riesgos_alertas" in modulos:
        secciones += _modulo_riesgos(riesgos)
    if "proyeccion_deuda" in modulos and activo:
        secciones += _modulo_proyeccion(tarjetas, activo)
    if "presupuesto_semanal" in modulos:
        secciones += _modulo_presupuesto(semana)
    if "suscripciones" in modulos:
        secciones += _modulo_suscripciones()

    return ft.Column(
        [
            ui.titulo("📊 Resumen financiero"),
            *secciones,
            ft.Text("⚙️ El perfil de pago se cambia en Configuración.",
                    size=11, italic=True, color=ft.Colors.GREY_600),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )
