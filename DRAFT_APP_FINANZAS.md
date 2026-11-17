# Draft: App de Finanzas Personales — "Dimensiones del Guardián"

> **Estado:** Borrador de trabajo. Se irá editando conforme avancemos.  
> **Temática:** Medieval / RPG / MMO (estilo Zelda, Dark Souls, Duolingo).  
> **Metáfora:** No son pisos, son **Dimensiones o Portales**. Se avanza de Punto A a Punto B como en *Left 4 Dead*: el tiempo avanza, el terreno y el clima cambian en cada trayecto.

---

## 1. Filosofía de experiencia (UX)

| Principio | Qué significa en la app |
|-----------|-------------------------|
| **Simplicidad primero** | Al abrir la app, el usuario ve solo lo esencial: su personaje default y la primera dimensión. Sin menús complejos. |
| **Progresión simple → complejo** | Cada dimensión añade una sola capa de complejidad financiera. Nunca se muestra lo que aún no se necesita. |
| **Condicionamiento positivo (Zelda)** | Al completar una dimensión, aparece un cofre con sonido, desbloquea funciones y otorga puntos. Nunca se castiga por errores. |
| **Progresión lineal sin bloqueos** | Se puede editar en cualquier momento sin que afecte ni ponga obstáculos. No hay "no se puede bajar". |
| **Personaje RPG** | El usuario tiene un personaje (default al inicio) que sube de nivel, usa armaduras, badges/pines y fondos. |

---

## 2. Progresión por niveles del personaje

La progresión **no son pisos**: son los **niveles del personaje**. Cada dimensión corresponde a un nivel del Guardián:

- El personaje inicia en **Nivel 1** → Desbloquea la **Dimensión 1: El Despertar**.
- Al completar la misión de la Dimensión N, el personaje **sube a Nivel N+1**, y ese nuevo nivel **abre el portal** a la Dimensión N+1.
- El nivel del personaje es la medida visible de tu progreso financiero: nivel alto = guardián experimentado con sus finanzas dominadas.
- En cada dimensión hay un **cofre** (premio) al completar la misión, y la ruta del Punto A al Punto B muestra terreno y clima que cambian.

| Dimensión | Nombre | Misión | Input (qué hace el usuario) | Complejidad | Cofre / Premio |
|-----------|--------|--------|-----------------------------|-------------|----------------|
| 1 | **El Despertar** | Conocer tu dinero actual | Crear primera cuenta, saldo inicial, tipo de cambio fijo (default 18.63) | Baja | Cofre de madera: "Primera cuenta" |
| 2 | **El Camino del Oro** | Registrar ingresos | Sueldo recurrente (semanal/quincenal/mensual) e ingresos esporádicos | Baja | Cofre de hierro: "Primer ingreso" |
| 3 | **Bosque de Gastos** | Ver a dónde sale el dinero | Gastos sencillos (monto, categoría, cuenta, fecha) | Baja | Cofre de bronce: "Control de egresos" |
| 4 | **Puerta del Crédito** | Primera tarjeta de crédito | Nombre, día de corte, día de pago, días para pagar (20/30) | Media | Cofre de plata: "Primera tarjeta" |
| 5 | **Cámara de Reglas** | Configurar reglas de tarjetas | Tasa de interés, límite de crédito, mínimo de uso (Invex/Sams: $2,000), cargo admin ($300) | Media-alta | Cofre de oro: "Reglas claras" |
| 6 | **Llanura del Presupuesto** | Planificar la semana | Presupuesto base por categorías (semana inicia lunes, navegar semanas atrás/adelante) | Media | Cofre de esmeralda: "Presupuestador" |
| 7 | **Mercado de Suscripciones** | Gastos fijos recurrentes | Luz, internet, Netflix, etc. (generales, no ligadas a perfiles) | Baja-media | Cofre de zafiro: "Gastos fijos" |
| 8 | **Prueba del Dragón** | Simulación de compra cara | Ingresar monto de compra grande (varios miles), elegir cuenta/tarjeta, ver impacto en saldo y deuda | Media-alta | Cofre de rubí: "Simulador" |
| 9 | **Salón de Estrategas** | Perfiles de pago | Configurar 3 perfiles: Mínimo, Optimizado (líquido), Agresivo. Elegir uno activo | Alta | Cofre de diamante: "Estratega" |
| 10 | **Forja del Guardián** | Perfil Custom + dashboard | Elegir módulos de dashboard de los otros perfiles, ajustar tipo de cambio si varió | Alta | Cofre legendario: "Arquitecto" |
| 11 | **Torre de Comparación** | Duelo de personajes | Comparar tu personaje con otros (estilo Duolingo), ver rankings (opcional futuro) | Alta | Cofre de campeón: "Guardián" |
| 12 | **Santuario de Datos** | Exportar y configurar | Exportar a CSV, temas visuales por versión, ajustes generales | Media | Cofre eterno: "Maestro de datos" |
| 13 | **Dimensión Maestra** | Modo libre | Todo desbloqueado, personaje completo, armadura, badges, fondos | Máxima | **Cofre del Guardián Supremo** |

---

## 3. Personaje y progresión RPG

### Personaje default
- No se pide al iniciar. Se asigna un personaje default (estilo Zelda/Dark Souls) en **Nivel 1**.
- El **nivel del personaje es la progresión**: cada dimensión completada sube un nivel y abre el portal a la siguiente.
- Se puede cambiar en **Configuración del Personaje** desde cualquier dimensión.
- Puede "pelear" o compararse con personajes de otros usuarios (estilo Duolingo) — funcionalidad futura/opcional.

