"""Exportaciones de repositorios."""

from app.database.repositories.componente_repository import ComponenteRepository
from app.database.repositories.equipo_repository import EquipoRepository
from app.database.repositories.incidencia_repository import IncidenciaRepository
from app.database.repositories.usuario_repository import UsuarioRepository

__all__ = [
    "ComponenteRepository",
    "EquipoRepository",
    "IncidenciaRepository",
    "UsuarioRepository",
]
