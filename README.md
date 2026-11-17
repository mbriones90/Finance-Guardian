# Finanzas — Dimensiones del Guardián 🛡️

App de finanzas personales con temática RPG medieval **retro 8 bits**: la
progresión son los **niveles del personaje**. Completar cada dimensión sube
un nivel y abre el portal a la siguiente. **8 dimensiones iterativas**
(puedes rejugarlas para editar/añadir registros y seguir ganando cofres),
avatar pixel-art que refleja tu estado financiero, armaduras, badges,
puntos y presupuestos con semáforo.

## Ejecutar en Windows
Doble clic en **`run.bat`** (instala dependencias con UV y lanza la app).

O manualmente:
```
uv pip install "flet>=0.20.0,<1.0.0"
uv run python src/main.py
```

## Generar APK para Android
```
uv run flet build apk
```
(Ver Fase 12 del plan; los assets deben empaquetarse.)

## Funcionalidades
- **Cuentas y tarjetas**: balances, fechas de corte/pago, tasa de interés,
  límite de crédito, mínimo de uso con cargo administración (Invex/Sams).
- **Ingresos y gastos**: sueldo fijo (semanal/quincenal/mensual) y
  esporádicos; gastos en pesos o dólares (tipo de cambio fijo, default 18.63).
  Cualquier registro se puede **editar o eliminar** (el balance de la cuenta
  se corrige solo) desde la sección Presupuesto.
- **Perfiles de pago**: Mínimo, Optimizado (protege liquidez y suscripciones),
  Agresivo (reserva de flujo) y Custom (combina módulos de dashboard). Se
  cambia solo en Personaje; el Resumen muestra el dashboard con los
  módulos del perfil activo.
- **Proyección de deuda**: reducción a 1/3/6/9/12 meses, fecha de liquidación,
  comparación lado a lado por perfil. Sección **Deuda** con barras tipo
  Gantt mes a mes según la estrategia elegida.
- **Presupuesto semanal**: inicia lunes, base repetible, editable por semana,
  "¿me alcanza para salir?" y simulación de compra cara.
- **Sección Presupuesto (semanal y mensual)**: gastos planeados que se
  añaden o quitan; disponible = límite − gastado − planeado. Al terminar
  el período confirmas el cierre: qué compras sí se hicieron, cuánto salió
  en gastos nuevos y si hubo ahorro o te pasaste (una sola vez por período).
- **Presupuesto general**: se define mensual, quincenal o semanal y todos
  coinciden (año = 52 semanas = 12 meses = 24 quincenas); las categorías
  no pueden pasarse del equivalente semanal.
- **Categorías de gasto**: 19 categorías en dropdown (Alimentos, Comida
  Fuera, Supermercado, Tecnología, Suscripciones, Intereses, Personal…).
- **Distribución de gastos**: real de la semana/mes y proyección por
  categoría a 1 semana, 1 mes, 1 año y 10 años.
- **Día de cobro del sueldo**: quincenal cobra día N y N+15 (o último del
  mes); aparece en el calendario.
- **Calendario y Masmorra**: vista semanal o mensual con cortes y pagos de
  tarjetas, cobros de suscripciones y días de sueldo. El presupuesto
  semanal/mensual es la masmorra: cierra la semana sin salirte y ganas
  puntos semanales.
- **Riesgos**: alertas con semáforo (límite, mínimo de uso, suscripciones).
- **RPG**: 8 dimensiones **iterativas** (rejugables con premio de repetición:
  mitad de puntos y XP), cofres, 5 armaduras (gris→naranja), 6 badges,
  fondos de dimensión, sonidos sintetizados estilo Zelda.
- **Edición total**: todos los registros de las dimensiones se pueden editar
  o eliminar desde la propia misión (✏️/🗑) y desde Presupuesto.
- **Personaje**: avatar pixel-art 8 bits que cambia según tu estado
  financiero (legendario/fuerte/herido/crítico, generado con
  `scripts/generar_avatares.py`).
- **Configuración**: sección propia con nombre, tipo de cambio, perfil de
  pago (solo se cambia aquí), armaduras, fondos y badges.
- **Estilo retro 8 bits**: fuente Press Start 2P en títulos y cifras,
  paleta pergamino, bordes gruesos de 2 px y esquinas cuadradas.
- **CSV**: exporta 9 tablas (Dimensión 12).

## UI estilo smartphone
La app ya nace con formato móvil (ventana 390×844) para facilitar la futura
versión móvil: navegación inferior con las 8 secciones (etiqueta solo en la
activa), tarjetas apiladas con wrap, semana del calendario como lista
vertical de días, mes con puntos de color (detalle en tooltip), tabla de
distribución con scroll lateral y barras de deuda compactas.

## Pruebas
```
uv run python tests/test_fase4.py     # lógica base        27 pruebas
uv run python tests/test_fase5.py     # lógica avanzada    33 pruebas
uv run python tests/test_fase6.py     # perfiles           25 pruebas
uv run python tests/test_fase7.py     # presupuesto/subs   34 pruebas
uv run python tests/test_fase8.py     # RPG                36 pruebas
uv run python tests/test_fase9_ui.py  # UI + CSV           14 pruebas
uv run python tests/test_fase10.py    # sonido/cofres      15 pruebas
uv run python tests/test_fase11_juego.py  # end-to-end     28 pruebas
uv run python tests/test_e2e_ui_formularios.py  # E2E con clics UI  69 pruebas
uv run python tests/test_calendario.py    # calendario/masmorra  35 pruebas
uv run python tests/test_dashboards_deuda.py  # dashboards/deuda 22 pruebas
uv run python tests/test_presupuesto_registros.py  # presupuesto/cierre 40 pruebas
uv run python tests/test_iteracion_avatar.py  # iteración/avatar/retro 20 pruebas
```

## Documentación
- `DRAFT_APP_FINANZAS.md` — diseño de la experiencia (dimensiones, RPG).
- `PLAN_DE_TRABAJO_AGENTES.md` — plan de trabajo por fases y agentes.
- `ASSETS_MANIFEST.md` — inventario de assets generados con OpenArt.

## Stack
Python 3.11 + UV · Flet (Windows y Android) · SQLite · Assets por OpenArt MCP.
