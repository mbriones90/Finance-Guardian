"""Vista de distribución de gastos por categoría.

Tabla con el gasto **real** de la semana y el mes actuales, y la
**proyección** por categoría a 1 semana, 1 mes, 1 año y 10 años
(promedio semanal histórico; si no hay gastos, el presupuesto planeado).
"""

import flet as ft

from src.services import distribucion_gastos
from src.ui import components as ui

COLUMNAS = [
    ("Categoría", 170),
    ("Real semana", 95),
    ("Real mes", 95),
    ("Proy. 1 sem", 95),
    ("Proy. 1 mes", 95),
    ("Proy. 1 año", 105),
    ("Proy. 10 años", 115),
]

CAMPOS = ["real_semana", "real_mes", "proy_semana", "proy_mes",
          "proy_ano", "proy_diez_anos"]


def _fila(valores, negrita=False, color=None, fondo=None):
    peso = "bold" if negrita else None
    celdas = [ft.Text(str(valores[0]), size=12, weight=peso, width=COLUMNAS[0][1],
                      color=color)]
    for i, v in enumerate(valores[1:], start=1):
        celdas.append(ft.Text(f"${v:,.2f}" if isinstance(v, (int, float)) else str(v),
                              size=12, weight=peso, width=COLUMNAS[i][1],
                              text_align=ft.TextAlign.RIGHT, color=color))
    return ft.Container(
        content=ft.Row(celdas, spacing=6),
        bgcolor=fondo,
        padding=ft.Padding(left=8, top=5, right=8, bottom=5),
        border_radius=6,
    )


def build(page: ft.Page, refresh) -> ft.Column:
    datos = distribucion_gastos()
    general = datos["presupuesto_general"]

    if general:
        texto_general = ft.Text(
            f"🎯 Presupuesto general {general['periodo']}: "
            f"${general['monto']:,.2f}  →  "
            f"${general['semanal']:,.2f}/sem · "
            f"${general['quincenal']:,.2f}/quincena · "
            f"${general['mensual']:,.2f}/mes",
            size=13, color=ft.Colors.GREY_700)
    else:
        texto_general = ft.Text(
            "🎯 Aún no defines presupuesto general (Dimensión 6).",
            size=13, color=ft.Colors.GREY_700)

    encabezado = ft.Container(
        content=ft.Row(
            [ft.Text(titulo, size=12, weight="bold", width=ancho,
                     color=ft.Colors.WHITE,
                     text_align=(ft.TextAlign.LEFT if i == 0
                                 else ft.TextAlign.RIGHT))
             for i, (titulo, ancho) in enumerate(COLUMNAS)],
            spacing=6,
        ),
        bgcolor=ft.Colors.BROWN_400,
        padding=ft.Padding(left=8, top=8, right=8, bottom=8),
        border_radius=6,
    )

    filas = []
    for i, c in enumerate(datos["categorias"]):
        valores = [c["categoria"]] + [c[campo] for campo in CAMPOS]
        fondo = ft.Colors.GREY_100 if i % 2 else None
        filas.append(_fila(valores, fondo=fondo))

    t = datos["totales"]
    filas.append(_fila(["TOTAL"] + [t[campo] for campo in CAMPOS],
                       negrita=True, color=ft.Colors.BROWN_700,
                       fondo=ft.Colors.AMBER_50))

    nota = ft.Text(
        "Proyección = promedio semanal histórico de la categoría "
        "(o su presupuesto planeado si aún no tiene gastos). Desliza la "
        "tabla hacia los lados para ver todas las columnas.",
        size=11, italic=True, color=ft.Colors.GREY_600)

    # La tabla es más ancha que un teléfono: scroll horizontal (patrón móvil).
    tabla = ft.Row(
        [ft.Column([encabezado, *filas], spacing=4)],
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Column(
        [ui.titulo("📊 Distribución de gastos"), texto_general, tabla, nota],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=4,
    )
