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

    @property
    def etiqueta_usuario(self) -> str:
        """Texto orientado al usuario final (seguimiento del ticket)."""
        return {
            EstadoIncidencia.ABIERTA: "En cola",
            EstadoIncidencia.EN_REPARACION: "En reparación",
            EstadoIncidencia.PENDIENTE: "Esperando tu respuesta",
            EstadoIncidencia.CERRADA: "Cerrada",
        }[self]


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

    @property
    def dias_sla(self) -> int:
        """Días de plazo SLA (0 = 24 horas para Crítica)."""
        from app.config import SLA_DIAS_POR_PRIORIDAD

        return int(SLA_DIAS_POR_PRIORIDAD.get(self.value, 3))


class CategoriaIncidencia(str, Enum):
    """
    Alias legacy de categorías planas.

    El catálogo jerárquico vive en ``app.models.catalogo_categorias``.
    Estos valores se normalizan a códigos ``Familia/Hoja`` al resolver.
    """

    RED = "Red"
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    IMPRESORA = "Impresora"
    CUENTA = "Cuenta"
    OTRO = "Otro"

    @property
    def plantilla(self) -> tuple[str, str]:
        """Compatibilidad: delega en el catálogo elaborado."""
        from app.models.catalogo_categorias import resolver_categoria

        hoja = resolver_categoria(self.value)
        if hoja is None:
            return ("Otra incidencia", "Describe el problema.")
        p = hoja.perfil.plantilla
        return (p.titulo, p.descripcion)
