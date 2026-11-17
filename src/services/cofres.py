"""Cofres estilo Zelda: premio al completar cada dimensión.

Flujo:
1. El jugador completa la misión de la dimensión de su nivel actual.
2. ``completar_dimension`` valida que no se adelante a dimensiones aún
   bloqueadas.
3. Abre el cofre (sonido en UI): otorga puntos + XP, entrega el badge
   correspondiente si existe, y sube el nivel del personaje,
   desbloqueando el portal a la siguiente dimensión.

**Las dimensiones son iterativas**: puedes volver a cualquier dimensión
ya desbloqueada para añadir, editar o eliminar registros y volver a
guardar. Al rejugarla el cofre vuelve a dar premio (la mitad de puntos y
XP que la primera vez), pero el nivel no se repite ni baja.

Recompensas: primera vez = 100 × dimensión pts y 50 × dimensión XP.
Repetición = 50 × dimensión pts y 25 × dimensión XP.
"""

from typing import Any, Dict

from src.services import badges, personaje as personaje_svc, puntos as puntos_svc

DIMENSIONES = [
    {"n": 1, "nombre": "El Despertar", "mision": "Crea tu primera cuenta y saldo inicial"},
    {"n": 2, "nombre": "El Camino del Oro", "mision": "Registra tu sueldo e ingresos"},
    {"n": 3, "nombre": "Bosque de Gastos", "mision": "Registra tus gastos diarios"},
    {"n": 4, "nombre": "Puerta del Crédito", "mision": "Crea tu primera tarjeta"},
    {"n": 5, "nombre": "Cámara de Reglas", "mision": "Configura tasas, límites y mínimos"},
    {"n": 6, "nombre": "Llanura del Presupuesto", "mision": "Define tu presupuesto semanal"},
    {"n": 7, "nombre": "Mercado de Suscripciones", "mision": "Registra tus gastos fijos"},
    {"n": 8, "nombre": "Salón de Estrategas", "mision": "Configura tus perfiles de pago"},
]

TOTAL_DIMENSIONES = len(DIMENSIONES)

CHEST_POR_DIMENSION = {
    1: "madera", 2: "hierro", 3: "bronce", 4: "plata", 5: "oro",
    6: "esmeralda", 7: "zafiro", 8: "diamante",
}

BADGE_POR_DIMENSION = {
    1: "Primera cuenta",
    2: "Primer ingreso",
    3: "Primer gasto",
    4: "Primera tarjeta",
    5: "Maestro de reglas",
    8: "Guardián Supremo",
}

FONDO_POR_DIMENSION = {
    1: "d1_despertar_dia",
    2: "d2_camino_oro",
    3: "d3_bosque_gastos",
    4: "d4_puerta_credito",
    5: "d5_camara_reglas",
    6: "d6_llanura_presupuesto",
    7: "d7_mercado_suscripciones",
    8: "d9_salon_estrategas",
}


def info_dimension(dimension: int) -> Dict[str, Any]:
    """Datos de una dimensión: nombre, cofre, fondo y badge asociado."""
    for d in DIMENSIONES:
        if d["n"] == int(dimension):
            return {
                **d,
                "cofre": CHEST_POR_DIMENSION[dimension],
                "cofre_imagen": f"assets/cofres/cofre_{CHEST_POR_DIMENSION[dimension]}.png",
                "fondo": FONDO_POR_DIMENSION.get(dimension),
                "badge": BADGE_POR_DIMENSION.get(dimension),
            }
    raise ValueError(
        f"Dimensión inválida: {dimension}. Debe estar entre 1 y {TOTAL_DIMENSIONES}.")


def es_repeticion(dimension: int) -> bool:
    """True si la dimensión ya se había completado antes (cofre repetido)."""
    prog = personaje_svc.progreso()
    return dimension < prog["nivel"] or prog["juego_completado"]


