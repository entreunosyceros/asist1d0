"""
Arranque de dependencias de Asist{1d0}.

Inicializa logging, la base SQLite (schema + migraciones + seed demo),
repositorios y servicios, y los agrupa en ``AppContext`` para inyectarlos
en la interfaz.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.auth.service import AuthService
from app.config import LOG_FILE
from app.database.connection import DatabaseConnection, get_db
from app.database.repositories import (
    ComponenteRepository,
    EquipoRepository,
    IncidenciaRepository,
    UsuarioRepository,
)
from app.database.seed import seed_database
from app.database.migrations import migrate_schema
from app.services import (
    EquipoService,
    HistorialService,
    IncidenciaService,
    InventarioService,
    ReportService,
    UsuarioService,
)
from app.services.notificador import NotificadorCompuesto, NotificadorConsola, NotificadorEmail


def setup_logging() -> None:
    """Configura log a fichero (logs/) y a la consola."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


@dataclass
class AppContext:
    """Contenedor de servicios y repositorios compartidos por la UI."""

    db: DatabaseConnection
    auth: AuthService
    usuarios: UsuarioService
    equipos: EquipoService
    incidencias: IncidenciaService
    inventario: InventarioService
    informes: ReportService
    historial: HistorialService
    usuario_repo: UsuarioRepository
    equipo_repo: EquipoRepository
    incidencia_repo: IncidenciaRepository
    componente_repo: ComponenteRepository


def bootstrap() -> AppContext:
    """Construye e inicializa el contexto completo de la aplicación."""
    setup_logging()
    db = get_db()
    db.initialize()
    migrate_schema(db)
    seed_database(db)

    usuario_repo = UsuarioRepository(db)
    equipo_repo = EquipoRepository(db)
    incidencia_repo = IncidenciaRepository(db)
    componente_repo = ComponenteRepository(db)

    return AppContext(
        db=db,
        auth=AuthService(usuario_repo),
        usuarios=UsuarioService(usuario_repo),
        equipos=EquipoService(equipo_repo),
        incidencias=IncidenciaService(
            incidencia_repo,
            # Notificaciones por consola y “email” simulado (fase 1).
            NotificadorCompuesto(NotificadorConsola(), NotificadorEmail()),
        ),
        inventario=InventarioService(componente_repo),
        informes=ReportService(db),
        historial=HistorialService(incidencia_repo),
        usuario_repo=usuario_repo,
        equipo_repo=equipo_repo,
        incidencia_repo=incidencia_repo,
        componente_repo=componente_repo,
    )
