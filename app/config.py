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
ADJUNTOS_DIR = DATA_DIR / "adjuntos"
DB_PATH = DATA_DIR / "asist1d0.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "database" / "schema.sql"
LOG_FILE = LOGS_DIR / "asist1d0.log"
# Límites de adjuntos en incidencias.
ADJUNTO_MAX_BYTES = 10 * 1024 * 1024
ADJUNTO_EXTENSIONES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".txt",
    ".log",
    ".zip",
}

# SLA: días naturales desde la creación hasta el vencimiento (Crítica = 24 h).
# Se importa Prioridad de forma diferida en enums para evitar ciclo.
SLA_DIAS_POR_PRIORIDAD = {
    "Baja": 7,
    "Media": 3,
    "Alta": 1,
    "Crítica": 0,
}

SMTP_CONFIG_PATH = DATA_DIR / "smtp.json"
API_HOST = "127.0.0.1"
API_PORT = 8765
JWT_SECRET = "asist1d0-dev-secret-change-in-production"
JWT_HOURS = 12

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
ADJUNTOS_DIR.mkdir(parents=True, exist_ok=True)
