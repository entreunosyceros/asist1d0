"""
Paquete de modelos de dominio (POO).

Reexporta entidades y enums usados por repositorios, servicios y UI.
"""

from app.models.componente import Componente, componente_desde_fila
from app.models.enums import EstadoIncidencia, Prioridad, Rol
from app.models.equipo import Equipo, equipo_desde_fila
from app.models.incidencia import (
    HistorialEntrada,
    Incidencia,
    Intervencion,
    historial_desde_fila,
    incidencia_desde_fila,
    intervencion_desde_fila,
)
from app.models.usuario import Administrador, Tecnico, Usuario, usuario_desde_fila

__all__ = [
    "Administrador",
    "Componente",
    "Equipo",
    "EstadoIncidencia",
    "HistorialEntrada",
    "Incidencia",
    "Intervencion",
    "Prioridad",
    "Rol",
    "Tecnico",
    "Usuario",
    "componente_desde_fila",
    "equipo_desde_fila",
    "historial_desde_fila",
    "incidencia_desde_fila",
    "intervencion_desde_fila",
    "usuario_desde_fila",
]
