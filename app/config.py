"""
Configuración central de Asist{1d0}.

Aquí se definen el nombre de la aplicación, la versión, la descripción
mostrada en «Acerca de», la URL del repositorio y las rutas de datos,
logs, assets y base SQLite.
"""

from pathlib import Path

# Identidad de la aplicación (UI, bandeja, diálogos).
APP_NAME = "Asist{1d0}"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Sistema de help desk para gestionar usuarios, equipos, incidencias, "
    "intervenciones, inventario de repuestos e informes de soporte técnico."
)
APP_REPO_URL = "https://github.com/entreunosyceros/asist1d0"

# Rutas absolutas derivadas de la ubicación de este paquete.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "asist1d0.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "database" / "schema.sql"
LOG_FILE = LOGS_DIR / "asist1d0.log"

# Logo del programa: coloca el archivo en assets/ con uno de estos nombres.
_LOGO_CANDIDATES = ("logo.png", "logo.svg", "logo.ico", "logo.jpg", "logo.jpeg")


def resolve_logo_path() -> Path | None:
    """Devuelve la ruta del logo si existe en assets/; si no, None."""
    for name in _LOGO_CANDIDATES:
        path = ASSETS_DIR / name
        if path.is_file():
            return path
    return None


LOGO_PATH = resolve_logo_path()

# Asegura carpetas de trabajo en el primer arranque.
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
