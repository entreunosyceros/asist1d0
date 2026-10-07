"""
Enumeraciones del dominio Asist{1d0}.

Roles de acceso, estados del ciclo de vida de una incidencia y niveles
de prioridad (con color/icono para la interfaz).
"""

from enum import Enum


class Rol(str, Enum):
    """Rol de aplicación: define menús, permisos y vistas visibles."""

    USUARIO = "usuario"
    TECNICO = "tecnico"
    ADMINISTRADOR = "administrador"

    @property
    def etiqueta(self) -> str:
        """Etiqueta legible para la UI."""
        return {
            Rol.USUARIO: "Usuario",
            Rol.TECNICO: "Técnico",
            Rol.ADMINISTRADOR: "Administrador",
        }[self]


class EstadoIncidencia(str, Enum):
    """Estados posibles de una incidencia de soporte."""

    ABIERTA = "Abierta"
    EN_REPARACION = "En reparación"
    PENDIENTE = "Pendiente"
    CERRADA = "Cerrada"


class Prioridad(str, Enum):
    """Prioridad de atención; incluye ayudas visuales para la UI."""

    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    CRITICA = "Crítica"

    @property
    def color(self) -> str:
        """Color hexadecimal asociado a la prioridad."""
        return {
            Prioridad.BAJA: "#2e7d32",
            Prioridad.MEDIA: "#f9a825",
            Prioridad.ALTA: "#e65100",
            Prioridad.CRITICA: "#c62828",
        }[self]

    @property
    def icono(self) -> str:
        """Emoji indicador de prioridad en listados."""
        return {
            Prioridad.BAJA: "🟢",
            Prioridad.MEDIA: "🟡",
            Prioridad.ALTA: "🟠",
            Prioridad.CRITICA: "🔴",
        }[self]