### Atributos del personaje
- **Nivel:** sube al completar dimensiones y ganar puntos.
- **Puntos de experiencia (XP):** se ganan con cofres.
- **Moneda del juego:** puntos obtenidos en cofres.

### Armadura y calidades
El usuario puede cambiar la armadura del personaje con calidades de colores:
- **Gris** (común)
- **Verde** (poco común)
- **Azul** (raro)
- **Morado** (épico)
- **Naranja** (legendario)

También se pueden cambiar:
- **Badges / pines:** se desbloquean por logros.
- **Fondos:** visuales de fondo de la app.
- **Temas visuales:** generales por versión de la app (no por personaje).

---

## 4. Sistema de cofres (estilo Zelda)

Cada cofre al completar una dimensión contiene:
- **Sonido de cofre abriéndose** (estilo Zelda).
- **Mensaje de celebración.**
- **Puntos** (acumulables, estilo Duolingo/RPG).
- **Desbloqueo de función nueva** en la app.
- **Posible badge/pin o pieza de armadura.**

Los puntos se pueden usar para:
- Comprar/desbloquear armaduras de distintas calidades.
- Cambiar fondos.
- Personalizar el personaje.

---

## 5. Tipo de cambio (fijo 18.63)

- Valor **default fijo: 18.63** pesos por dólar.
- Se configura en **Configuración del Personaje**, accesible desde cualquier dimensión.
- Se puede actualizar cuando el usuario quere si el cambio varía mucho.
- No se pide obligatoriamente al iniciar; viene por defecto.

---

## 6. Reglas financieras (sin obstáculos de edición)

- Se puede editar cualquier cuenta, gasto, ingreso, tarjeta o presupuesto en cualquier momento.
- **No hay bloqueos ni penalizaciones** por editar. El progreso no se pierde.
- Las reglas de negocio siguen activas (cargos por administración, intereses, mínimo de uso, etc.) pero el usuario es libre de ajustar sus datos.

---

## 7. Requisitos funcionales mapeados a dimensiones

| Requisito | Dimensión |
|-----------|-----------|
| Tipo de cambio fijo 18.63, editable en configuración del personaje | D1 (default), D10 (ajuste) |
| Cuentas y balances | D1 |
| Ingresos fijos y esporádicos | D2 |
| Gastos simples | D3 |
| Tarjetas con corte/pago (20/30 días) | D4 |
| Tasa de interés, límite de crédito | D5 |
| Mínimo de uso y cargo admin (Invex/Sams) | D5 |
| Presupuesto semanal (lunes, navegar semanas) | D6 |
| Suscripciones generales | D7 |
| Simulación compra cara | D8 |
| 3 perfiles de pago + Custom | D9 y D10 |
| Dashboard compartible / módulos elegibles | D10 |
| Proyección deuda 1-12 meses | D9 y D10 |
| Exportar CSV | D12 |
| Personaje, armadura, badges, puntos | D1-D13 (transversal) |

---

## 7.1 Assets generados (Fase 3)

Los assets visuales ya están generados y organizados en `assets/`:

- `assets/personajes/` — guerrero base + 5 armaduras (gris, verde, azul, morado, naranja)
- `assets/cofres/` — 12 cofres (madera → supremo)
- `assets/fondos/` — 13 dimensiones + 1 variante de clima (D1 día vs. tormenta)
- `assets/badges/` — 6 badges de logro
- `assets/iconos/` — 6 iconos de UI

Ver detalle completo, tamaños y mapeo en **`ASSETS_MANIFEST.md`**.
Vista previa: `assets/preview_contactsheet.png` y `assets/preview_fondos.png`.

> **Pendiente:** sonidos de cofre (OpenArt no genera audio).

---

## 8. Arquitectura técnica (resumen)

- **Lenguaje:** Python 3.11+
- **Gestor de dependencias:** UV (`uv.lock`, `pyproject.toml`)
- **Interfaz:** Flet (Windows + Android APK)
- **Base de datos:** SQLite local
- **Ejecución Windows:** `run.bat` → `uv run python src/main.py`
- **Ejecución Android:** `flet build apk` desde Windows

---

## 9. Flujo de primer uso (onboarding RPG)

1. Abrir app → aparece tu **personaje default** y la **Dimensión 1: El Despertar**.
2. Una ruta visual muestra el camino del Punto A al Punto B (terreno y clima cambian).
3. Completas la misión de la dimensión → aparece cofre con sonido Zelda → ganas puntos y desbloqueas la siguiente dimensión.
4. Puedes ir a Configuración del Personaje en cualquier momento para cambiar tipo de cambio, armadura, badges o fondo.
5. Al llegar a la Dimensión 13, todo está desbloqueado.

---

## 10. Preguntas abiertas (para cerrar este draft)

1. ¿El terreno y clima de cada dimensión deben ser solo visuales (fondos) o también afectan algo en la lógica financiera?
2. ¿El sistema de "pelear/comparar personajes" (estilo Duolingo) es para ahora o se deja para una versión futura?
3. ¿Los puntos se pueden gastar en armadura/fondos inmediatamente o solo se acumulan para mostrar estatus?
4. ¿Quieres que haya una tienda interna con los puntos, o solo se desbloquean por completar dimensiones?

---

¿Listo este draft? Si lo ajustamos, el siguiente paso es crear el **PLAN_DE_TRABAJO_AGENTES.md** para distribuir el desarrollo entre los 4 agentes.
