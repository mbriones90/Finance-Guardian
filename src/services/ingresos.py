"""Servicio de registro de ingresos.

Tipos permitidos:
- ``sueldo_recurrente``: ingreso fijo que se repite (semanal/quincenal/mensual).
- ``ingreso_esporadico``: ingreso puntual.

El ingreso se suma al saldo de la cuenta indicada (si se indica).
"""

from datetime import date
from typing import Any, Dict, List, Optional

from src.repositories import cuenta_repo, ingreso_repo
from src.services.convertidor import convertir_a_pesos

TIPOS_VALIDOS = {"sueldo_recurrente", "ingreso_esporadico"}
FRECUENCIAS_VALIDAS = {"semanal", "quincenal", "mensual"}


def registrar_ingreso(
    categoria: str,
    monto: float,
    moneda: str = "MXN",
    tipo: str = "ingreso_esporadico",
    descripcion: str = "",
    fecha: Optional[str] = None,
    cuenta_id: Optional[int] = None,
    frecuencia: Optional[str] = None,
    dia_cobro: Optional[int] = None,
) -> Dict[str, Any]:
    """Registra un ingreso y, si hay cuenta, suma el monto a su saldo.

    ``dia_cobro`` es el primer día de pago del sueldo (1-31):
    - mensual: cobra ese día cada mes.
    - quincenal: cobra ese día y ese día + 15 (o el último del mes).
      Ej. día inicial 15 → cobra el 15 y el 30/último.
    - semanal: cobra cada 7 días el mismo día de la semana.
    """
    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto del ingreso debe ser mayor que cero.")
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo inválido: {tipo!r}. Usa {sorted(TIPOS_VALIDOS)}.")
    if tipo == "sueldo_recurrente" and frecuencia and frecuencia not in FRECUENCIAS_VALIDAS:
        raise ValueError(f"Frecuencia inválida: {frecuencia!r}.")
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValueError("La categoría es obligatoria.")
    if dia_cobro is not None and not 1 <= int(dia_cobro) <= 31:
        raise ValueError("El día de cobro debe estar entre 1 y 31.")

    monto_pesos = convertir_a_pesos(monto, moneda)
    fecha = fecha or date.today().isoformat()

    if cuenta_id is not None and not cuenta_repo.get_by_id(cuenta_id):
        raise ValueError(f"No existe la cuenta con id {cuenta_id}.")

    ingreso_id = ingreso_repo.create(
        {
            "tipo": tipo,
            "categoria": categoria,
            "descripcion": (descripcion or "").strip(),
            "monto": monto,
            "moneda": (moneda or "MXN").upper(),
            "fecha": fecha,
            "convertido_a_pesos": monto_pesos,
            "cuenta_id": cuenta_id,
            "dia_cobro": int(dia_cobro) if dia_cobro is not None else None,
            "frecuencia": frecuencia,
        }
    )

    balance_nuevo = None
    if cuenta_id is not None:
        cuenta = cuenta_repo.get_by_id(cuenta_id)
        balance_nuevo = round(float(cuenta["balance_actual"]) + monto_pesos, 2)
        cuenta_repo.update(cuenta_id, {"balance_actual": balance_nuevo})

    return {
        "id": ingreso_id,
        "tipo": tipo,
        "categoria": categoria,
        "monto": monto,
        "moneda": (moneda or "MXN").upper(),
        "convertido_a_pesos": monto_pesos,
        "fecha": fecha,
        "cuenta_id": cuenta_id,
        "frecuencia": frecuencia,
        "dia_cobro": int(dia_cobro) if dia_cobro is not None else None,
        "balance_nuevo": balance_nuevo,
    }


def dias_cobro_del_mes(ingreso: Dict[str, Any], year: int, month: int) -> List[int]:
    """Días del mes en que cae el cobro de un sueldo recurrente.

    - quincenal: día inicial y día inicial + 15 (ajustado al último día).
      Ej. inicial 15 → [15, 30] (o [15, 28/29] en febrero).
    - mensual: [día inicial].
    - semanal: todos los días del mes que caen en el mismo día de la semana
      que la fecha del ingreso.
    """
    import calendar

    if ingreso["tipo"] != "sueldo_recurrente":
        return []
    ultimo = calendar.monthrange(year, month)[1]
    dia = int(ingreso.get("dia_cobro") or date.fromisoformat(ingreso["fecha"]).day)
    dia = min(max(1, dia), ultimo)
    frecuencia = ingreso.get("frecuencia") or "mensual"

    if frecuencia == "quincenal":
        segunda = min(dia + 15, ultimo)
        return sorted({dia, segunda})
    if frecuencia == "semanal":
        weekday = date.fromisoformat(ingreso["fecha"]).weekday()
        return [d for d in range(1, ultimo + 1)
                if date(year, month, d).weekday() == weekday]
    return [dia]


