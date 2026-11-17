"""Genera los sonidos del juego con Python puro (sin dependencias ni ffmpeg).

Sintetiza WAV 16-bit mono mediante suma de armónicos con envolvente
exponencial, estilo "campana mágica" (arpégio brillante ascendente como
el cofre de Zelda, fanfarria de nivel y buzz de error).

Uso:  uv run python scripts/generar_sonidos.py
Salida: assets/sonidos/{cofre,nivel,error}.wav
"""

import math
import os
import struct
import wave

SR = 22050  # Hz, suficiente para chimes
SALIDA = os.path.join("assets", "sonidos")


def nota(freq: float, duracion: float, volumen: float = 0.3,
         armonicos=((1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12))) -> list:
    """Una nota con armónicos y decaimiento exponencial (timbre de campana)."""
    n = int(SR * duracion)
    salida = []
    for i in range(n):
        t = i / SR
        env = math.exp(-3.2 * t / duracion)
        val = sum(amp * math.sin(2 * math.pi * freq * h * t)
                  for h, amp in armonicos)
        salida.append(val * env * volumen)
    return salida


def mezclar(eventos, duracion_total: float) -> bytes:
    """Mezcla eventos (freq, inicio_s, dur_s, vol) y devuelve PCM 16-bit."""
    total = int(SR * duracion_total)
    mezcla = [0.0] * total
    for freq, inicio, dur, vol in eventos:
        seg = nota(freq, dur, vol)
        inicio_muestra = int(SR * inicio)
        for j, v in enumerate(seg):
            if inicio_muestra + j < total:
                mezcla[inicio_muestra + j] += v
    pico = max(abs(v) for v in mezcla) or 1.0
    ganancia = 0.85 / pico
    return b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, v * ganancia)) * 32767))
        for v in mezcla
    )


def guardar(nombre: str, pcm: bytes) -> str:
    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, f"{nombre}.wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
    print(f"OK {ruta} ({os.path.getsize(ruta)} bytes)")
    return ruta


# --- Arpégio pentatónico ascendente (cofre estilo Zelda) ---
LA4, SI4, DOs5, MI5, FAs5, LA5, DOs6, MI6 = (
    440.00, 493.88, 554.37, 659.26, 739.99, 880.00, 1108.73, 1318.51,
)
escala = [LA4, SI4, DOs5, MI5, FAs5, LA5, DOs6, MI6]
eventos_cofre = [
    (f, i * 0.11, 1.1, 0.22) for i, f in enumerate(escala)
] + [(LA5, 0.88, 1.7, 0.14)]  # cola brillante

# --- Fanfarria de nivel (C mayor, triunfal) ---
DO5, MI5, SOL5, DO6 = 523.25, 659.26, 783.99, 1046.50
eventos_nivel = [
    (DO5, 0.00, 0.40, 0.26),
    (MI5, 0.14, 0.40, 0.26),
    (SOL5, 0.28, 0.40, 0.26),
    (DO6, 0.42, 1.00, 0.30),
    (SOL5, 0.42, 1.00, 0.12),
]

# --- Error (grave y corto) ---
eventos_error = [(110.0, 0.0, 0.38, 0.30), (220.0, 0.0, 0.20, 0.10)]


def main():
    guardar("cofre", mezclar(eventos_cofre, 2.7))
    guardar("nivel", mezclar(eventos_nivel, 1.5))
    guardar("error", mezclar(eventos_error, 0.45))


if __name__ == "__main__":
    main()
