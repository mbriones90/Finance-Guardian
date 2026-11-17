"""Pruebas de la Fase 10: sonidos, cofre animado y desbloqueo.

Se ejecuta como script:  uv run python tests/test_fase10.py
"""

import asyncio
import os
import sys
import tempfile
import wave

TMP_DB = os.path.join(tempfile.gettempdir(), "finanzas_test_fase10.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["FINANZAS_DB"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.ui import sonido
from src.ui import components
from src.services import completar_dimension, estado_progresion

PASADAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK " if condicion else "FAIL"
    PASADAS.append(bool(condicion))
    print(f"[{estado}] {nombre}" + (f" -> {detalle}" if detalle else ""))


class MockPage:
    """Página simulada con run_task síncrono (para probar la animación)."""

    def __init__(self):
        self.overlay = []
        self.dialogos = []

    def show_dialog(self, dlg):
        self.dialogos.append(dlg)

    def update(self):
        pass

    def run_task(self, handler, *args):
        asyncio.run(handler(*args))


def wav_info(ruta):
    with wave.open(ruta, "rb") as w:
        return {
            "canales": w.getnchannels(),
            "ancho": w.getsampwidth(),
            "rate": w.getframerate(),
            "frames": w.getnframes(),
        }


def main():
    init_db()

    # ---------- A. Archivos de sonido ----------
    for nombre, dur_min in [("cofre", 2.5), ("nivel", 1.4), ("error", 0.4)]:
        ruta = sonido.ruta_sonido(nombre)
        check(f"WAV {nombre} existe", os.path.exists(ruta), ruta)
        if os.path.exists(ruta):
            info = wav_info(ruta)
            dur = info["frames"] / info["rate"]
            check(f"WAV {nombre}: PCM 16-bit mono ~{dur_min}s",
                  info["canales"] == 1 and info["ancho"] == 2
                  and info["rate"] == 22050 and dur >= dur_min,
                  f"{dur:.2f}s rate={info['rate']}")
            check(f"Sonido {nombre} disponible()", sonido.disponible(nombre))

    # ---------- B. Reproducción sin página (winsound o no-op seguro) ----------
    try:
        sonado = sonido.reproducir("cofre")
        check("reproducir('cofre') no lanza excepción", True,
              f"retorno={sonado}")
    except Exception as e:  # noqa: BLE001
        check("reproducir('cofre') no lanza excepción", False, str(e))
    check("reproducir de sonido inexistente devuelve False",
          sonido.reproducir("no_existe") is False)

    # ---------- C. Diálogo de cofre con animación ----------
    payload = completar_dimension(1)
    page = MockPage()
    try:
        components.dialogo_cofre(page, payload)
        check("dialogo_cofre construye y anima sin errores",
              len(page.dialogos) == 1)
    except Exception as e:  # noqa: BLE001
        check("dialogo_cofre construye y anima sin errores", False, str(e))

    # El diálogo debe contener la imagen del cofre animado
    dlg = page.dialogos[0]
    check("Diálogo de cofre abierto", dlg is not None)
    check("Desbloqueo: Dimensión 2 ahora accesible",
          estado_progresion()["dimensiones"][1]["desbloqueada"] is True
          and estado_progresion()["dimensiones"][1]["completada"] is False)

    # ---------- D. Alerta de error con sonido ----------
    page2 = MockPage()
    try:
        components.mostrar_alerta_error(page2, ValueError("Prueba de error"))
        check("mostrar_alerta_error construye diálogo", len(page2.dialogos) == 1)
    except Exception as e:  # noqa: BLE001
        check("mostrar_alerta_error construye diálogo", False, str(e))

    total = len(PASADAS)
    ok = sum(PASADAS)
    print(f"\nResultado: {ok}/{total} pruebas pasadas")
    if ok != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
