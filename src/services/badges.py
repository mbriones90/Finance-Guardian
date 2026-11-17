"""Badges y pines del personaje (logros desbloqueables)."""

from datetime import date
from typing import Any, Dict, List, Optional

from src.database import get_connection
from src.repositories import BaseRepository

_badges = BaseRepository("badges")


def listar_badges() -> List[Dict[str, Any]]:
    """Todos los badges con su estado de desbloqueo para el jugador."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT b.id, b.nombre, b.descripcion, b.imagen,
                      (ub.badge_id IS NOT NULL) AS desbloqueado,
                      ub.fecha_desbloqueo
               FROM badges b
               LEFT JOIN usuario_badges ub
                 ON ub.badge_id = b.id AND ub.personaje_id = 1
               ORDER BY b.id"""
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _buscar_badge(badge_id: Optional[int] = None, nombre: Optional[str] = None) -> Dict[str, Any]:
    if badge_id is not None:
        fila = _badges.get_by_id(badge_id)
    elif nombre:
        filas = _badges.execute_query(
            "SELECT * FROM badges WHERE nombre = ?", (nombre,)
        )
        fila = filas[0] if filas else None
    else:
        raise ValueError("Indica badge_id o nombre.")
    if not fila:
        raise ValueError("Badge no encontrado.")
    return fila


def badge_otorgado(badge_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM usuario_badges WHERE personaje_id = 1 AND badge_id = ?",
            (badge_id,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def otorgar_badge(badge_id: Optional[int] = None, nombre: Optional[str] = None) -> Dict[str, Any]:
    """Otorga un badge al jugador (idempotente: no se duplica)."""
    badge = _buscar_badge(badge_id, nombre)
    if badge_otorgado(badge["id"]):
        return {"badge": badge, "nuevo": False}

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO usuario_badges (personaje_id, badge_id, fecha_desbloqueo)
               VALUES (1, ?, ?)""",
            (badge["id"], date.today().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"badge": badge, "nuevo": True}


def badges_del_usuario() -> List[Dict[str, Any]]:
    """Solo los badges desbloqueados por el jugador."""
    return [b for b in listar_badges() if b["desbloqueado"]]
