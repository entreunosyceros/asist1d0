"""
Modelo de usuario del help desk.

Incluye encapsulación de datos (propiedades), flag ``es_demo`` para
aislar datos de demostración, y subclases por rol (UsuarioFinal,
Tecnico, Administrador) que especializan permisos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.models.enums import Rol


@dataclass
class Usuario:
    """Usuario del sistema de soporte (cuenta real o demo)."""

    _nombre: str
    _email: str
    _telefono: str = ""
    _password_hash: str = ""
    _rol: Rol = Rol.USUARIO
    _activo: bool = True
    _es_demo: bool = False
    _id: Optional[int] = None
    _fecha_alta: Optional[str] = None

    def __post_init__(self) -> None:
        if not self._nombre.strip():
            raise ValueError("El nombre no puede estar vacío")
        if "@" not in self._email:
            raise ValueError("Email inválido")
        if isinstance(self._rol, str):
            self._rol = Rol(self._rol)

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
        if not value.strip():
            raise ValueError("El nombre no puede estar vacío")
        self._nombre = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if "@" not in value:
            raise ValueError("Email inválido")
        self._email = value.strip().lower()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, value: str) -> None:
        self._telefono = value or ""

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @password_hash.setter
    def password_hash(self, value: str) -> None:
        self._password_hash = value

    @property
    def rol(self) -> Rol:
        return self._rol

    @property
    def activo(self) -> bool:
        return self._activo

    @activo.setter
    def activo(self, value: bool) -> None:
        self._activo = bool(value)

    @property
    def es_demo(self) -> bool:
        return self._es_demo

    @es_demo.setter
    def es_demo(self, value: bool) -> None:
        self._es_demo = bool(value)

    @property
    def fecha_alta(self) -> Optional[str]:
        return self._fecha_alta

    def es_tecnico(self) -> bool:
        return self._rol in (Rol.TECNICO, Rol.ADMINISTRADOR)

    def es_admin(self) -> bool:
        return self._rol == Rol.ADMINISTRADOR

    def puede_ver_panel_tecnico(self) -> bool:
        return self.es_tecnico()

    def __str__(self) -> str:
        return f"{self._nombre} <{self._email}> [{self._rol.etiqueta}]"


@dataclass
class Tecnico(Usuario):
    """Técnico de soporte: puede gestionar incidencias e intervenciones."""

    _especialidad: str = field(default="General", kw_only=True)

    def __post_init__(self) -> None:
        self._rol = Rol.TECNICO
        super().__post_init__()

    @property
    def especialidad(self) -> str:
        return self._especialidad

    @especialidad.setter
    def especialidad(self, value: str) -> None:
        self._especialidad = value or "General"


@dataclass
class Administrador(Usuario):
    """Administrador del sistema con acceso completo."""

    def __post_init__(self) -> None:
        self._rol = Rol.ADMINISTRADOR
        super().__post_init__()


def usuario_desde_fila(row) -> Usuario:
    """Factory: siempre Usuario base (el rol discrimina permisos)."""
    data = dict(row)
    return Usuario(
        _id=data["id"],
        _nombre=data["nombre"],
        _email=data["email"],
        _telefono=data.get("telefono") or "",
        _password_hash=data["password_hash"],
        _rol=Rol(data["rol"]),
        _activo=bool(data.get("activo", 1)),
        _es_demo=bool(data.get("es_demo", 0)),
        _fecha_alta=data.get("fecha_alta"),
    )
