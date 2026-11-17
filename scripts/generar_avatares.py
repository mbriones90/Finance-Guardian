"""Genera los avatares pixel-art 8 bits del Guardián (24x24 → 192x192).

Un caballero retro cuyo color de armadura refleja el estado financiero:
- guardian_legendario.png: dorado (sin deuda ni alertas)
- guardian_fuerte.png: verde (todo en orden)
- guardian_herido.png: ámbar con vendaje (alertas amarillas)
- guardian_critico.png: rojo (alertas rojas)

Sin dependencias: el PNG se escribe a mano con zlib/struct.
Uso: uv run python scripts/generar_avatares.py
"""

import os
import struct
import zlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "assets", "personaje")

# Paletas por estado: armadura, pluma, detalle extra
PALETAS = {
    "legendario": {"armadura": (234, 179, 8), "pluma": (59, 130, 246),
                   "ojos": (38, 70, 130)},
    "fuerte": {"armadura": (34, 139, 76), "pluma": (20, 90, 50),
               "ojos": (30, 60, 40)},
    "herido": {"armadura": (217, 145, 22), "pluma": (150, 90, 10),
               "ojos": (90, 60, 20)},
    "critico": {"armadura": (200, 45, 45), "pluma": (120, 20, 20),
                "ojos": (255, 230, 60)},
}

PIEL = (240, 200, 160)
PIEL_SOMBRA = (215, 170, 130)
OSCURO = (40, 32, 36)
GRIS = (120, 118, 130)
BLANCO = (250, 250, 250)


def lienzo():
    return [[None] * 24 for _ in range(24)]


def rect(img, x0, y0, x1, y1, color):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < 24 and 0 <= y < 24:
                img[y][x] = color


def dibujar_guardian(estado: str):
    p = PALETAS[estado]
    img = lienzo()
    arm = p["armadura"]

    # Pluma del casco
    rect(img, 11, 0, 12, 3, p["pluma"])
    # Casco
    rect(img, 7, 3, 16, 5, arm)
    rect(img, 6, 5, 17, 8, arm)
    rect(img, 6, 8, 17, 9, OSCURO)          # visor
    rect(img, 8, 8, 9, 8, p["ojos"])        # ojo izquierdo
    rect(img, 14, 8, 15, 8, p["ojos"])      # ojo derecho
    # Cara
    rect(img, 8, 10, 15, 12, PIEL)
    rect(img, 8, 12, 15, 12, PIEL_SOMBRA)
    # Cuello y torso (armadura)
    rect(img, 10, 13, 13, 13, PIEL)
    rect(img, 6, 14, 17, 20, arm)
    rect(img, 10, 14, 13, 20, GRIS)         # peto central
    rect(img, 11, 15, 12, 17, BLANCO)       # brillo del peto
    # Brazos
    rect(img, 4, 14, 5, 18, arm)
    rect(img, 18, 14, 19, 18, arm)
    rect(img, 4, 18, 5, 19, PIEL)           # mano izquierda
    rect(img, 18, 18, 19, 19, PIEL)         # mano derecha
    # Piernas
    rect(img, 7, 21, 10, 23, OSCURO)
    rect(img, 13, 21, 16, 23, OSCURO)
    # Espada a la derecha
    rect(img, 21, 10, 22, 17, GRIS)
    rect(img, 20, 17, 22, 18, arm)
    rect(img, 21, 19, 22, 20, OSCURO)
    # Escudo a la izquierda
    rect(img, 1, 13, 3, 17, arm)
    rect(img, 1, 18, 3, 18, OSCURO)
    rect(img, 2, 14, 2, 16, BLANCO)

    if estado == "herido":
        # Vendaje cruzado en el casco
        rect(img, 7, 4, 12, 5, BLANCO)
        rect(img, 12, 3, 13, 5, BLANCO)
    if estado == "legendario":
        # Destellos alrededor
        for x, y in ((2, 2), (20, 3), (3, 8), (21, 6)):
            img[y][x] = (255, 240, 150)
    return img


def escribir_png(ruta: str, img, escala: int = 8):
    """Escribe el lienzo 24x24 como PNG RGBA escalado (nearest neighbor)."""
    alto, ancho = 24 * escala, 24 * escala
    raw = bytearray()
    for y in range(alto):
        raw.append(0)  # filtro 0 por scanline
        fila = img[y // escala]
        for x in range(ancho):
            color = fila[x // escala]
            if color is None:
                raw += bytes((0, 0, 0, 0))  # transparente
            else:
                raw += bytes((*color, 255))

    def chunk(tipo: bytes, datos: bytes) -> bytes:
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(ruta, "wb") as f:
        f.write(png)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for estado in PALETAS:
        ruta = os.path.join(OUT_DIR, f"guardian_{estado}.png")
        escribir_png(ruta, dibujar_guardian(estado))
        print(f"OK {ruta}")


if __name__ == "__main__":
    main()
