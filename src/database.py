"""Conexión y gestión de la base de datos SQLite local.

Fase 2: Implementación completa del esquema de base de datos
para la app "Dimensiones del Guardián".
"""

import sqlite3
import os
from src.utils.paths import get_db_path

SCHEMA_SQL = """
-- Configuración global
CREATE TABLE IF NOT EXISTS configuracion (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tipo_cambio_dolar REAL NOT NULL DEFAULT 18.63,
    moneda_base TEXT NOT NULL DEFAULT 'MXN',
    fecha_actualizacion TEXT NOT NULL
);

-- Cuentas (bancarias o tarjetas)
CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('cuenta', 'tarjeta_credito')),
    moneda TEXT NOT NULL DEFAULT 'MXN',
    balance_actual REAL NOT NULL DEFAULT 0,
    fecha_creacion TEXT NOT NULL
);

-- Reglas específicas de tarjetas de crédito
CREATE TABLE IF NOT EXISTS tarjetas_credito (
    cuenta_id INTEGER PRIMARY KEY,
    dia_corte INTEGER NOT NULL CHECK (dia_corte BETWEEN 1 AND 31),
    dia_pago INTEGER NOT NULL CHECK (dia_pago BETWEEN 1 AND 31),
    dias_para_pagar INTEGER NOT NULL DEFAULT 30,
    tasa_interes_mensual REAL NOT NULL DEFAULT 0,
    limite_credito_maximo REAL DEFAULT NULL,
    minimo_uso_monto REAL DEFAULT 0,
    costo_admin_si_no_alcance REAL DEFAULT 0,
    activa INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Gastos
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_id INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT,
    monto REAL NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    fecha TEXT NOT NULL,
    convertido_a_pesos REAL NOT NULL,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Ingresos (sueldo recurrente y esporádicos)
CREATE TABLE IF NOT EXISTS ingresos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK (tipo IN ('sueldo_recurrente', 'ingreso_esporadico')),
    categoria TEXT NOT NULL,
    descripcion TEXT,
    monto REAL NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    fecha TEXT NOT NULL,
    convertido_a_pesos REAL NOT NULL,
    cuenta_id INTEGER,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Suscripciones / gastos fijos generales
CREATE TABLE IF NOT EXISTS suscripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    monto REAL NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'MXN',
    dia_cobro INTEGER NOT NULL CHECK (dia_cobro BETWEEN 1 AND 31),
    periodo TEXT NOT NULL DEFAULT 'mensual',
    cuenta_id INTEGER NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Presupuesto base (plantilla)
CREATE TABLE IF NOT EXISTS presupuestos_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT NOT NULL,
    monto_limite_base REAL NOT NULL
);

-- Presupuesto por semana
CREATE TABLE IF NOT EXISTS presupuestos_semanales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semana_inicio TEXT NOT NULL,
    semana_fin TEXT NOT NULL,
    categoria TEXT NOT NULL,
    monto_limite_semana REAL NOT NULL,
    monto_gastado REAL NOT NULL DEFAULT 0
);

-- Perfiles de pago
CREATE TABLE IF NOT EXISTS perfiles_pago (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo_perfil TEXT NOT NULL CHECK (tipo_perfil IN ('minimo', 'optimizado', 'agresivo', 'custom')),
    pago_minimo_porcentaje REAL DEFAULT 0,
    pago_minimo_monto_fijo REAL DEFAULT 0,
    flujo_minimo_efectivo REAL DEFAULT 0,
    priorizar_intereses_mayores INTEGER NOT NULL DEFAULT 0,
    activo INTEGER NOT NULL DEFAULT 0
);

-- Módulos de dashboard disponibles
CREATE TABLE IF NOT EXISTS dashboard_modulos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_modulo TEXT NOT NULL,
    descripcion TEXT
);

-- Configuración de módulos por perfil (compartimiento)
CREATE TABLE IF NOT EXISTS perfil_dashboard_config (
    perfil_id INTEGER NOT NULL,
    modulo_id INTEGER NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0,
    visible INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (perfil_id, modulo_id),
    FOREIGN KEY (perfil_id) REFERENCES perfiles_pago(id),
    FOREIGN KEY (modulo_id) REFERENCES dashboard_modulos(id)
);

-- Proyección de deuda
CREATE TABLE IF NOT EXISTS simulaciones_deuda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil_id INTEGER,
    cuenta_id INTEGER NOT NULL,
    mes_proyectado INTEGER NOT NULL CHECK (mes_proyectado BETWEEN 1 AND 12),
    saldo_inicial REAL NOT NULL,
    pago_aplicado REAL NOT NULL,
    interes_generado REAL NOT NULL DEFAULT 0,
    cargo_admin REAL NOT NULL DEFAULT 0,
    saldo_final REAL NOT NULL,
    fecha_estimada_liquidacion TEXT,
    FOREIGN KEY (perfil_id) REFERENCES perfiles_pago(id),
    FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
);

-- Simulación de compra cara
CREATE TABLE IF NOT EXISTS simulacion_compra_cara (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semana_id INTEGER,
    monto_compra REAL NOT NULL,
    cuenta_usada_id INTEGER NOT NULL,
    impacto_saldo_semana REAL NOT NULL,
    impacto_deuda REAL NOT NULL DEFAULT 0,
    fecha_simulacion TEXT NOT NULL,
    FOREIGN KEY (cuenta_usada_id) REFERENCES cuentas(id)
);

-- Personaje del usuario
CREATE TABLE IF NOT EXISTS personaje (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nombre TEXT NOT NULL DEFAULT 'Guardián',
    nivel INTEGER NOT NULL DEFAULT 1,
    dimensiones_completadas INTEGER NOT NULL DEFAULT 0,
    puntos_experiencia INTEGER NOT NULL DEFAULT 0,
    armadura_actual TEXT DEFAULT 'gris',
    fondo_actual TEXT DEFAULT 'default',
    tipo_cambio_favorito REAL DEFAULT 18.63
);

-- Inventario de armaduras
CREATE TABLE IF NOT EXISTS inventario_armadura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    calidad TEXT NOT NULL CHECK (calidad IN ('gris', 'verde', 'azul', 'morado', 'naranja')),
    desbloqueada INTEGER NOT NULL DEFAULT 0
);

-- Badges / pines
CREATE TABLE IF NOT EXISTS badges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    imagen TEXT,
    desbloqueado INTEGER NOT NULL DEFAULT 0
);

-- Badges del usuario
CREATE TABLE IF NOT EXISTS usuario_badges (
    personaje_id INTEGER NOT NULL,
    badge_id INTEGER NOT NULL,
    fecha_desbloqueo TEXT NOT NULL,
    PRIMARY KEY (personaje_id, badge_id),
    FOREIGN KEY (personaje_id) REFERENCES personaje(id),
    FOREIGN KEY (badge_id) REFERENCES badges(id)
);

-- Puntos del usuario
CREATE TABLE IF NOT EXISTS puntos_usuario (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    total_puntos INTEGER NOT NULL DEFAULT 0
);

-- Presupuesto general (mensual/quincenal/semanal; todos equivalentes)
CREATE TABLE IF NOT EXISTS presupuesto_general (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    periodo TEXT NOT NULL CHECK (periodo IN ('semanal', 'quincenal', 'mensual')),
    monto REAL NOT NULL,
    fecha_actualizacion TEXT NOT NULL
);

-- Semanas derrotadas: premio semanal por cumplir el presupuesto (masmorra)
CREATE TABLE IF NOT EXISTS premios_semana (
    semana_inicio TEXT PRIMARY KEY,
    puntos INTEGER NOT NULL,
    fecha_otorgado TEXT NOT NULL
);

-- Gastos planeados del presupuesto (compras que planeas hacer en la
-- semana o el mes; al cerrar el período confirmas si se hicieron o no)
CREATE TABLE IF NOT EXISTS gastos_planeados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_periodo TEXT NOT NULL CHECK (tipo_periodo IN ('semanal', 'mensual')),
    periodo_inicio TEXT NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT,
    monto REAL NOT NULL,
    estado TEXT NOT NULL DEFAULT 'planeado'
        CHECK (estado IN ('planeado', 'gastado', 'omitido')),
    fecha_creacion TEXT NOT NULL
);

-- Cierre del período: confirmación de qué se gastó, qué salió nuevo y
-- cuánto se ahorró (una sola vez por período)
CREATE TABLE IF NOT EXISTS cierres_presupuesto (
    tipo_periodo TEXT NOT NULL CHECK (tipo_periodo IN ('semanal', 'mensual')),
    periodo_inicio TEXT NOT NULL,
    limite REAL NOT NULL,
    gastado REAL NOT NULL,
    ahorro REAL NOT NULL,
    planeados_total REAL NOT NULL,
    nuevos_total REAL NOT NULL,
    resultado TEXT NOT NULL CHECK (resultado IN ('ahorro', 'justo', 'excedido')),
    fecha_cierre TEXT NOT NULL,
    PRIMARY KEY (tipo_periodo, periodo_inicio)
);
"""

