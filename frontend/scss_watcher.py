import os
import re
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sass
import time
from src.utils.utils import PURPLE, GRAY, DARK_GRAY, BLUE, RESET

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format=f'{PURPLE}%(levelname)s - {DARK_GRAY}%(message)s{RESET}\n'
)

class SCSSCombiner:
    def __init__(self, main_file, source_directory, output_file):
        """Inicializa la clase con el archivo principal, el directorio de archivos y el archivo de salida."""
        self.main_file = os.path.abspath(main_file)
        self.source_directory = os.path.abspath(source_directory)
        self.output_file = os.path.abspath(output_file)

    def get_included_files(self):
        """Extrae los archivos mencionados con @use del archivo principal."""
        included_files = []
        if not os.path.exists(self.main_file):
            logging.error(f"El archivo principal '{self.main_file}' no fue encontrado.")
            return included_files
        
        with open(self.main_file, 'r', encoding='utf-8') as file:
            content = file.read()
            matches = re.findall(r"@use\s+'([^']+)'", content)
            included_files = [f"{match}.scss" for match in matches]
        return included_files

    def find_scss_file(self, file_name):
        """Busca un archivo SCSS con o sin guion bajo para archivos parciales."""
        normal_path = os.path.join(self.source_directory, file_name)
        partial_path = os.path.join(self.source_directory, "_" + file_name)
        if os.path.exists(normal_path):
            return normal_path
        elif os.path.exists(partial_path):
            return partial_path
        return None

    def combine_files(self):
        """Combina los archivos SCSS mencionados en el archivo principal."""
        included_files = self.get_included_files()
        if not included_files:
            logging.warning("No se encontraron archivos definidos con @use.")
            return

        with open(self.output_file, 'w', encoding='utf-8') as output:
            output.write(f"/* Archivo combinado generado automáticamente */\n\n")
            for file_name in included_files:
                file_path = self.find_scss_file(file_name)
                if file_path:
                    with open(file_path, 'r', encoding='utf-8') as scss_file:
                        output.write(f"\n/* {file_name} */\n")
                        output.write(scss_file.read())
                        output.write("\n")
                else:
                    logging.warning(f"⚠️ El archivo '{file_name}' definido en @use no fue encontrado.")
        
        logging.info(f"✅ Archivos combinados exitosamente en '{self.output_file}'")

class SCSSWatcher(FileSystemEventHandler):
    """
    Observador de cambios en archivos SCSS con recompilación automática.
    """
    def __init__(self, scss_dir, css_dir):
        self.scss_dir = os.path.abspath(scss_dir).replace("\\", "/")
        self.css_dir = os.path.abspath(css_dir).replace("\\", "/")
        self.last_compiled = 0  

        # Instancia del combinador para reutilizarlo
        self.combiner = SCSSCombiner(
            main_file=os.path.join(self.scss_dir, 'main.scss'),
            source_directory=self.scss_dir,
            output_file=os.path.join(self.scss_dir, 'combined.scss')
        )

    def on_modified(self, event):
        modified_path = event.src_path.replace("\\", "/")
        # Detectar cualquier cambio en archivos SCSS
        if modified_path.endswith('.scss'):
            if time.time() - self.last_compiled > 2:
                logging.info(f"🔄 Cambio detectado en {modified_path}. Recombining and recompiling SCSS...")
                
                # Recombinar y recompilar
                self.combiner.combine_files()
                self.compile_scss()
                self.last_compiled = time.time()

    def compile_scss(self):
        combined_scss_path = os.path.normpath(os.path.join(self.scss_dir, 'combined.scss')).replace("\\", "/")
        css_output_path = os.path.normpath(os.path.join(self.css_dir, 'styles.css')).replace("\\", "/")

        if not os.path.isfile(combined_scss_path):
            logging.error(f"❌ El archivo combinado '{combined_scss_path}' no fue encontrado.")
            return
        
        try:
            # Compilar el archivo combinado
            compiled_css = sass.compile(
                filename=combined_scss_path,
                output_style='compressed'
            )
            
            os.makedirs(self.css_dir, exist_ok=True)
            
            with open(css_output_path, 'w', encoding='utf-8') as css_file:
                css_file.write(compiled_css)

            logging.info(f"✅ SCSS compilado exitosamente en '{css_output_path}'")
        except sass.CompileError as e:
            logging.error(f"❌ Error de compilación SCSS: {e}")
        except Exception as e:
            logging.error(f"❌ Error inesperado durante la compilación: {e}")

def watch_scss(scss_dir, css_dir):
    """
    Observa un directorio SCSS y recompila automáticamente al detectar cambios en cualquier archivo SCSS.
    """
    scss_dir = os.path.abspath(scss_dir).replace("\\", "/")
    css_dir = os.path.abspath(css_dir).replace("\\", "/")

    if not os.path.exists(scss_dir):
        logging.error(f"❌ El directorio SCSS '{scss_dir}' no existe.")
        return
    if not os.path.exists(css_dir):
        os.makedirs(css_dir)
        logging.info(f"📁 Directorio CSS '{css_dir}' creado.")

    # Inicializa el observador y compila todo al iniciar
    scss_watcher = SCSSWatcher(scss_dir, css_dir)
    scss_watcher.combiner.combine_files()
    scss_watcher.compile_scss()

    event_handler = scss_watcher
    observer = Observer()
    observer.schedule(event_handler, path=scss_dir, recursive=True)
    observer.start()
    logging.info(f"👀 Observando cambios en '{scss_dir}'...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("👋 Observación detenida.")
    observer.join()

if __name__ == "__main__":
    SCSS_DIRECTORY = os.path.abspath("frontend/static/scss").replace("\\", "/")
    CSS_DIRECTORY = os.path.abspath("frontend/static/css").replace("\\", "/")

    watch_scss(SCSS_DIRECTORY, CSS_DIRECTORY)
