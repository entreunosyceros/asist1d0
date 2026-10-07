"""
Servicio de base de conocimiento.
"""

from __future__ import annotations

from typing import Optional

from app.database.repositories.knowledge_repository import KnowledgeRepository
from app.models.audit import AuditAction, AuditEntity
from app.models.knowledge import KnowledgeArticle
from app.services.audit_service import AuditService


class KnowledgeService:
    """Consulta, sugerencias y mantenimiento de artículos."""

    def __init__(
        self,
        repo: KnowledgeRepository,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo
        self._audit = audit

    def listar(
        self,
        *,
        solo_activos: bool = True,
        categoria_codigo: Optional[str] = None,
        texto: Optional[str] = None,
        es_demo: Optional[bool] = None,
    ) -> list[KnowledgeArticle]:
        return self._repo.listar(
            solo_activos=solo_activos,
            categoria_codigo=categoria_codigo,
            texto=texto,
            es_demo=es_demo,
        )

    def obtener(self, article_id: int) -> Optional[KnowledgeArticle]:
        return self._repo.obtener_por_id(article_id)

    def sugerir_para_categoria(
        self, categoria_codigo: str, *, limite: int = 6
    ) -> list[KnowledgeArticle]:
        return self._repo.sugerir_por_categoria(categoria_codigo, limite=limite)

    def crear(
        self,
        titulo: str,
        contenido: str,
        *,
        resumen: str = "",
        categoria_codigo: str = "",
        tags: str = "",
        es_demo: bool = False,
        actor_id: Optional[int] = None,
    ) -> KnowledgeArticle:
        art = KnowledgeArticle(
            _titulo=titulo,
            _contenido=contenido,
            _resumen=resumen,
            _categoria_codigo=categoria_codigo,
            _tags=tags,
            _es_demo=es_demo,
        )
        art.id = self._repo.crear(art)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CREAR,
                AuditEntity.ARTICULO,
                art.id,
                f"Creó artículo KB #{art.id}: {art.titulo}",
            )
        return art

    def actualizar(
        self, article: KnowledgeArticle, *, actor_id: Optional[int] = None
    ) -> KnowledgeArticle:
        self._repo.actualizar(article)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.ARTICULO,
                article.id,
                f"Actualizó artículo KB #{article.id}: {article.titulo}",
            )
        return article

    def eliminar(
        self, article_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        art = self._repo.obtener_por_id(article_id)
        self._repo.eliminar(article_id)
        if self._audit and art:
            self._audit.registrar(
                actor_id,
                AuditAction.ELIMINAR,
                AuditEntity.ARTICULO,
                article_id,
                f"Eliminó artículo KB #{article_id}: {art.titulo}",
            )