def premio_dimension(dimension: int) -> Dict[str, int]:
    """Puntos y XP del cofre: completo la primera vez, mitad al rejugar."""
    repeticion = es_repeticion(dimension)
    return {
        "puntos": (50 if repeticion else 100) * dimension,
        "xp": (25 if repeticion else 50) * dimension,
        "repeticion": repeticion,
    }


def abrir_cofre(dimension: int) -> Dict[str, Any]:
    """Abre el cofre de una dimensión desbloqueada.

    Valida que no te adelantes a dimensiones bloqueadas. Rejugar una
    dimensión ya completada está permitido y vuelve a dar premio (mitad).
    """
    info = info_dimension(dimension)
    prog = personaje_svc.progreso()

    if dimension > prog["nivel"] and not prog["juego_completado"]:
        raise ValueError(
            f"Primero completa la Dimensión {prog['nivel']}: "
            f"{info_dimension(prog['nivel'])['nombre']}."
        )

    premio = premio_dimension(dimension)
    saldo = puntos_svc.ganar_puntos(premio["puntos"])
    xp_total = personaje_svc.sumar_experiencia(premio["xp"])

    badge_payload = None
    if info["badge"] and not premio["repeticion"]:
        badge_payload = badges.otorgar_badge(nombre=info["badge"])

    return {
        "dimension": dimension,
        "nombre_dimension": info["nombre"],
        "cofre": info["cofre"],
        "cofre_imagen": info["cofre_imagen"],
        "puntos_ganados": premio["puntos"],
        "xp_ganada": premio["xp"],
        "puntos_totales": saldo,
        "xp_total": xp_total,
        "badge": badge_payload,
        "repeticion": premio["repeticion"],
        "es_master": dimension == TOTAL_DIMENSIONES and not premio["repeticion"],
    }


def completar_dimension(dimension: int) -> Dict[str, Any]:
    """Registra la dimensión como completada y entrega su cofre.

    Si es la dimensión del nivel actual, sube el nivel y abre el portal
    siguiente. Si es una repetición (dimensión ya superada), solo entrega
    el premio: el nivel y las dimensiones completadas no cambian.
    """
    prog_antes = personaje_svc.progreso()
    cofre = abrir_cofre(dimension)

    if cofre["repeticion"]:
        return {
            **cofre,
            "nivel_nuevo": prog_antes["nivel"],
            "nivel_antes": prog_antes["nivel"],
            "dimensiones_completadas": prog_antes["dimensiones_completadas"],
            "dimension_desbloqueada": prog_antes["dimension_actual"],
            "juego_completado": prog_antes["juego_completado"],
            "mensaje": (
                f"¡Cofre de repetición! +{cofre['puntos_ganados']} pts y "
                f"+{cofre['xp_ganada']} XP. Tus registros quedaron "
                "actualizados; vuelve cuando quieras."
            ),
        }

    avance = personaje_svc.registrar_dimension_completada()
    return {
        **cofre,
        "nivel_nuevo": avance["nivel_nuevo"],
        "nivel_antes": prog_antes["nivel"],
        "dimensiones_completadas": avance["dimensiones_completadas"],
        "dimension_desbloqueada": avance["dimension_desbloqueada"],
        "juego_completado": avance["juego_completado"],
        "mensaje": (
            "¡Eres el Guardián Supremo! Todas las dimensiones conquistadas. "
            "Puedes rejugar cualquiera para seguir ganando cofres."
            if avance["juego_completado"]
            else f"¡Nivel {avance['nivel_nuevo']} alcanzado! "
                 f"Portal abierto: Dimensión {avance['dimension_desbloqueada']}."
        ),
    }


def estado_progresion() -> Dict[str, Any]:
    """Vista completa para el mapa de dimensiones en la UI."""
    prog = personaje_svc.progreso()
    dimensiones = []
    for d in DIMENSIONES:
        completada = d["n"] <= prog["dimensiones_completadas"]
        desbloqueada = d["n"] <= prog["nivel"] or prog["juego_completado"]
        dimensiones.append({**info_dimension(d["n"]), "completada": completada,
                            "desbloqueada": desbloqueada})
    return {"personaje": prog, "dimensiones": dimensiones}
