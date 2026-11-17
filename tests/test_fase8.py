"""Pruebas de la Fase 8: personaje, niveles, cofres, armaduras y badges.

Se ejecuta como script:  uv run python tests/test_fase8.py
Usa una base de datos temporal aislada (variable FINANZAS_DB).
"""

import os
import sys
import tempfile

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase8.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.services import (
    obtener_personaje,
    configurar_personaje,
    progreso,
    obtener_puntos,
    ganar_puntos,
    listar_armaduras,
    desbloquear_armadura,
    equipar_armadura,
    equipar_fondo,
    listar_fondos,
    listar_badges,
    otorgar_badge,
    badges_del_usuario,
    badge_otorgado,
    info_dimension,
    abrir_cofre,
    completar_dimension,
    estado_progresion,
    get_tipo_cambio,
)

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def esperar_error(fn, fragmento):
    try:
        fn()
        return False, "no lanzó error"
    except ValueError as e:
        return fragmento.lower() in str(e).lower(), str(e)
    except Exception as e:  # noqa: BLE001
        return False, f"excepción inesperada: {e}"


def main():
    init_db()

    # ---------- A. Personaje default ----------
    p = obtener_personaje()
    check("Personaje default: Guardián, nivel 1, gris",
          p["nombre"] == "Guardián" and p["nivel"] == 1
          and p["armadura_actual"] == "gris" and p["dimensiones_completadas"] == 0)
    check("Puntos iniciales = 0", obtener_puntos() == 0)
    armaduras = listar_armaduras()
    check("5 armaduras sembradas, solo gris desbloqueada",
          len(armaduras) == 5
          and sum(1 for a in armaduras if a["desbloqueada"]) == 1
          and armaduras[0]["calidad"] == "gris")
    check("6 badges sembrados, ninguno otorgado",
          len(listar_badges()) == 6 and len(badges_del_usuario()) == 0)

    # ---------- B. Inventario ----------
    ok, det = esperar_error(lambda: equipar_armadura("verde"), "no está desbloqueada")
    check("Equipar sin desbloquear lanza error", ok, det)
    ok, det = esperar_error(lambda: desbloquear_armadura("verde"), "faltan")
    check("Desbloquear sin puntos lanza error", ok, det)
    ganar_puntos(500)
    res = desbloquear_armadura("verde")
    check("Verde desbloqueada por 200 puntos", res["puntos_restantes"] == 300,
          str(res))
    equipar_armadura("verde")
    check("Verde equipada", obtener_personaje()["armadura_actual"] == "verde")
    ok, det = esperar_error(lambda: equipar_armadura("azul"), "no está desbloqueada")
    check("Equipar azul bloqueada lanza error", ok, det)
    ok, det = esperar_error(lambda: equipar_fondo("falso"), "Fondo inválido")
    check("Fondo inválido lanza error", ok, det)
    equipar_fondo("d1_despertar_dia")
    check("Fondo d1 equipado", obtener_personaje()["fondo_actual"] == "d1_despertar_dia")
    check("Catálogo de fondos incluye 15 opciones", len(listar_fondos()) == 15)

    # ---------- C. Configuración del personaje ----------
    configurar_personaje(nombre="Miguel", tipo_cambio=19.10)
    check("Nombre actualizado", obtener_personaje()["nombre"] == "Miguel")
    check("Tipo de cambio global actualizado a 19.10",
          abs(get_tipo_cambio() - 19.10) < 1e-9, str(get_tipo_cambio()))
    configurar_personaje(tipo_cambio=18.63)

    # ---------- D. Progresión inicial ----------
    prog = progreso()
    check("Progreso: nivel 1, dimensión actual 1, 0 completadas",
          prog["nivel"] == 1 and prog["dimension_actual"] == 1
          and prog["dimensiones_completadas"] == 0
          and prog["juego_completado"] is False)

    # ---------- E. No adelantar, no repetir ----------
    ok, det = esperar_error(lambda: completar_dimension(2), "primero completa")
    check("No se puede adelantar a la Dimensión 2", ok, det)
    c1 = completar_dimension(1)
    check("Dimensión 1 completada: cofre madera",
          c1["cofre"] == "madera" and c1["puntos_ganados"] == 100
          and c1["xp_ganada"] == 50)
    check("Nivel subió a 2 y desbloquea Dimensión 2",
          c1["nivel_nuevo"] == 2 and c1["dimension_desbloqueada"] == 2)
    check("Badge 'Primera cuenta' otorgado",
          c1["badge"] and c1["badge"]["nuevo"] is True
          and badge_otorgado(c1["badge"]["badge"]["id"]))
    check("Puntos tras cofre 1 = 400", obtener_puntos() == 400, str(obtener_puntos()))
    # Las dimensiones son iterativas: rejugar D1 da premio de repetición
    rep = completar_dimension(1)
    check("Rejugar D1 da cofre de repetición (+50 pts, +25 XP, sin bajar nivel)",
          rep["repeticion"] and rep["puntos_ganados"] == 50
          and rep["xp_ganada"] == 25 and rep["nivel_nuevo"] == 2)
    check("Puntos tras cofre 1 y su repetición = 450",
          obtener_puntos() == 450, str(obtener_puntos()))

    # ---------- F. Dimensiones 2 a 5 ----------
    for d in range(2, 6):
        completar_dimension(d)
    prog = progreso()
    check("Tras D5: nivel 6, 5 completadas",
          prog["nivel"] == 6 and prog["dimensiones_completadas"] == 5,
          f"nivel={prog['nivel']} comp={prog['dimensiones_completadas']}")
    # puntos: 450 + (200+300+400+500) = 1850 ; xp: 75 + (100+150+200+250) = 775
    check("Puntos acumulados = 1850", obtener_puntos() == 1850, str(obtener_puntos()))
    check("XP acumulada = 775", prog["puntos_experiencia"] == 775,
          str(prog["puntos_experiencia"]))
    check("Badge 'Maestro de reglas' otorgado en D5",
          badge_otorgado(next(b["id"] for b in listar_badges()
                              if b["nombre"] == "Maestro de reglas")))

    # ---------- G. Hasta la última dimensión (8: Salón de Estrategas) ----------
    for d in range(6, 9):
        ultimo = completar_dimension(d)
    prog = progreso()
    check("Juego completado: nivel 8, 8 dimensiones",
          prog["nivel"] == 8 and prog["dimensiones_completadas"] == 8
          and prog["juego_completado"] is True and prog["dimension_actual"] is None)
    check("Último mensaje de Guardián Supremo",
          "Guardián Supremo" in ultimo["mensaje"], ultimo["mensaje"])
    # puntos: 1850 + (600+700+800) = 3950
    check("Puntos finales = 3950", obtener_puntos() == 3950, str(obtener_puntos()))
    check("6 badges otorgados en total", len(badges_del_usuario()) == 6,
          str([b["nombre"] for b in badges_del_usuario()]))

    # ---------- H. Compras del inventario (con cofres de repetición) ----------
    completar_dimension(8)  # +400 pts
    completar_dimension(8)  # +400 pts -> 4750
    res = desbloquear_armadura("naranja")
    check("Naranja desbloqueada (3000), saldo 1750", res["puntos_restantes"] == 1750)
    equipar_armadura("naranja")
    check("Naranja equipada", obtener_personaje()["armadura_actual"] == "naranja")
    desbloquear_armadura("azul")
    desbloquear_armadura("morado")
    check("Azul y morado desbloqueadas (50 restante)",
          obtener_puntos() == 50, str(obtener_puntos()))
    inv = listar_armaduras()
    check("Todo el inventario desbloqueado",
          all(a["desbloqueada"] for a in inv) and inv[-1]["equipada"] is True)

    # ---------- I. Rejugar tras completar todo sigue dando premio ----------
    rep_final = completar_dimension(8)
    check("Tras el final se puede seguir rejugando (+400 pts)",
          rep_final["repeticion"] and rep_final["puntos_ganados"] == 400
          and obtener_puntos() == 450, str(obtener_puntos()))

    ep = estado_progresion()
    check("Mapa: 8 dimensiones, todas desbloqueadas y completadas",
          len(ep["dimensiones"]) == 8
          and all(d["completada"] and d["desbloqueada"] for d in ep["dimensiones"]))

    total = len(PASADAS)
    ok_n = sum(PASADAS)
    print(f"\nResultado: {ok_n}/{total} pruebas pasadas")
    if ok_n != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
