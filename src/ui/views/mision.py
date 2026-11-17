"""Vista de misión de cada dimensión: registro, edición y rejugabilidad.

Cada dimensión tiene su formulario y la lista de **registros previos con
✏️ editar y 🗑 eliminar** (los diálogos viven en ``src/ui/edicion.py``).
Se puede volver a cualquier dimensión desbloqueada, añadir o corregir
registros y **guardar de nuevo**: el botón "Completar" abre el cofre otra
vez con el premio de repetición (mitad de puntos y XP), sin perder el
nivel alcanzado.
"""

import flet as ft

from src.repositories import (
    cuenta_repo,
    gasto_repo,
    ingreso_repo,
    perfil_repo,
    suscripcion_repo,
    tarjeta_repo,
)
from src.services import (
    agregar_suscripcion,
    activar_perfil,
    actualizar_perfil,
    completar_dimension,
    configurar_tarjeta,
    crear_cuenta,
    definir_presupuesto_base,
    definir_presupuesto_general,
    eliminar_cuenta,
    eliminar_gasto,
    eliminar_ingreso,
    eliminar_presupuesto_base,
    eliminar_suscripcion,
    estado_semana,
    listar_perfiles,
    listar_presupuesto_base,
    obtener_presupuesto_general,
    premio_dimension,
    registrar_gasto,
    registrar_ingreso,
    suma_categorias_base,
    CATEGORIAS_GASTO,
    CATEGORIA_DEFAULT,
)
from src.services.cofres import info_dimension
from src.services.inventario import FONDOS
from src.ui import components as ui, edicion


# ---------------------------------------------------------------------------
# Requisitos para completar cada dimensión
# ---------------------------------------------------------------------------

def _tarjetas_activas():
    return tarjeta_repo.get_activas()


REQUISITOS = {
    1: ("Tener al menos 1 cuenta registrada",
        lambda: len(cuenta_repo.get_by_tipo("cuenta")) >= 1),
    2: ("Tener al menos 1 ingreso registrado",
        lambda: len(ingreso_repo.get_all()) >= 1),
    3: ("Tener al menos 3 gastos registrados",
        lambda: len(gasto_repo.get_all()) >= 3),
    4: ("Tener al menos 1 tarjeta de crédito creada",
        lambda: len(_tarjetas_activas()) >= 1),
    5: ("Tener 1 tarjeta con tasa de interés configurada",
        lambda: any(float(t.get("tasa_interes_mensual") or 0) > 0
                    for t in _tarjetas_activas())),
    6: ("Definir el presupuesto general y repartir al menos 1 categoría",
        lambda: (obtener_presupuesto_general() is not None
                 and len(listar_presupuesto_base()) >= 1)),
    7: ("Tener al menos 1 suscripción activa",
        lambda: len(suscripcion_repo.get_activas()) >= 1),
    8: ("Tener un perfil de pago activo",
        lambda: perfil_repo.get_activo() is not None),
}


# ---------------------------------------------------------------------------
# Helpers de formulario
# ---------------------------------------------------------------------------

def _cuentas_opciones():
    opciones = []
    for c in cuenta_repo.get_all():
        moneda = f" ({c['moneda']})" if c["moneda"] != "MXN" else ""
        opciones.append(ft.dropdown.Option(str(c["id"]), f"{c['nombre']}{moneda}"))
    return opciones or [ft.dropdown.Option("", "— crea primero una cuenta —")]


def _seleccionar_cuenta_dropdown() -> ft.Dropdown:
    opciones = _cuentas_opciones()
    cuentas = cuenta_repo.get_all()
    # Preselecciona la primera cuenta: sin esto el dropdown arranca vacío
    # (value=None) y registrar falla con un error críptico de int(None).
    # Ancho fijo (no expand=True): en Flet 0.86 el Dropdown expandido dentro
    # de un Row con wrap se estira sin límite y tapa el resto del formulario.
    valor = str(cuentas[0]["id"]) if cuentas else None
    return ft.Dropdown(label="Cuenta", options=opciones, value=valor,
                       width=280)


