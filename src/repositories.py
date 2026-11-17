"""Capa de acceso a datos (CRUD por entidad).

Fase 2: Repositorios para todas las entidades del dominio.
"""

from typing import Optional, List, Dict, Any
from src.database import get_connection


class BaseRepository:
    """Clase base para repositorios."""

    def __init__(self, table_name: str):
        self.table_name = table_name

    def _conn(self):
        return get_connection()

    def create(self, data: Dict[str, Any]) -> int:
        """Inserta un registro y retorna su ID."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un registro por su ID."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?", (record_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all(self) -> List[Dict[str, Any]]:
        """Obtiene todos los registros de la tabla."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {self.table_name}")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def update(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Actualiza un registro por su ID."""
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [record_id]
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {self.table_name} SET {sets} WHERE id = ?", values
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def delete(self, record_id: int) -> bool:
        """Elimina un registro por su ID."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?", (record_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Ejecuta una consulta personalizada y retorna resultados."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class CuentaRepository(BaseRepository):
    def __init__(self):
        super().__init__("cuentas")

    def get_by_tipo(self, tipo: str) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE tipo = ?", (tipo,)
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class TarjetaRepository(BaseRepository):
    def __init__(self):
        super().__init__("tarjetas_credito")

    def get_by_cuenta(self, cuenta_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene las reglas de una tarjeta por el id de su cuenta."""
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM tarjetas_credito WHERE cuenta_id = ?", (cuenta_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_by_cuenta(self, cuenta_id: int, data: Dict[str, Any]) -> bool:
        """Actualiza las reglas de una tarjeta por el id de su cuenta."""
        sets = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [cuenta_id]
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE tarjetas_credito SET {sets} WHERE cuenta_id = ?", values
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_activas(self) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT t.*, c.nombre, c.moneda, c.balance_actual
                    FROM {self.table_name} t
                    JOIN cuentas c ON t.cuenta_id = c.id
                    WHERE t.activa = 1"""
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class GastoRepository(BaseRepository):
    def __init__(self):
        super().__init__("gastos")

    def get_by_cuenta(self, cuenta_id: int) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE cuenta_id = ? ORDER BY fecha DESC",
                (cuenta_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class IngresoRepository(BaseRepository):
    def __init__(self):
        super().__init__("ingresos")

    def get_recurrentes(self) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE tipo = 'sueldo_recurrente' ORDER BY fecha DESC"
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class SuscripcionRepository(BaseRepository):
    def __init__(self):
        super().__init__("suscripciones")

    def get_activas(self) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE activa = 1 ORDER BY dia_cobro"
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


class PerfilRepository(BaseRepository):
    def __init__(self):
        super().__init__("perfiles_pago")

    def get_activo(self) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM {self.table_name} WHERE activo = 1 LIMIT 1"
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class ConfiguracionRepository(BaseRepository):
    def __init__(self):
        super().__init__("configuracion")

    def get_tipo_cambio(self) -> float:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT tipo_cambio_dolar FROM configuracion WHERE id = 1")
            row = cur.fetchone()
            return row["tipo_cambio_dolar"] if row else 18.63
        finally:
            conn.close()

    def set_tipo_cambio(self, valor: float) -> None:
        from datetime import datetime
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE configuracion SET tipo_cambio_dolar = ?, fecha_actualizacion = ? WHERE id = 1",
                (valor, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()


class PersonajeRepository(BaseRepository):
    def __init__(self):
        super().__init__("personaje")

    def get_default(self) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM personaje WHERE id = 1")
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_armadura(self, armadura: str) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE personaje SET armadura_actual = ? WHERE id = 1", (armadura,)
            )
            conn.commit()
        finally:
            conn.close()


class PuntosRepository(BaseRepository):
    def __init__(self):
        super().__init__("puntos_usuario")

    def get_total(self) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT total_puntos FROM puntos_usuario WHERE id = 1")
            row = cur.fetchone()
            return row["total_puntos"] if row else 0
        finally:
            conn.close()

    def add_puntos(self, cantidad: int) -> None:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE puntos_usuario SET total_puntos = total_puntos + ? WHERE id = 1",
                (cantidad,),
            )
            conn.commit()
        finally:
            conn.close()


# Instancias globales de repositorios
cuenta_repo = CuentaRepository()
tarjeta_repo = TarjetaRepository()
gasto_repo = GastoRepository()
ingreso_repo = IngresoRepository()
suscripcion_repo = SuscripcionRepository()
perfil_repo = PerfilRepository()
configuracion_repo = ConfiguracionRepository()
personaje_repo = PersonajeRepository()
puntos_repo = PuntosRepository()
