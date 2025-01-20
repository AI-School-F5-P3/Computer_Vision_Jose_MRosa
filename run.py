import subprocess
import sys
import os
import time
import webbrowser
import requests
from pathlib import Path
from src.utils.utils import BLUE, RESET
from frontend.scss_watcher import watch_scss

# Configurar la variable de entorno
os.environ["PYTHONPATH"] = str(Path(".").resolve())

def wait_for_server(url, timeout=30):
    """
    Espera a que el servidor esté disponible antes de continuar.
    """
    start_time = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            pass

        if time.time() - start_time > timeout:
            print(f"\n⏰ {BLUE}Tiempo de espera agotado. El servidor no respondió.{RESET}\n")
            return False

        time.sleep(1)

def start_server():
    """
    Inicia el servidor Uvicorn.
    """
    print(f"\n🖥️ {BLUE} Iniciando servidor con Uvicorn...{RESET}\n")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--reload"],
        cwd="."
    )

def main():
    # Iniciar servidor
    frontend_process = start_server()

    # Esperar a que el servidor esté disponible
    SERVER_URL = "http://127.0.0.1:8000"  # Ajusta la URL si es necesario
    if wait_for_server(SERVER_URL):
        print(f"\n🌐 {BLUE}Servidor iniciado con éxito. Abriendo navegador...{RESET}\n")
        webbrowser.open(Path("frontend/static/html/home.html").resolve().as_uri())
    else:
        print(f"\n❌ {BLUE}No se pudo iniciar el servidor. Cerrando...{RESET}\n")
        frontend_process.terminate()
        return

    # Configuración de rutas para SCSS
    SCSS_DIRECTORY = "frontend/static/scss"
    CSS_DIRECTORY = "frontend/static/css"

    # Iniciar la monitorización de archivos SCSS
    watch_scss(SCSS_DIRECTORY, CSS_DIRECTORY)

    # Esperar a que el proceso del servidor termine
    frontend_process.wait()

if __name__ == "__main__":
    # Nos aseguramos de que el código solo se ejecute en el proceso principal
    if "uvicorn" not in sys.argv:
        main()