# Columnas añadidas después de la versión inicial (migraciones suaves).
MIGRACIONES = [
    # Día de cobro del sueldo (quincenal: día N y N+15/último del mes)
    ("ingresos", "dia_cobro", "ALTER TABLE ingresos ADD COLUMN dia_cobro INTEGER"),
    # Frecuencia del sueldo (semanal/quincenal/mensual): antes no se guardaba
    ("ingresos", "frecuencia", "ALTER TABLE ingresos ADD COLUMN frecuencia TEXT"),
]


def get_connection() -> sqlite3.Connection:
    """Crea y retorna una conexión a la base de datos SQLite."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Inicializa la base de datos creando todas las tablas si no existen."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        _migrar(conn)
        conn.commit()
        _seed_default_data(conn)
    finally:
        conn.close()


def _migrar(conn: sqlite3.Connection) -> None:
    """Aplica migraciones suaves: añade columnas nuevas si no existen."""
    cur = conn.cursor()
    for tabla, columna, sql in MIGRACIONES:
        cur.execute(f"PRAGMA table_info({tabla})")
        if columna not in {fila[1] for fila in cur.fetchall()}:
            cur.execute(sql)


def _seed_default_data(conn: sqlite3.Connection) -> None:
    """Inserta datos por defecto si la base de datos está vacía."""
    cur = conn.cursor()

    # Configuración global (tipo de cambio default 18.63)
    cur.execute("SELECT COUNT(*) FROM configuracion")
    if cur.fetchone()[0] == 0:
        from datetime import datetime
        cur.execute(
            "INSERT INTO configuracion (id, tipo_cambio_dolar, moneda_base, fecha_actualizacion) VALUES (1, 18.63, 'MXN', ?)",
            (datetime.now().isoformat(),)
        )

    # Personaje default
    cur.execute("SELECT COUNT(*) FROM personaje")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO personaje (id, nombre, nivel, puntos_experiencia, armadura_actual, fondo_actual, tipo_cambio_favorito) VALUES (1, 'Guardián', 1, 0, 'gris', 'default', 18.63)"
        )

    # Puntos usuario
    cur.execute("SELECT COUNT(*) FROM puntos_usuario")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO puntos_usuario (id, total_puntos) VALUES (1, 0)")

    # Perfiles de pago por defecto (Fase 6)
    cur.execute("SELECT COUNT(*) FROM perfiles_pago")
    if cur.fetchone()[0] == 0:
        perfiles = [
            ("Mínimo", "minimo", 5.0, 200.0, 0.0, 0, 1),
            ("Optimizado", "optimizado", 5.0, 200.0, 5000.0, 0, 0),
            ("Agresivo", "agresivo", 5.0, 200.0, 5000.0, 1, 0),
            ("Custom", "custom", 5.0, 200.0, 5000.0, 0, 0),
        ]
        cur.executemany(
            """INSERT INTO perfiles_pago
               (nombre, tipo_perfil, pago_minimo_porcentaje, pago_minimo_monto_fijo,
                flujo_minimo_efectivo, priorizar_intereses_mayores, activo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            perfiles,
        )

    # Módulos de dashboard disponibles (Fase 6)
    cur.execute("SELECT COUNT(*) FROM dashboard_modulos")
    if cur.fetchone()[0] == 0:
        modulos = [
            ("resumen_financiero", "Saldo total, ingresos vs gastos del mes, deuda total"),
            ("riesgos_alertas", "Alertas de riesgo con semáforo (verde/amarillo/rojo)"),
            ("proyeccion_deuda", "Reducción de deuda a 1, 3, 6, 9 y 12 meses por perfil"),
            ("presupuesto_semanal", "Semáforo semanal y simulación de compras caras"),
            ("suscripciones", "Suscripciones activas y su impacto mensual"),
        ]
        cur.executemany(
            "INSERT INTO dashboard_modulos (nombre_modulo, descripcion) VALUES (?, ?)",
            modulos,
        )

    # Dashboard por defecto de cada perfil (sin esto, ningún perfil muestra
    # módulos y el dashboard queda huérfano). Se siembra por perfil: solo
    # los que no tengan ningún módulo configurado (el Custom que el usuario
    # armó en la D10 se respeta).
    modulos_map = {m[0]: m[1]
                   for m in cur.execute(
                       "SELECT nombre_modulo, id FROM dashboard_modulos")}
    perfiles_map = {p[0]: p[1]
                    for p in cur.execute(
                        "SELECT tipo_perfil, id FROM perfiles_pago")}
    defaults = {
        "minimo": ["resumen_financiero", "riesgos_alertas"],
        "optimizado": ["resumen_financiero", "riesgos_alertas",
                       "suscripciones", "presupuesto_semanal"],
        "agresivo": ["resumen_financiero", "riesgos_alertas",
                     "proyeccion_deuda"],
        "custom": ["resumen_financiero", "riesgos_alertas"],
    }
    for tipo, nombres in defaults.items():
        perfil_id = perfiles_map.get(tipo)
        if not perfil_id:
            continue
        cur.execute(
            "SELECT COUNT(*) FROM perfil_dashboard_config WHERE perfil_id = ?",
            (perfil_id,),
        )
        if cur.fetchone()[0] > 0:
            continue  # ya configurado (por el usuario o por la semilla)
        for orden, nombre in enumerate(nombres):
            if nombre in modulos_map:
                cur.execute(
                    """INSERT OR IGNORE INTO perfil_dashboard_config
                       (perfil_id, modulo_id, orden, visible)
                       VALUES (?, ?, ?, 1)""",
                    (perfil_id, modulos_map[nombre], orden),
                )

    # Armaduras del inventario (Fase 8)
    cur.execute("SELECT COUNT(*) FROM inventario_armadura")
    if cur.fetchone()[0] == 0:
        armaduras = [
            ("Armadura de cuero", "gris", 1),
            ("Armadura del cazador", "verde", 0),
            ("Armadura de acero", "azul", 0),
            ("Armadura arcana", "morado", 0),
            ("Armadura del dragón", "naranja", 0),
        ]
        cur.executemany(
            "INSERT INTO inventario_armadura (nombre, calidad, desbloqueada) VALUES (?, ?, ?)",
            armaduras,
        )

    # Badges disponibles (Fase 8)
    cur.execute("SELECT COUNT(*) FROM badges")
    if cur.fetchone()[0] == 0:
        badges = [
            ("Primera cuenta", "Creaste tu primera cuenta", "assets/badges/badge_primera_cuenta.png"),
            ("Primer ingreso", "Registraste tu primer ingreso", "assets/badges/badge_primer_ingreso.png"),
            ("Primer gasto", "Registraste tu primer gasto", "assets/badges/badge_primer_gasto.png"),
            ("Primera tarjeta", "Agregaste tu primera tarjeta", "assets/badges/badge_primera_tarjeta.png"),
            ("Maestro de reglas", "Configuraste las reglas de tus tarjetas", "assets/badges/badge_maestro_reglas.png"),
            ("Guardián Supremo", "Completaste la Dimensión Maestra", "assets/badges/badge_guardian_supremo.png"),
        ]
        cur.executemany(
            "INSERT INTO badges (nombre, descripcion, imagen, desbloqueado) VALUES (?, ?, ?, 0)",
            badges,
        )

    conn.commit()
