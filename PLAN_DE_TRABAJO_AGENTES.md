# Plan de Trabajo — App "Dimensiones del Guardián"

> **Propósito:** Distribuir el desarrollo entre 4 agentes de forma secuencial.  
> **Cada fase tiene:** meta de inicio, meta de fin (Definition of Done), agente responsable, trabajo a realizar y dependencias.  
> **Las fases son secuenciales:** no se inicia la siguiente hasta que la anterior tenga su "Meta de fin" cumplida.  
> **El número de fases es abierto:** se pueden añadir fases según surjan necesidades, pero siempre manteniendo este formato.

---

## Tabla de agentes

| Rol | Agente | Responsabilidad principal |
|-----|--------|---------------------------|
| Arquitecto | **nemotron-3.5-super** (tú) | Arquitectura, diseño de datos, flujo de dimensiones, reglas de negocio, revisión de avances |
| Artista | **LLM de generación de imágenes** | Personaje default, armaduras (calidades gris/verde/azul/morado/naranja), cofres, fondos, dimensiones, badges/pines, iconografía |
| Lógica compleja | **Claude Code (Opus 5.5)** | Algoritmos financieros difíciles: proyección de deuda, simulación de compra cara, perfiles de pago, cálculo de intereses, cargos por administración, detección de riesgos |
| Programador Python | **Laguna-s-2.1** | Implementación de módulos Python, Flet UI, SQLite, integración de assets, build `.bat` y APK, export CSV |

---

## Cómo leer este plan

- **Meta de inicio:** qué debe estar listo antes de empezar la fase.
- **Meta de fin:** qué se debe haber logrado para dar la fase por completa.
- **Estado:** Pendiente → En curso → Completado → Verificado por Arquitecto.
- **Entregable:** archivo, función o módulo que resulta de la fase.

---

## Fase 1 — Setup del repositorio y arquitectura base

| Campo | Contenido |
|-------|-----------|
| **Agente** | nemotron-3.5-super |
| **Meta de inicio** | Carpeta del proyecto vacía. |
| **Meta de fin** | Repositorio inicializado con estructura de carpetas, `pyproject.toml`, `.python-version`, `uv.lock` base, y `run.bat` funcional que lance `uv run python src/main.py`. |
| **Trabajo** | Crear estructura de carpetas (`src/`, `data/`, `assets/`, etc.), definir dependencias mínimas (Flet, UV), escribir `run.bat`, probar que la app arranca en blanco en Windows. |
| **Dependencias** | Ninguna. |
| **Estado** | Pendiente |

---

## Fase 2 — Modelo de datos y base de datos SQLite

| Campo | Contenido |
|-------|-----------|
| **Agente** | nemotron-3.5-super (diseño) + Laguna-s-2.1 (implementación) |
| **Meta de inicio** | Fase 1 completada. |
| **Meta de fin** | Base de datos SQLite funcionando con tablas: `configuracion`, `cuentas`, `tarjetas_credito`, `gastos`, `ingresos`, `suscripciones`, `presupuestos_semanales`, `perfiles_pago`, `dashboard_modulos`, `perfil_dashboard_config`, `simulaciones_deuda`, `simulacion_compra_cara`, `personaje`, `inventario_armadura`, `badges`, `puntos_usuario`. Script de creación y migración simple. |
| **Trabajo** | Definir esquema SQL completo, crear `database.py` y `repositories.py` con CRUD básico. Probar inserción y lectura en SQLite. |
| **Dependencias** | Fase 1. |
| **Estado** | Pendiente |

---

## Fase 3 — Arte y assets RPG (personaje, armaduras, cofres, dimensiones)

| Campo | Contenido |
|-------|-----------|
| **Agente** | LLM de generación de imágenes |
| **Meta de inicio** | Fase 2 completada (se sabe qué assets se necesitan). |
| **Meta de fin** | Assets listos en `assets/`: personaje default (estilo Zelda/Dark Souls), armaduras en 5 calidades (gris, verde, azul, morado, naranja), cofres (madera, hierro, bronce, plata, oro, esmeralda, zafiro, rubí, diamante, legendario, eterno, Guardián Supremo), fondos de dimensión (12 + maestra), badges/pines, iconos de UI, sonidos de cofre (referencia de archivo de audio). |
| **Trabajo** | Generar prompts y obtener imágenes/sonidos. Entregar en formato usable (PNG con fondo transparente, OGG/MP3 para sonido). Documentar qué asset corresponde a cada dimensión y calidad de armadura. |
| **Dependencias** | Fase 2 (para conocer lista de assets). |
| **Estado** | ✅ COMPLETADO (2026-11-11) — 44 assets con OpenArt MCP / Seedream 5.5. Ver `ASSETS_MANIFEST.md`. Sonidos pendientes (OpenArt no genera audio). |

