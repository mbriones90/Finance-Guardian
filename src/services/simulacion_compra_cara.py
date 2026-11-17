"""Simulación de compra cara: "¿puedo comprarme algo de varios miles de pesos?".

Evalúa el impacto de una compra grande en:
- el saldo disponible (si se paga con cuenta normal),
- la deuda y los meses extra de pago (si se paga con tarjeta de crédito),
y asigna un semáforo: verde / amarillo / rojo.

Cada simulación se guarda en ``simulacion_compra_cara`` para historial.
"""

from datetime import date
from typing import Any, Dict, Optional

from src.repositories import cuenta_repo, tarjeta_repo
from src.services.convertidor import convertir_a_pesos
from src.services.proyeccion_deuda import proyectar_desde_saldo


def simular_compra(
    monto: float,
    cuenta_usada_id: int,
    pago_mensual_estimado: Optional[float] = None,
    semana_id: Optional[int] = None,
    descripcion: str = "",
    guardar: bool = True,
) -> Dict[str, Any]:
    """Simula una compra grande sin modificar saldos reales.

    Args:
        monto: monto de la compra en su moneda.
        cuenta_usada_id: cuenta o tarjeta con la que se pagaría.
        pago_mensual_estimado: pago mensual que destinarías a la deuda
            (solo relevante para tarjetas; permite calcular meses extra).
        semana_id: presupuesto semanal asociado (opcional, Fase 7).
        descripcion: nota libre.
        guardar: si True registra la simulación en la base de datos.

    Returns:
        Dict con el antes/después, semáforo, impacto en deuda y mensajes.
    """
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto de la compra debe ser mayor que cero.")

    cuenta = cuenta_repo.get_by_id(cuenta_usada_id)
    if not cuenta:
        raise ValueError(f"No existe la cuenta con id {cuenta_usada_id}.")

    monto_pesos = convertir_a_pesos(monto, cuenta["moneda"])
    saldo_antes = round(float(cuenta["balance_actual"]), 2)

    resultado: Dict[str, Any] = {
        "monto": monto,
        "moneda": cuenta["moneda"],
        "monto_pesos": monto_pesos,
        "cuenta_id": cuenta_usada_id,
        "nombre_cuenta": cuenta["nombre"],
        "tipo_cuenta": cuenta["tipo"],
        "antes": saldo_antes,
        "despues": None,
        "impacto_deuda": 0.0,
        "semaforo": None,
        "mensajes": [],
        "meses_extra_para_liquidar": None,
        "interes_extra": None,
    }

    if cuenta["tipo"] == "cuenta":
        # Compra con dinero propio: resta del saldo disponible.
        saldo_despues = round(saldo_antes - monto_pesos, 2)
        resultado["despues"] = saldo_despues
        resultado["impacto_saldo_semana"] = saldo_despues

        if saldo_despues < 0:
            resultado["semaforo"] = "rojo"
            resultado["mensajes"].append(
                "No alcanza: el saldo quedaría negativo."
            )
        elif saldo_antes > 0 and saldo_despues < saldo_antes * 0.2:
            resultado["semaforo"] = "amarillo"
            resultado["mensajes"].append(
                "Alcanza, pero dejarías menos del 20% de tu saldo."
            )
        else:
            resultado["semaforo"] = "verde"
            resultado["mensajes"].append("Compra cubierta sin problema.")
    else:
        # Compra con tarjeta: sube la deuda.
        deuda_nueva = round(saldo_antes + monto_pesos, 2)
        resultado["despues"] = deuda_nueva
        resultado["impacto_deuda"] = monto_pesos
        resultado["impacto_saldo_semana"] = 0.0

        reglas = tarjeta_repo.get_by_cuenta(cuenta_usada_id)
        limite = float(reglas["limite_credito_maximo"]) if reglas and reglas.get("limite_credito_maximo") else None

        if limite:
            uso = deuda_nueva / limite * 100 if limite > 0 else 0
            if uso >= 100:
                resultado["semaforo"] = "rojo"
                resultado["mensajes"].append(
                    f"Excederías el límite de crédito (${limite:,.2f})."
                )
            elif uso >= 90:
                resultado["semaforo"] = "amarillo"
                resultado["mensajes"].append(
                    f"Usarías el {uso:.0f}% de tu límite de crédito."
                )
            else:
                resultado["semaforo"] = "verde"
        else:
            resultado["semaforo"] = "verde"
            resultado["mensajes"].append(
                "La tarjeta no tiene límite configurado; no se evaluó límite."
            )

        # Impacto en el plan de pagos (si se indica un pago mensual estimado)
        if pago_mensual_estimado and pago_mensual_estimado > 0 and reglas:
            tasa = float(reglas.get("tasa_interes_mensual") or 0)
            base = proyectar_desde_saldo(saldo_antes, tasa, pago_mensual_estimado)
            nueva = proyectar_desde_saldo(deuda_nueva, tasa, pago_mensual_estimado)
            resultado["meses_extra_para_liquidar"] = (
                (nueva["meses_para_liquidar"] or 0) - (base["meses_para_liquidar"] or 0)
            )
            resultado["interes_extra"] = round(
                nueva["interes_total"] - base["interes_total"], 2
            )
            if resultado["interes_extra"] and resultado["interes_extra"] > 0:
                resultado["mensajes"].append(
                    f"La compra agregaría ~${resultado['interes_extra']:,.2f} "
                    f"de intereses y {resultado['meses_extra_para_liquidar']} "
                    "mes(es) extra de pago."
                )

    if guardar:
        resultado["id"] = _guardar(resultado, semana_id, descripcion)

    return resultado


def _guardar(res: Dict[str, Any], semana_id: Optional[int], descripcion: str) -> int:
    from src.database import get_connection

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO simulacion_compra_cara
               (semana_id, monto_compra, cuenta_usada_id, impacto_saldo_semana,
                impacto_deuda, fecha_simulacion)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                semana_id,
                res["monto"],
                res["cuenta_id"],
                res["impacto_saldo_semana"],
                res["impacto_deuda"],
                date.today().isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def listar_simulaciones(limite: int = 20) -> list:
    from src.repositories import BaseRepository

    repo = BaseRepository("simulacion_compra_cara")
    return repo.execute_query(
        "SELECT * FROM simulacion_compra_cara ORDER BY fecha_simulacion DESC, id DESC LIMIT ?",
        (int(limite),),
    )
