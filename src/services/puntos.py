"""Puntos del jugador: moneda canjeable por armaduras y personalización."""

from src.repositories import puntos_repo


def obtener_puntos() -> int:
    return puntos_repo.get_total()


def ganar_puntos(cantidad: int) -> int:
    """Suma puntos (nunca negativos al sumar). Devuelve el nuevo saldo."""
    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValueError("La cantidad de puntos debe ser mayor que cero.")
    puntos_repo.add_puntos(cantidad)
    return puntos_repo.get_total()


def gastar_puntos(cantidad: int) -> int:
    """Descuenta puntos si hay saldo suficiente. Devuelve el nuevo saldo."""
    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValueError("La cantidad de puntos debe ser mayor que cero.")
    saldo = puntos_repo.get_total()
    if saldo < cantidad:
        raise ValueError(f"Te faltan {cantidad - saldo} puntos (tienes {saldo}).")
    puntos_repo.add_puntos(-cantidad)
    return puntos_repo.get_total()
