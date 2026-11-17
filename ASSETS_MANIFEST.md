# Manifiesto de Assets — Fase 3

> Generado con **OpenArt MCP** (modelo **Seedream 5.5**, 12 créditos/imagen, fondos transparentes nativos).
> Todos los sprites e iconos son **PNG con canal alfa** (transparente). Los fondos son **PNG opacos 16:9**.
> Fecha de generación: 2026-11-11.

---

## 1. Personajes (`assets/personajes/`)

| Archivo | Calidad | Uso |
|---------|---------|-----|
| `guerrero_base.png` | Base (gris) | Personaje default al iniciar |
| `armadura_gris.png` | Gris (común) | Armadura calidad gris |
| `armadura_verde.png` | Verde (poco común) | Armadura calidad verde |
| `armadura_azul.png` | Azul (raro) | Armadura calidad azul |
| `armadura_morado.png` | Morado (épico) | Armadura calidad morado |
| `armadura_naranja.png` | Naranja (legendario) | Armadura calidad naranja |

- Tamaño: 880 × 1184 px (ratio 3:4), fondo transparente.
- Consistencia: las 5 armaduras usan el mismo personaje (rostro, pose, escudo) que el base, generadas con `image2image` desde `guerrero_base.png`.

---

## 2. Cofres (`assets/cofres/`) — 12 niveles

| Archivo | Nivel | Dimensión asociada |
|---------|-------|--------------------|
| `cofre_madera.png` | 1 | D1 El Despertar |
| `cofre_hierro.png` | 2 | D2 El Camino del Oro |
| `cofre_bronce.png` | 3 | D3 Bosque de Gastos |
| `cofre_plata.png` | 4 | D4 Puerta del Crédito |
| `cofre_oro.png` | 5 | D5 Cámara de Reglas |
| `cofre_esmeralda.png` | 6 | D6 Llanura del Presupuesto |
| `cofre_zafiro.png` | 7 | D7 Mercado de Suscripciones |
| `cofre_rubi.png` | 8 | D8 Prueba del Dragón |
| `cofre_diamante.png` | 9 | D9 Salón de Estrategas |
| `cofre_legendario.png` | 10 | D10 Forja del Guardián |
| `cofre_eterno.png` | 11 | D11 Torre de Comparación |
| `cofre_supremo.png` | 12 | D13 Dimensión Maestra |

- Tamaño: 1024 × 1024 px (ratio 1:1), fondo transparente.

---

## 3. Fondos de dimensión (`assets/fondos/`) — 13 dimensiones + variante de clima

| Archivo | Dimensión | Notas |
|---------|-----------|-------|
| `d1_despertar_dia.png` | D1 El Despertar | Clima: día claro |
| `d1_despertar_tormenta.png` | D1 El Despertar | **Misma región, clima: tormenta nocturna** (demuestra el cambio de clima A→B) |
| `d2_camino_oro.png` | D2 El Camino del Oro | Atardecer |
| `d3_bosque_gastos.png` | D3 Bosque de Gastos | Bosque con niebla |
| `d4_puerta_credito.png` | D4 Puerta del Crédito | Cañón con niebla |
| `d5_camara_reglas.png` | D5 Cámara de Reglas | Sala arcana |
| `d6_llanura_presupuesto.png` | D6 Llanura del Presupuesto | Pradera con hitos |
| `d7_mercado_suscripciones.png` | D7 Mercado de Suscripciones | Mercado medieval |
| `d8_prueba_dragon.png` | D8 Prueba del Dragón | Guarida volcánica |
| `d9_salon_estrategas.png` | D9 Salón de Estrategas | Sala de guerra |
| `d10_forja_guardian.png` | D10 Forja del Guardián | Forja enana |
| `d11_torre_comparacion.png` | D11 Torre de Comparación | Arena de duelo |
| `d12_santuario_datos.png` | D12 Santuario de Datos | Biblioteca arcana |
| `d13_dimension_maestra.png` | D13 Dimensión Maestra | Nexus cósmico |

- Tamaño: 1360 × 768 px aprox. (ratio 16:9), fondo opaco.

**Mecánica de clima:** para cada dimensión se puede generar una o más variantes climáticas (día/noche, tormenta, nieve, etc.) reusando el mismo prompt base. Ya existe el ejemplo D1 día vs. D1 tormenta.

---

## 4. Badges / Pines (`assets/badges/`) — 6

| Archivo | Logro |
|---------|-------|
| `badge_primera_cuenta.png` | Primera cuenta creada |
| `badge_primer_ingreso.png` | Primer ingreso registrado |
| `badge_primer_gasto.png` | Primer gasto registrado |
| `badge_primera_tarjeta.png` | Primera tarjeta creada |
| `badge_maestro_reglas.png` | Reglas de tarjetas configuradas |
| `badge_guardian_supremo.png` | Dimensión maestra completada |

- Tamaño: 1024 × 1024 px, fondo transparente.

---

## 5. Iconos de UI (`assets/iconos/`) — 6

| Archivo | Uso |
|---------|-----|
| `icono_moneda.png` | Dinero / saldo |
| `icono_cuenta.png` | Cuentas bancarias |
| `icono_tarjeta.png` | Tarjetas de crédito |
| `icono_estadistica.png` | Dashboard / estadísticas |
| `icono_suscripcion.png` | Suscripciones / gastos fijos |
| `icono_exportar.png` | Exportar CSV |

- Tamaño: 1024 × 1024 px, fondo transparente.

---

## 6. Pendiente de la Fase 3 (sonido)

**Los sonidos de cofre (estilo Zelda) NO se generaron**, porque OpenArt MCP solo produce imagen y video (no audio), y no hay `ffmpeg` instalado para extraer audio de un video.

Opciones para resolverlo:
1. Descargar efectos de sonido libres de regalías (ej. freesound.org) y colocarlos en `assets/sonidos/`.
2. Generar un video de cofre abriéndose con audio (Seedance/Gemini Omni) e instalar `ffmpeg` para extraer la pista.
3. Añadir un MCP de audio si existe.

Recomendación: opción 1 para arrancar rápido; opción 2 si se quiere un sonido 100 % original.

---

## 6. Sonidos (`assets/sonidos/`) — generados con Python puro

| Archivo | Uso | Duración |
|---------|-----|----------|
| `cofre.wav` | Arpégio pentatónico ascendente (estilo Zelda) al abrir cofre | 2.7 s |
| `nivel.wav` | Fanfarria de nivel (C mayor) 0.65 s después del cofre | 1.5 s |
| `error.wav` | Buzz grave en errores de formulario | 0.45 s |

- PCM 16-bit mono 22050 Hz. Sintetizados por `scripts/generar_sonidos.py`
  (suma de armónicos con envolvente exponencial; sin dependencias ni ffmpeg).
- Reproducción: `winsound` en Windows; `flet.Audio` si la versión lo expone;
  silencio seguro en otros entornos (ver `src/ui/sonido.py`).

---

## 7. Coste aproximado de la Fase 3

| Lote | Imágenes | Créditos aprox. |
|------|----------|-----------------|
| Personaje + 5 cofres | 6 | 72 |
| 5 armaduras (image2image) | 5 | 85 |
| 6 fondos iniciales | 6 | 72 |
| 7 cofres + 6 badges | 13 | 156 |
| 8 fondos restantes | 8 | 96 |
| 6 iconos | 6 | 72 |
| **Total** | **44** | **≈ 553** |

Saldo de créditos al cierre de la Fase 3: ≈ **11,447**.
