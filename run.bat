@echo off
cd /d "%~dp0"
echo ==========================================
echo  Iniciando entorno UV...
echo ==========================================
uv pip install "flet>=0.20.0,<1.0.0"
if errorlevel 1 (
    echo Error al instalar dependencias.
    pause
    exit /b 1
)
echo ==========================================
echo  Lanzando aplicacion...
echo ==========================================
uv run python src/main.py
pause
