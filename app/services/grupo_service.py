"""
Servicio de grupos de soporte y membresía de técnicos.
"""

from __future__ import annotations

from typing import Optional

from app.database.repositories.grupo_repository import GrupoRepository
from app.models.grupo import GrupoSoporte
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.models.audit import AuditAction, AuditEntity


class GrupoService:
    """Consulta y mantenimiento de colas de soporte."""

    def __init__(
        self,
        repo: GrupoRepository,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo
        self._audit = audit

    def listar(self, solo_activos: bool = True) -> list[GrupoSoporte]:
        return self._repo.listar(solo_activos=solo_activos)

    def obtener(self, grupo_id: int) -> Optional[GrupoSoporte]:
        return self._repo.obtener_por_id(grupo_id)

    def obtener_por_codigo(self, codigo: str) -> Optional[GrupoSoporte]:
        return self._repo.obtener_por_codigo(codigo)

    def grupos_de_usuario(self, usuario_id: int) -> list[GrupoSoporte]:
        return self._repo.grupos_de_usuario(usuario_id)

    def ids_grupos_de_usuario(self, usuario_id: int) -> list[int]:
        return self._repo.ids_grupos_de_usuario(usuario_id)

    def set_grupos_usuario(
        self,
        usuario_id: int,
        grupo_ids: list[int],
        *,
        actor_id: Optional[int] = None,
    ) -> None:
        self._repo.set_grupos_usuario(usuario_id, grupo_ids)
        if self._audit:
            nombres = []
            for gid in grupo_ids:
                g = self._repo.obtener_por_id(gid)
                if g:
                    nombres.append(g.nombre)
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.USUARIO,
                usuario_id,
                f"Grupos del usuario #{usuario_id}: {', '.join(nombres) or '(ninguno)'}",
            )

    def tecnicos_del_grupo(
        self,
        grupo_id: int,
        *,
        es_demo: Optional[bool] = None,
    ) -> list[Usuario]:
        return self._repo.tecnicos_del_grupo(grupo_id, es_demo=es_demo)

    def anadir_miembro(
        self, grupo_id: int, usuario_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        self._repo.anadir_miembro(grupo_id, usuario_id)
        if self._audit:
            g = self._repo.obtener_por_id(grupo_id)
            self._audit.registrar(
                actor_id,
                AuditAction.ASIGNAR,
                AuditEntity.USUARIO,
                usuario_id,
                f"Añadido al grupo {g.nombre if g else grupo_id}",
            )
