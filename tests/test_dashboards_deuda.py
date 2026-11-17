"""Pruebas de dashboards por perfil y de la vista Deuda (Gantt).

Verifica:
- Los perfiles predefinidos traen módulos de dashboard por defecto
  (semilla), así el Resumen sí muestra secciones.
- El Resumen renderiza las secciones según los módulos del perfil activo.
- El perfil de pago se puede cambiar desde Personaje.
- La vista Deuda dibuja las barras mes a mes según la estrategia.

Se ejecuta como script:  uv run python tests/test_dashboards_deuda.py
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_dashboards.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import flet as ft

from src.database import init_db
from src.repositories import perfil_repo
from src.services import (
    activar_perfil,
    configurar_tarjeta,
    crear_cuenta,
    listar_perfiles,
    modulos_visibles,
    obtener_perfil_activo,
    registrar_gasto,
)
from src.ui.views import configuracion, deuda, personaje, resumen

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    # La consola de Windows (cp1252) no imprime emojis ni flechas.
    seguro = str(detalle).encode("ascii", "replace").decode()
    nombre_seguro = str(nombre).encode("ascii", "replace").decode()
    print(f"[{estado}] {nombre_seguro}" + (f" -> {seguro}" if detalle else ""))


class MockPage:
    def __init__(self):
        self.overlay = []
        self.dialogos = []

    def show_dialog(self, dlg):
        self.dialogos.append(dlg)

    def update(self):
        pass

    def run_task(self, handler, *args):
        import asyncio
        return asyncio.run(handler(*args))


def _hijos(control):
    if hasattr(control, "controls") and control.controls:
        yield from control.controls
    contenido = getattr(control, "content", None)
    if contenido is not None and isinstance(contenido, ft.Control):
        yield contenido


def caminar(raiz):
    pila = [raiz]
    while pila:
        c = pila.pop()
        yield c
        pila.extend(_hijos(c))


def textos(raiz):
    out = []
    for c in caminar(raiz):
        if isinstance(c, ft.Text) and isinstance(c.value, str):
            out.append(c.value)
    return out


class Evt:
    def __init__(self, control=None):
        self.control = control


def _texto_boton(btn):
    for attr in ("content", "text", "label"):
        valor = getattr(btn, attr, None)
        if isinstance(valor, str) and valor:
            return valor
    return ""


def main():
    init_db()

    # ---------- Semilla: módulos por defecto por perfil ----------
    por_tipo = {p["tipo_perfil"]: p for p in listar_perfiles()}
    visibles = {t: [m["nombre_modulo"] for m in modulos_visibles(p["id"])]
                for t, p in por_tipo.items()}
    check("Mínimo trae resumen + riesgos por defecto",
          visibles["minimo"] == ["resumen_financiero", "riesgos_alertas"],
          str(visibles["minimo"]))
    check("Optimizado trae 4 módulos por defecto",
          visibles["optimizado"] == ["resumen_financiero", "riesgos_alertas",
                                     "suscripciones", "presupuesto_semanal"],
          str(visibles["optimizado"]))
    check("Agresivo incluye proyección de deuda",
          "proyeccion_deuda" in visibles["agresivo"], str(visibles["agresivo"]))
    check("Custom trae base y se arma en la D10",
          visibles["custom"] == ["resumen_financiero", "riesgos_alertas"])

    # ---------- Datos: tarjeta con deuda ----------
    cuenta_id = crear_cuenta("Nómina", "cuenta", "MXN", 3000.0)
    tarjeta_id = crear_cuenta("Invex", "tarjeta_credito", "MXN", 0.0)
    configurar_tarjeta(tarjeta_id, 15, 5, 20, tasa_interes_mensual=3.5,
                       limite_credito_maximo=15000.0)
    registrar_gasto(tarjeta_id, "Tecnología", 6000.0)  # deuda 6000

    page = MockPage()
    refrescos = []

    def refresh(destino=None):
        refrescos.append(destino or "actual")

    # ---------- Resumen muestra los módulos del perfil activo ----------
    activar_perfil(por_tipo["optimizado"]["id"])
    v_res = resumen.build(page, refresh)
    txt = textos(v_res)
    check("Resumen dice qué dashboard muestra",
          any("Dashboard del perfil Optimizado" in t for t in txt))
    check("Resumen (Optimizado) muestra riesgos",
          any("Riesgos" in t for t in txt))
    check("Resumen (Optimizado) muestra suscripciones",
          any("Suscripciones" in t for t in txt))
    check("Resumen (Optimizado) muestra presupuesto semanal",
          any("Presupuesto semanal" in t for t in txt))
    check("Resumen (Optimizado) NO muestra proyección (no es su módulo)",
          not any("Proyección de deuda" in t for t in txt))

    activar_perfil(por_tipo["agresivo"]["id"])
    v_res2 = resumen.build(page, refresh)
    txt2 = textos(v_res2)
    check("Resumen (Agresivo) SÍ muestra proyección de deuda",
          any("Proyección de deuda" in t for t in txt2))
    check("Proyección resume pago y meses para liquidar",
          any("liquidas en" in t for t in txt2),
          str([t for t in txt2 if "liquidas" in t]).encode(
              "ascii", "replace").decode())

    # ---------- Perfil de pago se cambia en Configuración ----------
    v_cfg = configuracion.build(page, refresh)
    txt_c = textos(v_cfg)
    check("Configuración tiene la sección de perfil de pago",
          any("Perfil de pago" in t for t in txt_c))
    botones_activar = [b for b in caminar(v_cfg)
                       if isinstance(b, ft.Button)
                       and _texto_boton(b) == "Activar"]
    check("Configuración muestra botones Activar en perfiles no activos",
          len(botones_activar) == 3, f"{len(botones_activar)} botones")
    n_refrescos = len(refrescos)
    botones_activar[0].on_click(Evt())
    check("Activar perfil desde Configuración refresca y cambia el activo",
          len(refrescos) == n_refrescos + 1
          and obtener_perfil_activo()["tipo_perfil"] != "agresivo",
          obtener_perfil_activo()["nombre"])

    # ---------- Personaje: avatar según estado financiero ----------
    v_per = personaje.build(page, refresh)
    imagenes = [c.src for c in caminar(v_per)
                if isinstance(c, ft.Image)]
    check("Personaje muestra el avatar del Guardián",
          any("guardian_" in (src or "") for src in imagenes),
          str(imagenes))
    check("Personaje indica el estado financiero del avatar",
          any("Guardián" in t for t in textos(v_per)))

    # ---------- Vista Deuda (Gantt) ----------
    activar_perfil(por_tipo["agresivo"]["id"])
    estado = {}
    v_deuda = deuda.build(page, refresh, estado)
    txt_d = textos(v_deuda)
    check("Deuda muestra la estrategia seleccionada",
          any("Agresivo" in t for t in txt_d))
    check("Deuda tiene 12 filas de meses (M1..M12)",
          all(any(t.startswith(f"M{i:>2}") for t in txt_d)
              for i in (1, 6, 12)),
          str([t for t in txt_d if t.startswith("M")][:3]))
    check("Deuda muestra fecha de liquidación",
          any("Liquidas en" in t for t in txt_d),
          str([t for t in txt_d if "Liquidas" in t]))
    barras = [c for c in caminar(v_deuda)
              if isinstance(c, ft.Container) and c.height == 16]
    # El recorrido DFS las devuelve al revés (M12..M1): los anchos deben
    # ir de menor a mayor en ese orden, y ninguna supera el ancho máximo.
    anchos = [b.width for b in barras]
    check("Las barras del Gantt existen y van bajando",
          len(barras) == 12 and anchos == sorted(anchos)
          and anchos[0] < anchos[-1] <= 380,
          f"{min(anchos):.0f} .. {max(anchos):.0f}")

    # Cambiar estrategia desde el selector
    seg = next(c for c in caminar(v_deuda)
               if isinstance(c, ft.SegmentedButton))
    minimo_id = str(por_tipo["minimo"]["id"])
    seg.selected = [minimo_id]
    seg.on_change(Evt(control=seg))
    check("Selector cambia la estrategia de proyección",
          estado["perfil_id"] == por_tipo["minimo"]["id"])
    v_deuda2 = deuda.build(page, refresh, estado)
    txt_d2 = textos(v_deuda2)
    check("Deuda reproyecta con Mínimo (pago menor → más meses)",
          any("Mínimo" in t for t in txt_d2)
          and any("Liquidas en" in t or "no se liquida" in t for t in txt_d2))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