def editar_ingreso(
    ingreso_id: int,
    categoria: Optional[str] = None,
    monto: Optional[float] = None,
    moneda: Optional[str] = None,
    descripcion: Optional[str] = None,
    fecha: Optional[str] = None,
    dia_cobro: Optional[int] = None,
    frecuencia: Optional[str] = None,
) -> Dict[str, Any]:
    """Edita un ingreso existente corrigiendo el balance de su cuenta.

    Revierte la suma del ingreso anterior y aplica la nueva. La cuenta
    destino no se puede cambiar (borra y vuelve a registrar).
    """
    ingreso = ingreso_repo.get_by_id(ingreso_id)
    if not ingreso:
        raise ValueError(f"No existe el ingreso con id {ingreso_id}.")

    nueva_categoria = (categoria if categoria is not None
                       else ingreso["categoria"] or "").strip()
    if not nueva_categoria:
        raise ValueError("La categoría es obligatoria.")
    nuevo_monto = float(monto) if monto is not None else float(ingreso["monto"])
    if nuevo_monto <= 0:
        raise ValueError("El monto del ingreso debe ser mayor que cero.")
    nueva_moneda = (moneda or ingreso["moneda"] or "MXN").upper()
    nueva_fecha = (fecha or ingreso["fecha"]).strip()
    nueva_descripcion = (descripcion if descripcion is not None
                         else ingreso["descripcion"] or "").strip()
    nueva_frecuencia = frecuencia if frecuencia is not None else ingreso.get("frecuencia")
    if (ingreso["tipo"] == "sueldo_recurrente" and nueva_frecuencia
            and nueva_frecuencia not in FRECUENCIAS_VALIDAS):
        raise ValueError(f"Frecuencia inválida: {nueva_frecuencia!r}.")
    nuevo_dia = dia_cobro if dia_cobro is not None else ingreso.get("dia_cobro")
    if nuevo_dia is not None and not 1 <= int(nuevo_dia) <= 31:
        raise ValueError("El día de cobro debe estar entre 1 y 31.")
    nuevos_pesos = convertir_a_pesos(nuevo_monto, nueva_moneda)

    balance_nuevo = None
    if ingreso.get("cuenta_id"):
        cuenta = cuenta_repo.get_by_id(ingreso["cuenta_id"])
        if not cuenta:
            raise ValueError("La cuenta del ingreso ya no existe.")
        delta = nuevos_pesos - float(ingreso["convertido_a_pesos"])
        balance_nuevo = round(float(cuenta["balance_actual"]) + delta, 2)
        cuenta_repo.update(cuenta["id"], {"balance_actual": balance_nuevo})

    ingreso_repo.update(ingreso_id, {
        "categoria": nueva_categoria,
        "monto": nuevo_monto,
        "moneda": nueva_moneda,
        "descripcion": nueva_descripcion,
        "fecha": nueva_fecha,
        "convertido_a_pesos": nuevos_pesos,
        "dia_cobro": int(nuevo_dia) if nuevo_dia is not None else None,
        "frecuencia": nueva_frecuencia,
    })

    return {
        "id": ingreso_id,
        "tipo": ingreso["tipo"],
        "categoria": nueva_categoria,
        "monto": nuevo_monto,
        "moneda": nueva_moneda,
        "convertido_a_pesos": nuevos_pesos,
        "fecha": nueva_fecha,
        "dia_cobro": int(nuevo_dia) if nuevo_dia is not None else None,
        "frecuencia": nueva_frecuencia,
        "balance_nuevo": balance_nuevo,
    }


def eliminar_ingreso(ingreso_id: int) -> bool:
    """Elimina un ingreso y revierte la suma que hizo en su cuenta."""
    ingreso = ingreso_repo.get_by_id(ingreso_id)
    if not ingreso:
        raise ValueError(f"No existe el ingreso con id {ingreso_id}.")
    if ingreso.get("cuenta_id"):
        cuenta = cuenta_repo.get_by_id(ingreso["cuenta_id"])
        if cuenta:
            cuenta_repo.update(cuenta["id"], {
                "balance_actual": round(
                    float(cuenta["balance_actual"])
                    - float(ingreso["convertido_a_pesos"]), 2)
            })
    return ingreso_repo.delete(ingreso_id)


def listar_ingresos(
    tipo: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista ingresos con filtros opcionales."""
    condiciones = []
    params: list = []
    if tipo:
        condiciones.append("tipo = ?")
        params.append(tipo)
    if desde:
        condiciones.append("fecha >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("fecha <= ?")
        params.append(hasta)

    query = "SELECT * FROM ingresos"
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY fecha DESC"
    return ingreso_repo.execute_query(query, tuple(params))