---

## Fase 4 — Lógica financiera base (cálculos simples)

| Campo | Contenido |
|-------|-----------|
| **Agente** | Claude Code (Opus 5.5) |
| **Meta de inicio** | Fase 2 completada (modelo de datos listo). |
| **Meta de fin** | Servicios de cálculo funcionando: conversión de moneda con tipo de cambio fijo (default 18.63), cálculo de saldo de cuenta, registro de gasto simple, registro de ingreso, cálculo de días hasta corte/pago de tarjeta. |
| **Trabajo** | Escribir `services/convertidor.py`, `services/cuentas.py`, `services/gastos.py`, `services/ingresos.py`, `services/tarjetas_base.py`. Incluir pruebas unitarias básicas. |
| **Dependencias** | Fase 2. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — `src/services/` con 5 módulos. 27/27 pruebas pasando (`tests/test_fase4.py`). |

---

## Fase 5 — Lógica financiera avanzada (tasas, límites, cargos, proyección)

| Campo | Contenido |
|-------|-----------|
| **Agente** | Claude Code (Opus 5.5) |
| **Meta de inicio** | Fase 4 completada. |
| **Meta de fin** | Motor de reglas avanzadas: tasa de interés mensual configurable, límite de crédito máximo, mínimo de uso mensual (Invex/Sams $2,000), cargo por administración ($300), generación automática de cargo si no se alcanza mínimo, proyección de deuda a 1, 3, 6, 9, 12 meses por perfil, simulación de compra cara con impacto en saldo y deuda. |
| **Trabajo** | `services/tarjetas_avanzadas.py`, `services/proyeccion_deuda.py`, `services/cargos_admin.py`, `services/simulacion_compra_cara.py`, `services/deteccion_riesgos.py`. Probar con datos simulados. |
| **Dependencias** | Fase 4. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — `cargos_admin.py` (Invex/Sams idempotente), `proyeccion_deuda.py` (+`proyectar_desde_saldo` para simulaciones), `simulacion_compra_cara.py` (semáforo + meses/interés extra), `deteccion_riesgos.py`. 33/33 pruebas (`tests/test_fase5.py`). |

---

## Fase 6 — Perfiles de pago y dashboard compartible

| Campo | Contenido |
|-------|-----------|
| **Agente** | Claude Code (Opus 5.5) + nemotron-3.5-super (diseño de reglas) |
| **Meta de inicio** | Fase 5 completada. |
| **Meta de fin** | Sistema de perfiles: Mínimo, Optimizado (líquido), Agresivo, Custom. Perfil Custom puede elegir módulos de dashboard de los otros 3. Cálculo de pago mensual por perfil, fecha estimada de liquidación, comparación lado a lado. |
| **Trabajo** | `services/perfiles_pago.py`, `services/dashboard_modulos.py`, lógica de asignación de módulos al perfil Custom. |
| **Dependencias** | Fase 5. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — 4 perfiles sembrados (Mínimo/Optimizado/Agresivo/Custom), fórmulas de pago por perfil, comparación lado a lado con fecha de liquidación (horizonte hasta 120 meses, guarda primeros 12), distribución de presupuesto priorizando tasas, módulos de dashboard compartibles vía `copiar_dashboard`. 25/25 pruebas (`tests/test_fase6.py`). |

---

## Fase 7 — Presupuesto semanal y suscripciones

| Campo | Contenido |
|-------|-----------|
| **Agente** | Claude Code (Opus 5.5) |
| **Meta de inicio** | Fase 4 completada. |
| **Meta de fin** | Presupuesto base por categorías, semanas que inician lunes, navegación semanas atrás/adelante, edición por semana actual, suscripciones generales (luz, internet, Netflix) con día de cobro y cuenta asociada, cálculo de gasto acumulado semanal. |
| **Trabajo** | `services/presupuesto_semanal.py`, `services/suscripciones.py`, integración con repositorios. |
| **Dependencias** | Fase 4. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — semana lun-dom con navegación atrás/adelante, presupuesto base repetible editable por semana, semáforo 70/100 %, `puedo_gastar` y `simular_compra_semanal` (impacto semanal + deuda). Suscripciones generales CRUD + cobros del mes + impacto semanal. 34/34 pruebas (`tests/test_fase7.py`). Regresión 4-6 OK. |

