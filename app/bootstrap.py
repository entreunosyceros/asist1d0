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
    AuditRepository,
    ComponenteRepository,
    EquipoRepository,
    GrupoRepository,
    IncidenciaRepository,
    KnowledgeRepository,
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
from app.services.audit_service import AuditService
from app.services.grupo_service import GrupoService
from app.services.knowledge_service import KnowledgeService
from app.services.notificador import NotificadorCompuesto, NotificadorConsola, NotificadorEmail
from app.services.search_service import SearchService


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
    audit: AuditService
    usuarios: UsuarioService
    equipos: EquipoService
    incidencias: IncidenciaService
    inventario: InventarioService
    grupos: GrupoService
    conocimiento: KnowledgeService
    busqueda: SearchService
    informes: ReportService
    historial: HistorialService
    usuario_repo: UsuarioRepository
    equipo_repo: EquipoRepository
    incidencia_repo: IncidenciaRepository
    componente_repo: ComponenteRepository
    grupo_repo: GrupoRepository


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
    grupo_repo = GrupoRepository(db)
    knowledge_repo = KnowledgeRepository(db)
    audit_repo = AuditRepository(db)
    audit = AuditService(audit_repo)
    grupos = GrupoService(grupo_repo, audit=audit)
    conocimiento = KnowledgeService(knowledge_repo, audit=audit)

    return AppContext(
        db=db,
        auth=AuthService(usuario_repo, audit=audit),
        audit=audit,
        usuarios=UsuarioService(usuario_repo, audit=audit),
        equipos=EquipoService(equipo_repo, audit=audit),
        incidencias=IncidenciaService(
            incidencia_repo,
            NotificadorCompuesto(NotificadorConsola(), NotificadorEmail()),
            audit=audit,
            grupos=grupo_repo,
        ),
        inventario=InventarioService(componente_repo, audit=audit),
        grupos=grupos,
        conocimiento=conocimiento,
        busqueda=SearchService(db),
        informes=ReportService(db),
        historial=HistorialService(incidencia_repo),
        usuario_repo=usuario_repo,
        equipo_repo=equipo_repo,
        incidencia_repo=incidencia_repo,
        componente_repo=componente_repo,
        grupo_repo=grupo_repo,
    )
