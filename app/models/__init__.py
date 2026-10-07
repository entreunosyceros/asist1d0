"""
Paquete de modelos de dominio (POO).

Reexporta entidades y enums usados por repositorios, servicios y UI.
"""

from app.models.audit import AuditAction, AuditEntity, AuditEntry, audit_desde_fila
from app.models.catalogo_categorias import (
    CategoriaHoja,
    CategoriaNodo,
    PerfilCategoria,
    catalogo_api,
    listar_hojas,
    resolver_categoria,
)
from app.models.grupo import GrupoSoporte
from app.models.componente import Componente, componente_desde_fila
from app.models.enums import CategoriaIncidencia, EstadoIncidencia, Prioridad, Rol
from app.models.equipo import (
    Equipo,
    EquipoComponente,
    EquipoReparacion,
    EquipoSoftware,
    equipo_desde_fila,
)
from app.models.incidencia import (
    HistorialEntrada,
    Incidencia,
    Intervencion,
    historial_desde_fila,
    incidencia_desde_fila,
    intervencion_desde_fila,
)
from app.models.timeline import TimelineEvent, TimelineKind, construir_timeline
from app.models.usuario import Administrador, Tecnico, Usuario, usuario_desde_fila

__all__ = [
    "Administrador",
    "AuditAction",
    "AuditEntity",
    "AuditEntry",
    "CategoriaHoja",
    "CategoriaIncidencia",
    "CategoriaNodo",
    "Componente",
    "Equipo",
    "EquipoComponente",
    "EquipoReparacion",
    "EquipoSoftware",
    "EstadoIncidencia",
    "GrupoSoporte",
    "HistorialEntrada",
    "Incidencia",
    "Intervencion",
    "PerfilCategoria",
    "Prioridad",
    "Rol",
    "Tecnico",
    "TimelineEvent",
    "TimelineKind",
    "Usuario",
    "audit_desde_fila",
    "catalogo_api",
    "componente_desde_fila",
    "construir_timeline",
    "equipo_desde_fila",
    "historial_desde_fila",
    "incidencia_desde_fila",
    "intervencion_desde_fila",
    "listar_hojas",
    "resolver_categoria",
    "usuario_desde_fila",
]