---

## Fase 8 — Sistema de personaje, puntos, armadura y badges

| Campo | Contenido |
|-------|-----------|
| **Agente** | Claude Code (Opus 5.5) + nemotron-3.5-super (diseño de progresión) |
| **Meta de inicio** | Fase 3 (assets) y Fase 2 (modelo de datos con tablas de personaje/inventario) completadas. |
| **Meta de fin** | Personaje default asignado al iniciar. Sistema de puntos (XP) ganados por cofre. Inventario de armadura con calidades (gris, verde, azul, morado, naranja). Badges/pines desbloqueables. Cambio de fondo. Configuración del personaje accesible desde cualquier dimensión para editar tipo de cambio (default 18.63) y apariencia sin obstáculos. |
| **Trabajo** | `services/personaje.py`, `services/inventario.py`, `services/puntos.py`, `services/badges.py`, lógica de asignación de cofre → puntos → desbloqueo. |
| **Dependencias** | Fase 2, Fase 3. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — progresión por **niveles del personaje** (ajuste de diseño): completar Dimensión N → Nivel N+1, sin adelantarse ni repetir. Cofres 1-13 con puntos (100×d) y XP (50×d), 6 badges mapeados, inventario de 5 armaduras con costos (0/200/500/1200/3000), 15 fondos, configuración del personaje (nombre/armadura/fondo/tipo de cambio) desde cualquier dimensión. 35/35 pruebas (`tests/test_fase8.py`). Regresión 4-7 OK. |

---

## Fase 9 — UI de dimensiones y portales (Punto A → Punto B)

| Campo | Contenido |
|-------|-----------|
| **Agente** | Laguna-s-2.1 |
| **Meta de inicio** | Fase 4, Fase 5, Fase 6, Fase 7, Fase 8 completadas (lógica lista). Fase 3 (assets) entregada. |
| **Meta de fin** | Interfaz en Flet que muestra el viaje del Punto A al Punto B por dimensión. Terreno y clima cambian visualmente (fondos). Navegación lineal entre dimensiones. Pantallas de cada dimensión con su misión, input y progreso. |
| **Trabajo** | `ui/views/dimensiones.py`, `ui/components/camino.py`, `ui/components/portal.py`, integración con Flet, temas visuales por versión. |
| **Dependencias** | Fase 3 (assets), Fase 4-8 (lógica). |
| **Estado** | ✅ COMPLETADO (2026-11-11) — shell con NavigationRail (Dimensiones/Resumen/Personaje). Mapa A→B con fondo por dimensión, chips de estado (completada/actual/bloqueada), 13 vistas de misión con formularios reales conectados a servicios, requisitos por dimensión, diálogo de cofre, vista Resumen (estado financiero + riesgos + ciclos de tarjetas), vista Personaje (config, inventario, fondos, badges). Servicio `export_csv.py` (9 tablas). 13/13 pruebas (`tests/test_fase9_ui.py`). Regresión 4-8 OK. |

---

## Fase 10 — Cofres, sonido y desbloqueo de funciones

| Campo | Contenido |
|-------|-----------|
| **Agente** | Laguna-s-2.1 + Claude Code (Opus 5.5) |
| **Meta de inicio** | Fase 9 completada. Fase 3 (sonido de cofre) lista. |
| **Meta de fin** | Al completar una dimensión se muestra cofre animado con sonido (estilo Zelda), entrega puntos, desbloquea la siguiente dimensión/función y muestra mensaje de celebración. Los puntos se reflejan en el personaje. |
| **Trabajo** | `ui/components/cofre.py`, `services/desbloqueo.py`, manejo de audio, estado de dimensiones desbloqueadas. |
| **Dependencias** | Fase 9, Fase 3, Fase 8. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — sonidos sintetizados sin ffmpeg (`scripts/generar_sonidos.py`: cofre/nivel/error WAV), reproductor multi-plataforma con fallback (`src/ui/sonido.py`: winsound → flet.Audio → no-op), cofre animado con entrada rebote (animate_scale + run_task) y doble sonido (cofre → fanfarria), error con buzz, desbloqueo de siguiente dimensión verificado. 15/15 pruebas (`tests/test_fase10.py`). Regresión completa OK. |

---

