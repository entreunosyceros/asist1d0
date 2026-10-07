"""
Modelo de entrada de auditoría global (``audit_log``).

Complementa el historial por ticket: aquí se registra trazabilidad
transversal (usuarios, equipos, stock, incidencias, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AuditAction(str, Enum):
    CREAR = "crear"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"
    ASIGNAR = "asignar"
    CAMBIAR_ESTADO = "cambiar_estado"
    COMENTAR = "comentar"
    ADJUNTAR = "adjuntar"
    USAR_REPUESTO = "usar_repuesto"
    CONFIRMAR = "confirmar"
    REABRIR = "reabrir"
    LOGIN = "login"


class AuditEntity(str, Enum):
    USUARIO = "usuario"
    INCIDENCIA = "incidencia"
    EQUIPO = "equipo"
    COMPONENTE = "componente"
    COMENTARIO = "comentario"
    ADJUNTO = "adjunto"
    ARTICULO = "articulo"


@dataclass
class AuditEntry:
    """Registro de una acción auditada."""

    _action: str
    _entity_type: str
    _entity_id: Optional[int] = None
    _user_id: Optional[int] = None
    _details: str = ""
    _ip_address: Optional[str] = None
    _id: Optional[int] = None
    _timestamp: Optional[str] = None
    _usuario_nombre: Optional[str] = field(default=None, repr=False)
    _usuario_rol: Optional[str] = field(default=None, repr=False)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def timestamp(self) -> Optional[str]:
        return self._timestamp

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def action(self) -> str:
        return self._action

    @property
    def entity_type(self) -> str:
        return self._entity_type

    @property
    def entity_id(self) -> Optional[int]:
        return self._entity_id

    @property
    def details(self) -> str:
        return self._details

    @property
    def ip_address(self) -> Optional[str]:
        return self._ip_address

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self._usuario_nombre

    @property
    def usuario_rol(self) -> Optional[str]:
        return self._usuario_rol


def audit_desde_fila(row) -> AuditEntry:
    data = dict(row)
    return AuditEntry(
        _id=data["id"],
        _timestamp=data.get("timestamp"),
        _user_id=data.get("user_id"),
        _action=data["action"],
        _entity_type=data["entity_type"],
        _entity_id=data.get("entity_id"),
        _details=data.get("details") or "",
        _ip_address=data.get("ip_address"),
        _usuario_nombre=data.get("usuario_nombre"),
        _usuario_rol=data.get("usuario_rol"),
    )
