"""
Modelo de grupo de soporte técnico.

Un técnico puede pertenecer a varios grupos; una incidencia puede
asignarse primero al grupo y luego a un técnico concreto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GrupoSoporte:
    """Cola / equipo de soporte (Hardware, Software, Redes, Sistemas…)."""

    _nombre: str
    _codigo: str
    _descripcion: str = ""
    _activo: bool = True
    _id: Optional[int] = None
    _miembros_ids: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._nombre.strip():
            raise ValueError("El nombre del grupo es obligatorio")
        if not self._codigo.strip():
            raise ValueError("El código del grupo es obligatorio")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, value: str) -> None:
        self._nombre = value.strip()

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def miembros_ids(self) -> list[int]:
        return list(self._miembros_ids)

    def __str__(self) -> str:
        return self._nombre


def grupo_desde_fila(row) -> GrupoSoporte:
    data = dict(row)
    return GrupoSoporte(
        _id=data["id"],
        _codigo=data["codigo"],
        _nombre=data["nombre"],
        _descripcion=data.get("descripcion") or "",
        _activo=bool(data.get("activo", 1)),
    )


# Códigos canónicos sembrados en BBDD / catálogo de categorías.
GRUPOS_CANONICOS: tuple[tuple[str, str, str], ...] = (
    ("soporte_hardware", "Soporte Hardware", "PCs, monitores, impresoras y periféricos"),
    ("soporte_software", "Soporte Software", "Aplicaciones, SO y licencias"),
    ("redes", "Redes", "Wi‑Fi, Ethernet, Internet y VPN"),
    ("sistemas", "Sistemas", "Cuentas, identidad y servicios generales"),
)