## Fase 11 — Integración completa y pruebas de flujo

| Campo | Contenido |
|-------|-----------|
| **Agente** | Laguna-s-2.1 (integración) + nemotron-3.5-super (verificación) |
| **Meta de inicio** | Fases 1 a 10 completadas. |
| **Meta de fin** | App funcional de principio a fin: usuario inicia, ve personaje default, avanza por dimensiones, edita datos en cualquier momento sin obstáculos, gana puntos, cambia armadura, usa presupuestos, simula compras, ve proyección de deuda, exporta CSV. Sin errores críticos. |
| **Trabajo** | Conectar todos los servicios con la UI, pruebas de flujo end-to-end, corrección de bugs, ajuste de navegación. |
| **Dependencias** | Fase 10. |
| **Estado** | ✅ COMPLETADO (2026-11-11) — partida completa simulada de la D1 a la D13 con edición libre de datos en cualquier momento (sin afectar progresión), sin errores críticos. 33/33 pruebas (`tests/test_fase11_juego.py`). Suite completa: 215 pruebas en verde. README actualizado. |

---

## Fase 12 — Build, empaquetado y despliegue

| Campo | Contenido |
|-------|-----------|
| **Agente** | Laguna-s-2.1 |
| **Meta de inicio** | Fase 11 completada y verificada por el Arquitecto. |
| **Meta de fin** | `run.bat` funcional en Windows que instale dependencias con UV y ejecute la app. APK generado con `flet build apk` para Android. Documentación de cómo ejecutar en PC y cómo instalar en Android. |
| **Trabajo** | Configurar `flet build apk`, probar en emulador o dispositivo Android, empaquetar assets, generar instrucciones de instalación. |
| **Dependencias** | Fase 11. |
| **Estado** | Pendiente |

---

## Fase N — Mantenimiento, expansiones y nuevas dimensiones

| Campo | Contenido |
|-------|-----------|
| **Agente** | Según corresponda (Arquitecto para diseño, Claude para lógica, Laguna para código, LLM imágenes para nuevos assets) |
| **Meta de inicio** | Fase 12 completada. |
| **Meta de fin** | Nuevas dimensiones, nuevas calidades de armadura, nuevas funciones, corrección de bugs reportados, actualización de tipos de cambio, mejoras de UX. |
| **Trabajo** | Iterar sobre el plan añadiendo nuevas fases numeradas (Fase 13, 14, ...). |
| **Dependencias** | Fase 12. |
| **Estado** | Pendiente |

---

## Reglas de ejecución

1. **Secuencialidad:** El agente de la fase siguiente no inicia hasta que la fase anterior tenga "Estado: Completado" y haya sido verificada por nemotron-3.5-super.
2. **Registro de avances:** Al terminar cada fase, el agente responsable debe actualizar este documento marcando la fase como "Completado" y anotando la fecha.
3. **Bloqueos:** Si una fase no puede completarse por dependencia externa, se anota en "Estado" con la razón y se notifica al Arquitecto.
4. **Cambios de alcance:** Cualquier nueva fase se añade al final con el mismo formato.

---

## Estado actual del proyecto

| Fase | Nombre | Agente | Estado | Fecha inicio | Fecha fin |
|------|--------|--------|--------|--------------|-----------|
| 1 | Setup del repositorio y arquitectura base | nemotron-3.5-super | Pendiente | — | — |
| 2 | Modelo de datos y base de datos SQLite | nemotron + Laguna | Pendiente | — | — |
| 3 | Arte y assets RPG | LLM imágenes (OpenArt) | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 4 | Lógica financiera base | Claude Code | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 5 | Lógica financiera avanzada | Claude Code | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 6 | Perfiles de pago y dashboard compartible | Claude + nemotron | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 7 | Presupuesto semanal y suscripciones | Claude Code | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 8 | Sistema de personaje, puntos, armadura y badges | Claude + nemotron | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 9 | UI de dimensiones y portales | Laguna-s-2.1 | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 10 | Cofres, sonido y desbloqueo | Laguna + Claude | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 11 | Integración completa y pruebas | Laguna + nemotron | ✅ Completada | 2026-11-11 | 2026-11-11 |
| 12 | Build, empaquetado y despliegue | Laguna-s-2.1 | Pendiente | — | — |
| N | Mantenimiento y expansiones | Según corresponda | Pendiente | — | — |

---

Cuando completes una fase, actualiza esta tabla y el campo "Estado" de la fase correspondiente.
