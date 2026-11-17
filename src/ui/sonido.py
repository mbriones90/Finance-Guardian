"""Reproducción de sonidos del juego.

Estrategia por plataforma (sin dependencias externas):
1. ``flet.Audio`` si la versión de Flet lo expone (futuro/Android).
2. ``winsound`` en Windows (reproduce WAV de forma asíncrona).
3. Silencio si ninguna vía está disponible (nunca rompe la app).

Los WAV se generan con ``scripts/generar_sonidos.py``.
"""

import os

CARPETA = os.path.join("assets", "sonidos")


def ruta_sonido(nombre: str) -> str:
    return os.path.join(CARPETA, f"{nombre}.wav")


def disponible(nombre: str) -> bool:
    return os.path.exists(ruta_sonido(nombre))


def reproducir(nombre: str, page=None) -> bool:
    """Intenta reproducir ``assets/sonidos/{nombre}.wav``. Devuelve True si sonó."""
    ruta = ruta_sonido(nombre)
    if not os.path.exists(ruta):
        return False

    # 1) flet.Audio (si la versión lo tiene y hay página)
    if page is not None:
        try:
            import flet as ft
            if hasattr(ft, "Audio"):
                if not hasattr(page, "_sonidos"):
                    page._sonidos = {}
                if nombre not in page._sonidos:
                    audio = ft.Audio(src=ruta, volume=0.7)
                    page._sonidos[nombre] = audio
                    page.overlay.append(audio)
                    page.update()
                page._sonidos[nombre].play()
                return True
        except Exception:  # noqa: BLE001
            pass

    # 2) winsound (Windows, asíncrono)
    try:
        import winsound
        winsound.PlaySound(os.path.abspath(ruta),
                           winsound.SND_ASYNC | winsound.SND_FILENAME)
        return True
    except Exception:  # noqa: BLE001
        pass

    return False
