"""Personaje RPG: niveles, progreso por dimensiones y configuración.

Progresión (ajuste del diseño): la progresión SON los niveles del personaje.
- El Guardián inicia en **Nivel 1** con la Dimensión 1 desbloqueada.
- Completar la Dimensión N → el personaje sube a Nivel N+1, que abre el
  portal de la Dimensión N+1 (hasta la 8, Salón de Estrategas).
- Las dimensiones son **iterativas**: se pueden rejugar para editar o
  añadir registros y seguir ganando cofres (premio de repetición).
"""

from typing import Any, Dict, Optional

from src.database import get_connection
from src.repositories import personaje_repo
from src.services.convertidor import set_tipo_cambio
from src.services.inventario import FONDOS, _fila_armadura, equipar_armadura, equipar_fondo

MAX_NIVEL = 8  # 8 dimensiones (la 8 es el Salón de Estrategas)


def obtener_personaje() -> Dict[str, Any]:
    """Personaje del jugador (se crea por defecto si no existe)."""
    p = personaje_repo.get_default()
    if not p:
        personaje_repo.create({
            "id": 1, "nombre": "Guardián", "nivel": 1,
            "dimensiones_completadas": 0, "puntos_experiencia": 0,
            "armadura_actual": "gris", "fondo_actual": "default",
            "tipo_cambio_favorito": 18.63,
        })
        p = personaje_repo.get_default()
    return p


def configurar_personaje(
    nombre: Optional[str] = None,
    fondo: Optional[str] = None,
    armadura: Optional[str] = None,
    tipo_cambio: Optional[float] = None,
) -> Dict[str, Any]:
    """Configuración del personaje, accesible desde cualquier dimensión.

    - ``nombre``: renombra al Guardián.
    - ``fondo``: fondo visual (libre, temas generales por versión).
    - ``armadura``: equipa una calidad desbloqueada del inventario.
    - ``tipo_cambio``: actualiza el tipo de cambio global USD→MXN.
    """
    obtener_personaje()
    cambios = {}
    if nombre:
        cambios["nombre"] = nombre.strip()
    if fondo is not None:
        if fondo not in FONDOS:
            raise ValueError(f"Fondo inválido. Disponibles: {sorted(FONDOS)}")
        cambios["fondo_actual"] = fondo
    if armadura is not None:
        equipar_armadura(armadura)  # valida que esté desbloqueada
    if tipo_cambio is not None:
        set_tipo_cambio(tipo_cambio)
        cambios["tipo_cambio_favorito"] = float(tipo_cambio)
    if cambios:
        personaje_repo.update(1, cambios)
    return obtener_personaje()


def progreso() -> Dict[str, Any]:
    """Estado de progresión RPG del personaje."""
    p = obtener_personaje()
    completadas = int(p["dimensiones_completadas"])
    nivel = int(p["nivel"])
    juego_completado = completadas >= MAX_NIVEL
    return {
        "nombre": p["nombre"],
        "nivel": nivel,
        "dimensiones_completadas": completadas,
        "dimension_actual": None if juego_completado else nivel,
        "puntos_experiencia": int(p["puntos_experiencia"]),
        "armadura": p["armadura_actual"],
        "fondo": p["fondo_actual"],
        "juego_completado": juego_completado,
    }


def registrar_dimension_completada() -> Dict[str, Any]:
    """Sube el nivel tras completar la dimensión actual (uso interno de cofres)."""
    p = obtener_personaje()
    completadas = min(int(p["dimensiones_completadas"]) + 1, MAX_NIVEL)
    nuevo_nivel = min(completadas + 1, MAX_NIVEL)
    personaje_repo.update(1, {
        "dimensiones_completadas": completadas,
        "nivel": nuevo_nivel,
    })
    p = obtener_personaje()
    return {
        "nivel_nuevo": int(p["nivel"]),
        "dimensiones_completadas": int(p["dimensiones_completadas"]),
        "dimension_desbloqueada": None if completadas >= MAX_NIVEL else int(p["nivel"]),
        "juego_completado": completadas >= MAX_NIVEL,
    }


def sumar_experiencia(xp: int) -> int:
    """Suma puntos de experiencia (métrica de logros, no sube nivel)."""
    xp = int(xp)
    if xp <= 0:
        raise ValueError("La XP debe ser mayor que cero.")
    p = obtener_personaje()
    personaje_repo.update(1, {"puntos_experiencia": int(p["puntos_experiencia"]) + xp})
    return int(obtener_personaje()["puntos_experiencia"])


# ---------------------------------------------------------------------------
# Avatar: el Guardián refleja tu estado financiero
# ---------------------------------------------------------------------------

ESTADOS_GUARDIAN = {
    "legendario": {
        "titulo": "🌟 Guardián Legendario",
        "imagen": "assets/personaje/guardian_legendario.png",
        "consejo": "Sin deuda y sin alertas: tus finanzas están en su máximo "
                   "esplendor. ¡Sigue así!",
    },
    "fuerte": {
        "titulo": "🛡️ Guardián Fuerte",
        "imagen": "assets/personaje/guardian_fuerte.png",
        "consejo": "Todo bajo control. Revisa tu presupuesto semanal para "
                   "mantener la racha.",
    },
    "herido": {
        "titulo": "🩹 Guardián Herido",
        "imagen": "assets/personaje/guardian_herido.png",
        "consejo": "Hay alertas amarillas: gastas cerca del límite. Ajusta "
                   "tus gastos planeados esta semana.",
    },
    "critico": {
        "titulo": "🔥 Guardián en Peligro",
        "imagen": "assets/personaje/guardian_critico.png",
        "consejo": "Alertas rojas: te saliste del presupuesto o de tus "
                   "límites. Ataca primero el gasto más grande.",
    },
}


def estado_guardian() -> Dict[str, Any]:
    """Estado visual del avatar según las finanzas actuales.

    - ``critico``: algún riesgo rojo o la semana en rojo (te pasaste).
    - ``herido``: riesgos amarillos o semana en amarillo.
    - ``legendario``: sin alertas, semana verde y sin deuda de tarjetas.
    - ``fuerte``: todo lo demás en orden (con deuda bajo control).
    """
    from src.services.cuentas import deuda_total_pesos
    from src.services.deteccion_riesgos import evaluar_riesgos
    from src.services.presupuesto_semanal import estado_semana

    riesgos = evaluar_riesgos()
    semana = estado_semana()
    niveles = {a["nivel"] for a in riesgos}
    semaforo = semana["semaforo_total"]

    if "rojo" in niveles or semaforo == "rojo":
        estado = "critico"
    elif "amarillo" in niveles or semaforo == "amarillo":
        estado = "herido"
    elif deuda_total_pesos() <= 0:
        estado = "legendario"
    else:
        estado = "fuerte"

    return {
        "estado": estado,
        **ESTADOS_GUARDIAN[estado],
        "alertas_rojas": sum(1 for a in riesgos if a["nivel"] == "rojo"),
        "alertas_amarillas": sum(1 for a in riesgos if a["nivel"] == "amarillo"),
        "semaforo_semana": semaforo,
        "deuda_total": deuda_total_pesos(),
    }


def resumen_configuracion() -> Dict[str, Any]:
    """Vista de configuración del personaje (para la pantalla de ajustes)."""
    p = obtener_personaje()
    return {
        "nombre": p["nombre"],
        "armadura_actual": p["armadura_actual"],
        "fondo_actual": p["fondo_actual"],
        "tipo_cambio_actual": p["tipo_cambio_favorito"],
        "fondos_disponibles": list(FONDOS.keys()),
    }
