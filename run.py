import subprocess
import sys
import os
import webbrowser
from pathlib import Path
from src.utils.utils import BLUE, RESET
from frontend.scss_watcher import watch_scss

# Configurar la variable de entorno
os.environ["PYTHONPATH"] = str(Path(".").resolve())

def main():
    main_path = Path("frontend")
      
    # Iniciar servidor con Uvicorn usando subprocess
    print(f"\n🖥️ {BLUE} Iniciando servidor con Uvicorn...{RESET}\n")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "frontend.app:app", "--reload"],
        cwd="."
    )
    
    # Abrir el navegador
    webbrowser.open("http://127.0.0.1:8000")

    # Configuración de rutas para SCSS
    SCSS_DIRECTORY = "frontend/static/scss"
    CSS_DIRECTORY = "frontend/static/css"

    # Iniciar la monitorización de archivos SCSS
    watch_scss(SCSS_DIRECTORY, CSS_DIRECTORY)

    # Esperar a que el proceso del servidor termine
    frontend_process.wait()

# Ejecuta el servidor
if __name__ == "__main__":
    main()
