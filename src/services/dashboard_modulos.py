"""Configuración de módulos de dashboard por perfil.

Cada perfil (Mínimo, Optimizado, Agresivo, Custom) puede tener visibles
distintos módulos de dashboard. El perfil **Custom** puede heredar
(compartir) los módulos de los otros perfiles mediante ``copiar_dashboard``.
"""

from typing import Any, Dict, List

from src.database import get_connection
from src.repositories import perfil_repo


def listar_modulos() -> List[Dict[str, Any]]:
    """Catálogo completo de módulos disponibles."""
    from src.repositories import BaseRepository
    return BaseRepository("dashboard_modulos").get_all()


def modulos_visibles(perfil_id: int) -> List[Dict[str, Any]]:
    """Módulos visibles para un perfil, en su orden configurado."""
    if not perfil_repo.get_by_id(perfil_id):
        raise ValueError(f"No existe el perfil con id {perfil_id}.")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT m.id, m.nombre_modulo, m.descripcion, c.orden
               FROM perfil_dashboard_config c
               JOIN dashboard_modulos m ON c.modulo_id = m.id
               WHERE c.perfil_id = ? AND c.visible = 1
               ORDER BY c.orden""",
            (perfil_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def asignar_modulos(perfil_id: int, modulo_ids: List[int]) -> None:
    """Define (reemplaza) los módulos visibles de un perfil con su orden."""
    if not perfil_repo.get_by_id(perfil_id):
        raise ValueError(f"No existe el perfil con id {perfil_id}.")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM perfil_dashboard_config WHERE perfil_id = ?", (perfil_id,))
        for orden, modulo_id in enumerate(modulo_ids):
            cur.execute(
                """INSERT INTO perfil_dashboard_config
                   (perfil_id, modulo_id, orden, visible) VALUES (?, ?, ?, 1)""",
                (perfil_id, int(modulo_id), orden),
            )
        conn.commit()
    finally:
        conn.close()


def copiar_dashboard(perfil_origen_id: int, perfil_destino_id: int) -> None:
    """Copia la configuración de dashboard de un perfil a otro.

    Es el mecanismo con el que el perfil **Custom** comparte dashboards
    de los perfiles Mínimo, Optimizado o Agresivo.
    """
    visibles = modulos_visibles(perfil_origen_id)
    asignar_modulos(perfil_destino_id, [m["id"] for m in visibles])
