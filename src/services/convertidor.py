"""Conversión de moneda con tipo de cambio fijo manual.

La moneda base es el peso mexicano (MXN). El dólar (USD) se convierte
usando el tipo de cambio global guardado en `configuracion`
(valor por defecto: 18.63).
"""

from src.repositories import configuracion_repo

MONEDAS_SOPORTADAS = {"MXN", "USD"}
ALIAS_PESOS = {"MXN", "PESOS", "PESO"}
ALIAS_DOLARES = {"USD", "DOLARES", "DOLAR", "DÓLAR", "DÓLARES"}


def get_tipo_cambio() -> float:
    """Devuelve el tipo de cambio USD→MXN vigente (fijo, manual)."""
    return float(configuracion_repo.get_tipo_cambio())


def set_tipo_cambio(valor: float) -> None:
    """Actualiza el tipo de cambio global. Debe ser mayor que cero."""
    valor = float(valor)
    if valor <= 0:
        raise ValueError("El tipo de cambio debe ser mayor que cero.")
    configuracion_repo.set_tipo_cambio(valor)


def _normalizar_moneda(moneda: str) -> str:
    m = (moneda or "").strip().upper()
    if m in ALIAS_PESOS:
        return "MXN"
    if m in ALIAS_DOLARES:
        return "USD"
    raise ValueError(f"Moneda no soportada: {moneda!r}. Usa MXN o USD.")


def convertir_a_pesos(monto: float, moneda: str = "MXN") -> float:
    """Convierte un monto a pesos usando el tipo de cambio fijo.

    - MXN: se devuelve igual (redondeado a 2 decimales).
    - USD: se multiplica por el tipo de cambio vigente.
    """
    monto = float(monto)
    m = _normalizar_moneda(moneda)
    if m == "MXN":
        return round(monto, 2)
    return round(monto * get_tipo_cambio(), 2)


def convertir_desde_pesos(monto_pesos: float, moneda_destino: str = "MXN") -> float:
    """Convierte un monto en pesos a la moneda destino."""
    monto_pesos = float(monto_pesos)
    m = _normalizar_moneda(moneda_destino)
    if m == "MXN":
        return round(monto_pesos, 2)
    return round(monto_pesos / get_tipo_cambio(), 2)