def _campo(label: str, valor=None, numerico=False, ancho=None) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=str(valor) if valor is not None else None,
        keyboard_type=ft.KeyboardType.NUMBER if numerico else None,
        width=ancho,
    )


def _dropdown_categorias() -> ft.Dropdown:
    return ft.Dropdown(
        label="Categoría",
        options=[ft.dropdown.Option(c, c) for c in CATEGORIAS_GASTO],
        value=CATEGORIA_DEFAULT,
        width=280,
    )


def _lista_titulo(texto: str) -> ft.Text:
    return ft.Text(texto, size=13, weight="bold")


# ---------------------------------------------------------------------------
# Formularios por dimensión (todos con registros editables/eliminables)
# ---------------------------------------------------------------------------

def _formulario_d1(page, refresh):
    nombre = _campo("Nombre de la cuenta", "Cuenta de ahorro")
    saldo = _campo("Saldo inicial", 0, numerico=True)
    moneda = ft.Dropdown(
        label="Moneda",
        options=[ft.dropdown.Option("MXN", "Pesos (MXN)"),
                 ft.dropdown.Option("USD", "Dólares (USD)")],
        value="MXN", width=150,
    )

    def guardar(e):
        try:
            crear_cuenta(nombre.value or "Cuenta", "cuenta",
                         moneda.value, float(saldo.value or 0))
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    filas = []
    for c in cuenta_repo.get_by_tipo("cuenta"):
        filas.append(ft.Row([
            ft.Text(f"• {c['nombre']}: ${c['balance_actual']:,.2f} "
                    f"{c['moneda']}", size=13, expand=True),
            *edicion.botones_edicion(
                edicion.dialogo_editar_cuenta(page, refresh, c),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar la cuenta «{c['nombre']}»? (Solo si no "
                    "tiene registros ligados.)",
                    lambda cid=c["id"]: eliminar_cuenta(cid))),
        ], spacing=2))

    return ft.Column([
        ft.Text("Crea tus cuentas y registra su saldo. Vuelve cuando "
                "quieras para añadir más o corregirlas.", size=14),
        ft.Row([nombre, saldo, moneda], wrap=True, spacing=10),
        ft.Button("Guardar cuenta", icon=ft.Icons.SAVE, on_click=guardar),
        _lista_titulo("Tus cuentas (✏️ edita · 🗑 elimina):"),
        *(filas or [ft.Text("Sin cuentas todavía.", size=13,
                            color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d2(page, refresh):
    cat = _campo("Categoría (ej. Sueldo, Bono)", "Sueldo")
    monto = _campo("Monto", 0, numerico=True)
    frecuencia = ft.Dropdown(
        label="Frecuencia",
        options=[ft.dropdown.Option("mensual", "Mensual"),
                 ft.dropdown.Option("quincenal", "Quincenal"),
                 ft.dropdown.Option("semanal", "Semanal")],
        value="quincenal", width=150,
    )
    dia_cobro = _campo("Primer día de cobro (1-31)", 15, numerico=True, ancho=180)
    cuenta = _seleccionar_cuenta_dropdown()

    def guardar(e):
        try:
            registrar_ingreso(cat.value or "Sueldo", float(monto.value or 0),
                              tipo="sueldo_recurrente",
                              frecuencia=frecuencia.value,
                              dia_cobro=int(dia_cobro.value) if dia_cobro.value else None,
                              cuenta_id=int(cuenta.value) if cuenta.value else None)
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    filas = []
    for i in ingreso_repo.get_all():
        filas.append(ft.Row([
            ft.Text(f"• {i['categoria']}: ${i['convertido_a_pesos']:,.2f} "
                    f"({i['fecha']})", size=13, expand=True),
            *edicion.botones_edicion(
                edicion.dialogo_editar_ingreso(page, refresh, i),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar el ingreso «{i['categoria']}» de "
                    f"${i['convertido_a_pesos']:,.2f}?",
                    lambda iid=i["id"]: eliminar_ingreso(iid))),
        ], spacing=2))

    return ft.Column([
        ft.Text("Registra tu sueldo fijo (y otros ingresos).", size=14),
        ft.Text("💡 Quincenal con día inicial 15 → cobras el 15 y el 30 "
                "(o último del mes). Mensual → ese día cada mes.",
                size=12, color=ft.Colors.GREY_600),
        ft.Row([cat, monto, frecuencia, dia_cobro, cuenta], wrap=True, spacing=10),
        ft.Button("Guardar ingreso", icon=ft.Icons.SAVE, on_click=guardar),
        _lista_titulo("Tus ingresos (✏️ edita · 🗑 elimina):"),
        *(filas or [ft.Text("Sin ingresos todavía.", size=13,
                            color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d3(page, refresh):
    cuenta = _seleccionar_cuenta_dropdown()
    cat = _dropdown_categorias()
    monto = _campo("Monto", 0, numerico=True)
    desc = _campo("Descripción (opcional)", "")

    def guardar(e):
        try:
            if not cuenta.value:
                raise ValueError(
                    "Selecciona la cuenta donde hiciste el gasto "
                    "(si no hay cuentas, crea una en la Dimensión 1).")
            registrar_gasto(int(cuenta.value), cat.value or CATEGORIA_DEFAULT,
                            float(monto.value or 0),
                            descripcion=desc.value or "")
            refresh()
        except (ValueError, TypeError) as err:
            ui.mostrar_alerta_error(page, ValueError(str(err)))

    filas = []
    for g in gasto_repo.get_all()[:12]:
        filas.append(ft.Row([
            ft.Text(f"• {g['categoria']}: ${g['convertido_a_pesos']:,.2f} "
                    f"({g['fecha']})", size=13, expand=True),
            *edicion.botones_edicion(
                edicion.dialogo_editar_gasto(page, refresh, g),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar el gasto «{g['categoria']}» de "
                    f"${g['convertido_a_pesos']:,.2f}?",
                    lambda gid=g["id"]: eliminar_gasto(gid))),
        ], spacing=2))

    return ft.Column([
        ft.Text("Registra gastos para conocer a dónde va tu dinero "
                "(mínimo 3 para el cofre).", size=14),
        ft.Row([cuenta, cat, monto, desc], wrap=True, spacing=10),
        ft.Button("Guardar gasto", icon=ft.Icons.SAVE, on_click=guardar),
        _lista_titulo("Últimos gastos (✏️ edita · 🗑 elimina):"),
        *(filas or [ft.Text("Sin gastos todavía.", size=13,
                            color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d4(page, refresh):
    nombre = _campo("Nombre de la tarjeta", "Tarjeta crédito")
    corte = _campo("Día de corte (1-31)", 15, numerico=True, ancho=130)
    pago = _campo("Día de pago (1-31)", 5, numerico=True, ancho=130)
    dias = _campo("Días para pagar", 30, numerico=True, ancho=120)

    def guardar(e):
        try:
            tarjeta_id = crear_cuenta(nombre.value or "Tarjeta",
                                      "tarjeta_credito", "MXN", 0.0)
            configurar_tarjeta(tarjeta_id, int(corte.value), int(pago.value),
                               int(dias.value))
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    filas = []
    for t in _tarjetas_activas():
        filas.append(ft.Row([
            ft.Text(f"• {t['nombre']}: corte {t['dia_corte']}, "
                    f"pago {t['dia_pago']}", size=13, expand=True),
            *edicion.botones_edicion(
                edicion.dialogo_editar_cuenta(page, refresh, {
                    "id": t["cuenta_id"], "nombre": t["nombre"],
                    "tipo": "tarjeta_credito",
                    "balance_actual": t["balance_actual"]}),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar la tarjeta «{t['nombre']}»? (Solo si no "
                    "tiene registros ligados.)",
                    lambda tid=t["cuenta_id"]: eliminar_cuenta(tid))),
        ], spacing=2))

    return ft.Column([
        ft.Text("Crea tus tarjetas de crédito. Sus reglas (tasa, límite) "
                "se ajustan en la Dimensión 5.", size=14),
        ft.Row([nombre, corte, pago, dias], wrap=True, spacing=10),
        ft.Button("Guardar tarjeta", icon=ft.Icons.CREDIT_CARD, on_click=guardar),
        _lista_titulo("Tus tarjetas (✏️ edita nombre/deuda · 🗑 elimina):"),
        *(filas or [ft.Text("Sin tarjetas todavía.", size=13,
                            color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d5(page, refresh):
    tarjetas = _tarjetas_activas()
    if not tarjetas:
        return ft.Text("Primero crea una tarjeta en la Dimensión 4.", size=14)
    t = tarjetas[0]
    tasa = _campo("Tasa de interés mensual %", t.get("tasa_interes_mensual") or 0,
                  numerico=True, ancho=170)
    limite = _campo("Límite de crédito", t.get("limite_credito_maximo") or 0,
                    numerico=True, ancho=150)
    minimo = _campo("Mínimo de uso mensual (ej. 2000)", t.get("minimo_uso_monto") or 0,
                    numerico=True, ancho=190)
    cargo = _campo("Cargo por no alcanzar mínimo (ej. 300)",
                   t.get("costo_admin_si_no_alcance") or 0, numerico=True, ancho=210)

    def guardar(e):
        try:
            configurar_tarjeta(
                t["cuenta_id"], t["dia_corte"], t["dia_pago"], t["dias_para_pagar"],
                tasa_interes_mensual=float(tasa.value or 0),
                limite_credito_maximo=float(limite.value or 0) or None,
                minimo_uso_monto=float(minimo.value or 0),
                costo_admin_si_no_alcance=float(cargo.value or 0),
            )
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    return ft.Column([
        ft.Text(f"Configura las reglas de {t['nombre']} (puedes cambiarlas "
                "y guardar de nuevo cuando quieras)", size=14),
        ft.Text("Ejemplo Invex/Sams: mínimo de uso $2,000 y cargo de $300.",
                size=12, color=ft.Colors.GREY_600),
        ft.Row([tasa, limite, minimo, cargo], wrap=True, spacing=10),
        ft.Button("Guardar reglas", icon=ft.Icons.RULE, on_click=guardar),
    ], spacing=8)


def _formulario_d6(page, refresh):
    # ---- 1. Presupuesto general (mensual/quincenal/semanal, equivalentes) ----
    general = obtener_presupuesto_general()
    monto_general = _campo("Presupuesto general",
                           general["monto"] if general else 4000, numerico=True,
                           ancho=180)
    periodo = ft.Dropdown(
        label="Periodo",
        options=[ft.dropdown.Option("mensual", "Mensual"),
                 ft.dropdown.Option("quincenal", "Quincenal"),
                 ft.dropdown.Option("semanal", "Semanal")],
        value=general["periodo"] if general else "mensual",
        width=150,
    )

    def guardar_general(e):
        try:
            definir_presupuesto_general(float(monto_general.value or 0),
                                        periodo.value)
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    if general:
        equivalencias = ft.Text(
            f"✅ General {general['periodo']}: ${general['monto']:,.2f}  →  "
            f"≈ ${general['quincenal']:,.2f} quincenal · "
            f"≈ ${general['semanal']:,.2f} semanal · "
            f"≈ ${general['mensual']:,.2f} mensual",
            size=13, color=ft.Colors.GREEN_700)
    else:
        equivalencias = ft.Text(
            "Define tu presupuesto general: las equivalencias semanal, "
            "quincenal y mensual siempre coinciden.",
            size=13, color=ft.Colors.GREY_700)

    # ---- 2. Distribución por categorías (mismas categorías de los gastos) ----
    cat = _dropdown_categorias()
    monto = _campo("Límite semanal de la categoría", 200, numerico=True,
                   ancho=220)

    def guardar(e):
        try:
            definir_presupuesto_base(cat.value or CATEGORIA_DEFAULT,
                                     float(monto.value or 0))
            refresh()
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)

    def borrar_categoria(categoria):
        def fn(e):
            eliminar_presupuesto_base(categoria)
            refresh()
        return fn

    suma = suma_categorias_base()
    if general:
        color_suma = (ft.Colors.GREEN_700 if suma <= general["semanal"] + 0.01
                      else ft.Colors.RED_600)
        texto_suma = ft.Text(
            f"Repartido: ${suma:,.2f} de ${general['semanal']:,.2f} semanales",
            size=13, weight="bold", color=color_suma)
    else:
        texto_suma = ft.Text(
            f"Repartido: ${suma:,.2f} semanales (define el general primero)",
            size=13, color=ft.Colors.GREY_700)

    base = []
    for b in listar_presupuesto_base():
        base.append(ft.Row([
            ft.Text(f"• {b['categoria']}: ${b['monto_limite_base']:,.2f} /sem",
                    size=13, expand=True),
            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=16,
                          tooltip="Eliminar", icon_color=ft.Colors.RED_400,
                          on_click=borrar_categoria(b["categoria"])),
        ], spacing=2))

    estado = estado_semana()
    cats = [ft.Text(f"• {c['categoria']}: límite ${c['limite']:,.0f} · "
                    f"gastado ${c['gastado']:,.2f}", size=13)
            for c in estado["categorias"]]

    return ft.Column([
        ft.Text("La masmorra del presupuesto: define tu límite general y "
                "reparte semana a semana sin salirte.", size=14),
        ui.subtitulo("1️⃣ Presupuesto general"),
        ft.Row([monto_general, periodo,
                ft.Button("Guardar general", icon=ft.Icons.SAVE,
                          on_click=guardar_general)], wrap=True, spacing=10),
        equivalencias,
        ft.Divider(),
        ui.subtitulo("2️⃣ Reparte por categorías (sin pasarte del general)"),
        ft.Text("Para editar una categoría, vuelve a guardarla con su nuevo "
                "límite; para quitarla, usa 🗑.", size=12,
                color=ft.Colors.GREY_600),
        ft.Row([cat, monto,
                ft.Button("Guardar categoría", icon=ft.Icons.SAVE,
                          on_click=guardar)], wrap=True, spacing=10),
        texto_suma,
        *(base or [ft.Text("Aún no repartes ninguna categoría.", size=13,
                           color=ft.Colors.GREY_600)]),
        ft.Divider(),
        ft.Text(f"Semana actual ({estado['inicio']}):", size=13, weight="bold"),
        *(cats or [ft.Text("Sin categorías esta semana todavía.", size=13,
                           color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d7(page, refresh):
    nombre = _campo("Servicio (ej. Luz, Internet, Netflix)", "Netflix")
    monto = _campo("Monto", 200, numerico=True)
    dia = _campo("Día de cobro (1-31)", 15, numerico=True, ancho=140)
    periodo = ft.Dropdown(
        label="Periodo",
        options=[ft.dropdown.Option("mensual", "Mensual"),
                 ft.dropdown.Option("anual", "Anual")],
        value="mensual", width=120,
    )
    cuenta = _seleccionar_cuenta_dropdown()

    def guardar(e):
        try:
            agregar_suscripcion(nombre.value or "Servicio", float(monto.value or 0),
                                "MXN", int(dia.value or 1), periodo.value,
                                cuenta_id=int(cuenta.value) if cuenta.value else None)
            refresh()
        except (ValueError, TypeError) as err:
            ui.mostrar_alerta_error(page, ValueError(str(err)))

    filas = []
    for s in suscripcion_repo.get_activas():
        filas.append(ft.Row([
            ft.Text(f"• {s['nombre']}: ${s['monto']:,.0f} {s['moneda']} "
                    f"día {s['dia_cobro']}", size=13, expand=True),
            *edicion.botones_edicion(
                edicion.dialogo_editar_suscripcion(page, refresh, s),
                edicion.dialogo_confirmar_borrado(
                    page, refresh,
                    f"¿Eliminar la suscripción «{s['nombre']}»?",
                    lambda sid=s["id"]: eliminar_suscripcion(sid))),
        ], spacing=2))

    return ft.Column([
        ft.Text("Registra tus gastos fijos mensuales y anuales.", size=14),
        ft.Row([nombre, monto, dia, periodo, cuenta], wrap=True, spacing=10),
        ft.Button("Guardar suscripción", icon=ft.Icons.SUBSCRIPTIONS,
                  on_click=guardar),
        _lista_titulo("Tus suscripciones (✏️ edita · 🗑 elimina):"),
        *(filas or [ft.Text("Sin suscripciones todavía.", size=13,
                            color=ft.Colors.GREY_600)]),
    ], spacing=8)


def _formulario_d8(page, refresh):
    def activar(perfil_id):
        def fn(e):
            activar_perfil(perfil_id)
            refresh()
        return fn

    def dialogo_editar(p):
        def fn(e):
            porcentaje = _campo("Pago mínimo %", p["pago_minimo_porcentaje"],
                                numerico=True, ancho=140)
            fijo = _campo("Pago mínimo fijo $", p["pago_minimo_monto_fijo"],
                          numerico=True, ancho=150)
            flujo = _campo("Flujo mínimo de efectivo $",
                           p["flujo_minimo_efectivo"], numerico=True, ancho=190)
            priorizar = ft.Checkbox(
                label="Priorizar la tarjeta con mayor interés",
                value=bool(p["priorizar_intereses_mayores"]))

            def guardar(ev):
                try:
                    actualizar_perfil(p["id"], {
                        "pago_minimo_porcentaje": float(porcentaje.value or 0),
                        "pago_minimo_monto_fijo": float(fijo.value or 0),
                        "flujo_minimo_efectivo": float(flujo.value or 0),
                        "priorizar_intereses_mayores": int(bool(priorizar.value)),
                    })
                    edicion.cerrar_dialogo(page, dlg)
                    refresh()
                except (ValueError, TypeError) as err:
                    edicion.cerrar_dialogo(page, dlg)
                    ui.mostrar_alerta_error(page, ValueError(str(err)))

            dlg = ft.AlertDialog(
                title=ft.Text(f"✏️ Editar perfil {p['nombre']}"),
                content=ft.Column([
                    ft.Row([porcentaje, fijo], wrap=True, spacing=8),
                    flujo, priorizar,
                    ft.Row([ft.Button("Guardar cambios", icon=ft.Icons.SAVE,
                                      on_click=guardar),
                            ft.TextButton("Cancelar", on_click=lambda ev2:
                                          edicion.cerrar_dialogo(page, dlg))],
                           spacing=8),
                ], tight=True, width=340, spacing=8),
            )
            page.show_dialog(dlg)
        return fn

    filas = []
    activo = perfil_repo.get_activo()
    for p in listar_perfiles():
        etiqueta = " ✅ activo" if activo and p["id"] == activo["id"] else ""
        filas.append(ft.Row([
            ft.Text(f"{p['nombre']} ({p['tipo_perfil']}){etiqueta}",
                    size=13, expand=True),
            ft.IconButton(ft.Icons.EDIT, icon_size=16, tooltip="Editar",
                          on_click=dialogo_editar(p)),
            ft.Button("Activar", on_click=activar(p["id"]), width=100),
        ], spacing=2))

    return ft.Column([
        ft.Text("Elige y ajusta tu estrategia de pago de deudas.", size=14),
        ft.Text("Mínimo: paga lo mínimo · Optimizado: protege liquidez · "
                "Agresivo: liquida rápido manteniendo reserva · Custom: a tu medida.",
                size=12, color=ft.Colors.GREY_600),
        ft.Text("💡 También puedes cambiar el perfil activo en la sección "
                "Configuración.", size=12, italic=True,
                color=ft.Colors.BLUE_700),
        *filas,
    ], spacing=6)


FORMULARIOS = {
    1: _formulario_d1, 2: _formulario_d2, 3: _formulario_d3, 4: _formulario_d4,
    5: _formulario_d5, 6: _formulario_d6, 7: _formulario_d7, 8: _formulario_d8,
}


def build(page: ft.Page, refresh, dimension: int, estado_local: dict) -> ft.Control:
    info = info_dimension(dimension)
    requisito_texto, requisito_ok = REQUISITOS[dimension]
    cumple = requisito_ok()
    premio = premio_dimension(dimension)
    repeticion = premio["repeticion"]

    form = FORMULARIOS[dimension](page, refresh)

    def completar(e):
        # Tras completar se vuelve al mapa; el servicio entrega el cofre
        # (premio completo la primera vez, premio de repetición al rejugar).
        try:
            payload = completar_dimension(dimension)
            estado_local.clear()
            refresh("dimensiones")  # vuelve al mapa con la nueva dimensión abierta
            ui.dialogo_cofre(page, payload)  # cofre encima del mapa
        except ValueError as err:
            ui.mostrar_alerta_error(page, err)
        except Exception as err:  # noqa: BLE001 — diagnóstico de errores inesperados
            import traceback
            from src.ui.sonido import reproducir
            detalle = "".join(traceback.format_exception(type(err), err, err.__traceback__))
            with open("data/app.log", "a", encoding="utf-8") as f:
                f.write(f"\n[ERROR completar_dimension] {detalle}\n")
            reproducir("error", page)
            page.show_dialog(ft.AlertDialog(
                title=ft.Text("Error inesperado", color=ft.Colors.RED_600),
                content=ft.Text(str(err), selectable=True),
            ))

    btn = ft.Button(
        (f"🔁 Rejugar Dimensión {dimension} · +{premio['puntos']} pts"
         if repeticion else f"✅ Completar Dimensión {dimension}"),
        icon=ft.Icons.REPLAY if repeticion else ft.Icons.CHECK_CIRCLE,
        on_click=completar,
        disabled=not cumple,
    )
    if not cumple:
        btn.tooltip = f"Requisito: {requisito_texto}"

    nota_rejugar = ft.Text(
        f"🔁 Dimensión iterativa: ya la superaste, pero puedes añadir o "
        f"corregir registros y guardar de nuevo para ganar "
        f"+{premio['puntos']} pts y +{premio['xp']} XP.",
        size=12, color=ft.Colors.PURPLE_700) if repeticion else ft.Container()

    cuerpo = ft.Column(
        [
            ft.Row(
                [ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: refresh("dimensiones")),
                 ui.titulo(f"Dimensión {dimension}: {info['nombre']}")],
                spacing=4,
            ),
            ft.Text(info["mision"], size=14, color=ft.Colors.GREY_700),
            ft.Text(f"Requisito: {requisito_texto}"
                    + (" ✅" if cumple else " ⏳ (pendiente)"), size=12,
                    color=ft.Colors.GREEN_700 if cumple else ft.Colors.AMBER_700),
            nota_rejugar,
            ft.Divider(),
            form,
            ft.Divider(),
            btn,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=10,
    )

    # Fondo de la dimensión (el paisaje cambia con el portal, Fase 3).
    # El contenido va sobre un panel blanco translúcido para legibilidad.
    fondo_img = FONDOS.get(info["fondo"])
    if not fondo_img:
        return cuerpo
    return ft.Container(
        content=ft.Container(
            content=cuerpo,
            padding=16,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.88, ft.Colors.WHITE),
            expand=True,
        ),
        image=ft.DecorationImage(src=ui.ruta_asset(fondo_img),
                                 fit=ft.BoxFit.COVER),
        padding=12,
        expand=True,
    )
