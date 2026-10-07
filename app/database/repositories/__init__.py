"""Exportaciones de repositorios."""

from app.database.repositories.audit_repository import AuditRepository
from app.database.repositories.componente_repository import ComponenteRepository
from app.database.repositories.equipo_repository import EquipoRepository
from app.database.repositories.grupo_repository import GrupoRepository
from app.database.repositories.incidencia_repository import IncidenciaRepository
from app.database.repositories.knowledge_repository import KnowledgeRepository
from app.database.repositories.usuario_repository import UsuarioRepository

__all__ = [
    "AuditRepository",
    "ComponenteRepository",
    "EquipoRepository",
    "GrupoRepository",
    "IncidenciaRepository",
    "KnowledgeRepository",
    "UsuarioRepository",
]
