"""
Modelo de equipo informático asociado a un usuario.

Encapsula número de serie, marca, modelo y sistema operativo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Equipo:
    """Equipo perteneciente a un usuario del help desk."""

    _numero_serie: str
    _marca: str
    _modelo: str
    _usuario_id: int
    _sistema_operativo: str = ""
    _id: Optional[int] = None
    _fecha_registro: Optional[str] = None
    _usuario_nombre: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self._numero_serie.strip():
            raise ValueError("El número de serie es obligatorio")
        if not self._marca.strip() or not self._modelo.strip():
            raise ValueError("Marca y modelo son obligatorios")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

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
    def nombre_completo(self) -> str:
        return f"{self._marca} {self._modelo}"

    def __str__(self) -> str:
        return f"{self.nombre_completo} ({self._numero_serie})"


def equipo_desde_fila(row) -> Equipo:
    data = dict(row)
    return Equipo(
        _id=data["id"],
        _usuario_id=data["usuario_id"],
        _numero_serie=data["numero_serie"],
        _marca=data["marca"],
        _modelo=data["modelo"],
        _sistema_operativo=data.get("sistema_operativo") or "",
        _fecha_registro=data.get("fecha_registro"),
        _usuario_nombre=data.get("usuario_nombre"),
    )
