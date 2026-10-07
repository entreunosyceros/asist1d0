"""
Servicio central de auditoría.

Nunca debe interrumpir el flujo de negocio: los errores de escritura
se capturan y se registran en el logger de la aplicación.
"""

from __future__ import annotations

import logging
from typing import Optional, Union

from app.database.repositories.audit_repository import AuditRepository
from app.models.audit import AuditAction, AuditEntity, AuditEntry

logger = logging.getLogger(__name__)


class AuditService:
    """Registro y consulta de eventos de trazabilidad global."""

    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    def registrar(
        self,
        user_id: Optional[int],
        action: Union[AuditAction, str],
        entity_type: Union[AuditEntity, str],
        entity_id: Optional[int],
        details: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Persiste un evento. Ante fallo solo escribe en log."""
        try:
            action_val = action.value if isinstance(action, AuditAction) else str(action)
            entity_val = (
                entity_type.value if isinstance(entity_type, AuditEntity) else str(entity_type)
            )
            ip = ip_address if ip_address is not None else "desktop"
            self._repo.crear(
                user_id=user_id,
                action=action_val,
                entity_type=entity_val,
                entity_id=entity_id,
                details=details or "",
                ip_address=ip,
            )
        except Exception:
            logger.exception(
                "No se pudo registrar auditoría: %s %s #%s",
                action,
                entity_type,
                entity_id,
            )

    def listar(
        self,
        *,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        texto: Optional[str] = None,
        limite: int = 500,
    ) -> list[AuditEntry]:
        return self._repo.listar(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            desde=desde,
            hasta=hasta,
            texto=texto,
            limite=limite,
        )
