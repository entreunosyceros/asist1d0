"""
Modelo de equipo informático asociado a un usuario.

Incluye especificaciones (CPU, RAM, disco, GPU) y entidades hijas
(componentes instalados, software, reparaciones) vía composición.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EquipoComponente:
    """Pieza de inventario instalada en un equipo."""

    _equipo_id: int
    _componente_id: int
    _cantidad: int = 1
    _notas: str = ""
    _id: Optional[int] = None
    _fecha: Optional[str] = None
    _componente_nombre: Optional[str] = field(default=None, repr=False)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def equipo_id(self) -> int:
        return self._equipo_id

    @property
    def componente_id(self) -> int:
        return self._componente_id

    @property
    def cantidad(self) -> int:
        return self._cantidad

    @property
    def notas(self) -> str:
        return self._notas

    @property
    def fecha(self) -> Optional[str]:
        return self._fecha

    @property
    def componente_nombre(self) -> Optional[str]:
        return self._componente_nombre

    def __str__(self) -> str:
        nombre = self._componente_nombre or f"#{self._componente_id}"
        return f"{nombre} × {self._cantidad}"


@dataclass
class EquipoSoftware:
    """Software instalado en un equipo."""

    _equipo_id: int
    _nombre: str
    _version: str = ""
    _licencia: str = ""
    _id: Optional[int] = None
    _fecha_instalacion: Optional[str] = None

    def __post_init__(self) -> None:
        if not self._nombre.strip():
            raise ValueError("El nombre del software es obligatorio")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def equipo_id(self) -> int:
        return self._equipo_id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def version(self) -> str:
        return self._version

    @property
    def licencia(self) -> str:
        return self._licencia

    @property
    def fecha_instalacion(self) -> Optional[str]:
        return self._fecha_instalacion

    def __str__(self) -> str:
        ver = f" {self._version}" if self._version else ""
        return f"{self._nombre}{ver}"


@dataclass
class EquipoReparacion:
    """Entrada del historial de reparaciones del equipo."""

    _equipo_id: int
    _descripcion: str
    _tecnico_id: Optional[int] = None
    _incidencia_id: Optional[int] = None
    _coste: float = 0.0
    _id: Optional[int] = None
    _fecha: Optional[str] = None
    _tecnico_nombre: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self._descripcion.strip():
            raise ValueError("La descripción de la reparación es obligatoria")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def equipo_id(self) -> int:
        return self._equipo_id

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def tecnico_id(self) -> Optional[int]:
        return self._tecnico_id

    @property
    def incidencia_id(self) -> Optional[int]:
        return self._incidencia_id

    @property
    def coste(self) -> float:
        return self._coste

    @property
    def fecha(self) -> Optional[str]:
        return self._fecha

    @property
    def tecnico_nombre(self) -> Optional[str]:
        return self._tecnico_nombre


@dataclass
class Equipo:
    """Equipo perteneciente a un usuario del help desk."""

    _numero_serie: str
    _marca: str
    _modelo: str
    _usuario_id: int
    _sistema_operativo: str = ""
    _cpu: str = ""
    _ram_gb: int = 0
    _almacenamiento: str = ""
    _gpu: str = ""
    _id: Optional[int] = None
    _fecha_registro: Optional[str] = None
    _usuario_nombre: Optional[str] = field(default=None, repr=False)
    _componentes: list[EquipoComponente] = field(default_factory=list)
    _software: list[EquipoSoftware] = field(default_factory=list)
    _reparaciones: list[EquipoReparacion] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._numero_serie.strip():
            raise ValueError("El número de serie es obligatorio")
        if not self._marca.strip() or not self._modelo.strip():
            raise ValueError("Marca y modelo son obligatorios")
        if self._ram_gb < 0:
            raise ValueError("La RAM no puede ser negativa")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def codigo(self) -> str:
        """Identificador legible tipo PC-023."""
        return f"PC-{(self._id or 0):03d}"

    @property
    def numero_serie(self) -> str:
        return self._numero_serie

    @numero_serie.setter
    def numero_serie(self, value: str) -> None:
        if not value.strip():
            raise ValueError("El número de serie es obligatorio")
        self._numero_serie = value.strip().upper()

    @property
    def marca(self) -> str:
        return self._marca

    @marca.setter
    def marca(self, value: str) -> None:
        self._marca = value.strip()

    @property
    def modelo(self) -> str:
        return self._modelo

    @modelo.setter
    def modelo(self, value: str) -> None:
        self._modelo = value.strip()

    @property
    def sistema_operativo(self) -> str:
        return self._sistema_operativo

    @sistema_operativo.setter
    def sistema_operativo(self, value: str) -> None:
        self._sistema_operativo = value or ""

    @property
    def cpu(self) -> str:
        return self._cpu

    @cpu.setter
    def cpu(self, value: str) -> None:
        self._cpu = value or ""

    @property
    def ram_gb(self) -> int:
        return self._ram_gb

    @ram_gb.setter
    def ram_gb(self, value: int) -> None:
        self._ram_gb = max(0, int(value))

    @property
    def almacenamiento(self) -> str:
        return self._almacenamiento

    @almacenamiento.setter
    def almacenamiento(self, value: str) -> None:
        self._almacenamiento = value or ""

    @property
    def gpu(self) -> str:
        return self._gpu

    @gpu.setter
    def gpu(self, value: str) -> None:
        self._gpu = value or ""

    @property
    def usuario_id(self) -> int:
        return self._usuario_id

    @usuario_id.setter
    def usuario_id(self, value: int) -> None:
        self._usuario_id = value

    @property
    def fecha_registro(self) -> Optional[str]:
        return self._fecha_registro

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self._usuario_nombre

    @property
    def componentes(self) -> list[EquipoComponente]:
        return self._componentes

    @property
    def software(self) -> list[EquipoSoftware]:
        return self._software

    @property
    def reparaciones(self) -> list[EquipoReparacion]:
        return self._reparaciones

    @property
    def nombre_completo(self) -> str:
        return f"{self._marca} {self._modelo}"

    def resumen_specs(self) -> str:
        partes = []
        if self._cpu:
            partes.append(self._cpu)
        if self._ram_gb:
            partes.append(f"{self._ram_gb} GB RAM")
        if self._almacenamiento:
            partes.append(self._almacenamiento)
        if self._gpu:
            partes.append(self._gpu)
        if self._sistema_operativo:
            partes.append(self._sistema_operativo)
        return " · ".join(partes) if partes else "Sin especificaciones"

    def __str__(self) -> str:
        return f"{self.codigo} {self.nombre_completo} ({self._numero_serie})"


def equipo_desde_fila(row) -> Equipo:
    data = dict(row)
    return Equipo(
        _id=data["id"],
        _usuario_id=data["usuario_id"],
        _numero_serie=data["numero_serie"],
        _marca=data["marca"],
        _modelo=data["modelo"],
        _sistema_operativo=data.get("sistema_operativo") or "",
        _cpu=data.get("cpu") or "",
        _ram_gb=int(data.get("ram_gb") or 0),
        _almacenamiento=data.get("almacenamiento") or "",
        _gpu=data.get("gpu") or "",
        _fecha_registro=data.get("fecha_registro"),
        _usuario_nombre=data.get("usuario_nombre"),
    )


def equipo_componente_desde_fila(row) -> EquipoComponente:
    data = dict(row)
    return EquipoComponente(
        _id=data["id"],
        _equipo_id=data["equipo_id"],
        _componente_id=data["componente_id"],
        _cantidad=int(data.get("cantidad") or 1),
        _notas=data.get("notas") or "",
        _fecha=data.get("fecha"),
        _componente_nombre=data.get("componente_nombre"),
    )


def equipo_software_desde_fila(row) -> EquipoSoftware:
    data = dict(row)
    return EquipoSoftware(
        _id=data["id"],
        _equipo_id=data["equipo_id"],
        _nombre=data["nombre"],
        _version=data.get("version") or "",
        _licencia=data.get("licencia") or "",
        _fecha_instalacion=data.get("fecha_instalacion"),
    )


def equipo_reparacion_desde_fila(row) -> EquipoReparacion:
    data = dict(row)
    return EquipoReparacion(
        _id=data["id"],
        _equipo_id=data["equipo_id"],
        _descripcion=data["descripcion"],
        _tecnico_id=data.get("tecnico_id"),
        _incidencia_id=data.get("incidencia_id"),
        _coste=float(data.get("coste") or 0),
        _fecha=data.get("fecha"),
        _tecnico_nombre=data.get("tecnico_nombre"),
    )
