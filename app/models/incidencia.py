"""
Modelos de incidencia, intervención e historial de cambios.

``Incidencia`` es el ticket de soporte; ``Intervencion`` registra
acciones técnicas; el historial guarda cambios de estado/prioridad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.enums import EstadoIncidencia, Prioridad


@dataclass
class Intervencion:
    """Acción técnica registrada sobre una incidencia."""

    _descripcion: str
    _incidencia_id: int
    _tecnico_id: int
    _id: Optional[int] = None
    _fecha: Optional[str] = None
    _tecnico_nombre: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self._descripcion.strip():
            raise ValueError("La descripción de la intervención es obligatoria")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def incidencia_id(self) -> int:
        return self._incidencia_id

    @property
    def tecnico_id(self) -> int:
        return self._tecnico_id

    @property
    def fecha(self) -> Optional[str]:
        return self._fecha

    @property
    def tecnico_nombre(self) -> Optional[str]:
        return self._tecnico_nombre

    def __str__(self) -> str:
        fecha = self._fecha or ""
        return f"{fecha} → {self._descripcion}"


@dataclass
class Comentario:
    """Mensaje público en el hilo de una incidencia (usuario o técnico)."""

    _texto: str
    _incidencia_id: int
    _usuario_id: int
    _id: Optional[int] = None
    _fecha: Optional[str] = None
    _usuario_nombre: Optional[str] = field(default=None, repr=False)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def texto(self) -> str:
        return self._texto

    @property
    def incidencia_id(self) -> int:
        return self._incidencia_id

    @property
    def usuario_id(self) -> int:
        return self._usuario_id

    @property
    def fecha(self) -> Optional[str]:
        return self._fecha

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self._usuario_nombre


@dataclass
class HistorialEntrada:
    """Registro de un cambio (estado, prioridad, etc.) sobre una incidencia."""

    _accion: str
    _incidencia_id: int
    _usuario_id: Optional[int] = None
    _id: Optional[int] = None
    _fecha: Optional[str] = None
    _usuario_nombre: Optional[str] = field(default=None, repr=False)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def accion(self) -> str:
        return self._accion

    @property
    def incidencia_id(self) -> int:
        return self._incidencia_id

    @property
    def usuario_id(self) -> Optional[int]:
        return self._usuario_id

    @property
    def fecha(self) -> Optional[str]:
        return self._fecha

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self._usuario_nombre


@dataclass
class Incidencia:
    """Ticket de soporte vinculado a un equipo y, opcionalmente, a un técnico."""
    """Incidencia con composición de intervenciones e historial."""

    _titulo: str
    _equipo_id: int
    _descripcion: str = ""
    _estado: EstadoIncidencia = EstadoIncidencia.ABIERTA
    _prioridad: Prioridad = Prioridad.MEDIA
    _tecnico_id: Optional[int] = None
    _id: Optional[int] = None
    _fecha_creacion: Optional[str] = None
    _fecha_cierre: Optional[str] = None
    _intervenciones: list[Intervencion] = field(default_factory=list)
    _historial: list[HistorialEntrada] = field(default_factory=list)
    _comentarios: list[Comentario] = field(default_factory=list)
    # Datos enriquecidos (joins)
    _equipo_nombre: Optional[str] = field(default=None, repr=False)
    _usuario_nombre: Optional[str] = field(default=None, repr=False)
    _tecnico_nombre: Optional[str] = field(default=None, repr=False)
    _usuario_id: Optional[int] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self._titulo.strip():
            raise ValueError("El título es obligatorio")
        if isinstance(self._estado, str):
            self._estado = EstadoIncidencia(self._estado)
        if isinstance(self._prioridad, str):
            self._prioridad = Prioridad(self._prioridad)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def codigo(self) -> str:
        return f"INC-{self._id:05d}" if self._id else "INC-?????"

    @property
    def titulo(self) -> str:
        return self._titulo

    @titulo.setter
    def titulo(self, value: str) -> None:
        if not value.strip():
            raise ValueError("El título es obligatorio")
        self._titulo = value.strip()

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @descripcion.setter
    def descripcion(self, value: str) -> None:
        self._descripcion = value or ""

    @property
    def estado(self) -> EstadoIncidencia:
        return self._estado

    @estado.setter
    def estado(self, value: EstadoIncidencia | str) -> None:
        self._estado = EstadoIncidencia(value) if isinstance(value, str) else value

    @property
    def prioridad(self) -> Prioridad:
        return self._prioridad

    @prioridad.setter
    def prioridad(self, value: Prioridad | str) -> None:
        self._prioridad = Prioridad(value) if isinstance(value, str) else value

    @property
    def equipo_id(self) -> int:
        return self._equipo_id

    @property
    def tecnico_id(self) -> Optional[int]:
        return self._tecnico_id

    @tecnico_id.setter
    def tecnico_id(self, value: Optional[int]) -> None:
        self._tecnico_id = value

    @property
    def fecha_creacion(self) -> Optional[str]:
        return self._fecha_creacion

    @property
    def fecha_cierre(self) -> Optional[str]:
        return self._fecha_cierre

    @property
    def intervenciones(self) -> list[Intervencion]:
        return self._intervenciones

    @property
    def historial(self) -> list[HistorialEntrada]:
        return self._historial

    @property
    def comentarios(self) -> list[Comentario]:
        return self._comentarios

    @property
    def equipo_nombre(self) -> Optional[str]:
        return self._equipo_nombre

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self._usuario_nombre

    @property
    def tecnico_nombre(self) -> Optional[str]:
        return self._tecnico_nombre

    @property
    def usuario_id(self) -> Optional[int]:
        return self._usuario_id

    def agregar_intervencion(self, intervencion: Intervencion) -> None:
        self._intervenciones.append(intervencion)

    def esta_abierta(self) -> bool:
        return self._estado != EstadoIncidencia.CERRADA

    def __str__(self) -> str:
        return f"{self.codigo} {self._prioridad.icono} {self._titulo}"


def intervencion_desde_fila(row) -> Intervencion:
    data = dict(row)
    return Intervencion(
        _id=data["id"],
        _incidencia_id=data["incidencia_id"],
        _tecnico_id=data["tecnico_id"],
        _descripcion=data["descripcion"],
        _fecha=data.get("fecha"),
        _tecnico_nombre=data.get("tecnico_nombre"),
    )


def historial_desde_fila(row) -> HistorialEntrada:
    data = dict(row)
    return HistorialEntrada(
        _id=data["id"],
        _incidencia_id=data["incidencia_id"],
        _accion=data["accion"],
        _usuario_id=data.get("usuario_id"),
        _fecha=data.get("fecha"),
        _usuario_nombre=data.get("usuario_nombre"),
    )


def comentario_desde_fila(row) -> Comentario:
    data = dict(row)
    return Comentario(
        _id=data["id"],
        _incidencia_id=data["incidencia_id"],
        _usuario_id=data["usuario_id"],
        _texto=data["texto"],
        _fecha=data.get("fecha"),
        _usuario_nombre=data.get("usuario_nombre"),
    )


def incidencia_desde_fila(row) -> Incidencia:
    data = dict(row)
    return Incidencia(
        _id=data["id"],
        _equipo_id=data["equipo_id"],
        _tecnico_id=data.get("tecnico_id"),
        _titulo=data["titulo"],
        _descripcion=data.get("descripcion") or "",
        _estado=data["estado"],
        _prioridad=data["prioridad"],
        _fecha_creacion=data.get("fecha_creacion"),
        _fecha_cierre=data.get("fecha_cierre"),
        _equipo_nombre=data.get("equipo_nombre"),
        _usuario_nombre=data.get("usuario_nombre"),
        _tecnico_nombre=data.get("tecnico_nombre"),
        _usuario_id=data.get("usuario_id"),
    )
