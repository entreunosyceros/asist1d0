"""
Repositorio de artículos de la base de conocimiento.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.knowledge import KnowledgeArticle, article_desde_fila


class KnowledgeRepository:
    """CRUD y búsqueda de ``knowledge_articles``."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, article: KnowledgeArticle) -> int:
        return self._db.execute(
            """
            INSERT INTO knowledge_articles
                (titulo, resumen, contenido, categoria_codigo, tags, activo, es_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.titulo,
                article.resumen,
                article.contenido,
                article.categoria_codigo,
                article.tags,
                1 if article.activo else 0,
                1 if article.es_demo else 0,
            ),
            lastrowid=True,
        )

    def actualizar(self, article: KnowledgeArticle) -> None:
        self._db.execute(
            """
            UPDATE knowledge_articles
            SET titulo = ?, resumen = ?, contenido = ?, categoria_codigo = ?,
                tags = ?, activo = ?,
                fecha_actualizacion = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (
                article.titulo,
                article.resumen,
                article.contenido,
                article.categoria_codigo,
                article.tags,
                1 if article.activo else 0,
                article.id,
            ),
        )

    def eliminar(self, article_id: int) -> None:
        self._db.execute("DELETE FROM knowledge_articles WHERE id = ?", (article_id,))

    def obtener_por_id(self, article_id: int) -> Optional[KnowledgeArticle]:
        row = self._db.fetchone(
            "SELECT * FROM knowledge_articles WHERE id = ?", (article_id,)
        )
        return article_desde_fila(row) if row else None

    def listar(
        self,
        *,
        solo_activos: bool = True,
        categoria_codigo: Optional[str] = None,
        texto: Optional[str] = None,
        es_demo: Optional[bool] = None,
        limite: int = 200,
    ) -> list[KnowledgeArticle]:
        clauses = ["1=1"]
        params: list = []
        if solo_activos:
            clauses.append("activo = 1")
        if categoria_codigo:
            clauses.append(
                "(categoria_codigo = ? OR categoria_codigo LIKE ? OR ? LIKE categoria_codigo || '/%')"
            )
            params.extend(
                [
                    categoria_codigo,
                    f"{categoria_codigo}/%",
                    categoria_codigo,
                ]
            )
        if texto:
            q = f"%{texto.strip()}%"
            clauses.append(
                "(titulo LIKE ? OR resumen LIKE ? OR contenido LIKE ? OR tags LIKE ?)"
            )
            params.extend([q, q, q, q])
        if es_demo is not None:
            clauses.append("es_demo = ?")
            params.append(1 if es_demo else 0)
        where = " AND ".join(clauses)
        params.append(max(1, min(limite, 1000)))
        rows = self._db.fetchall(
            f"""
            SELECT * FROM knowledge_articles
            WHERE {where}
            ORDER BY titulo COLLATE NOCASE
            LIMIT ?
            """,
            params,
        )
        return [article_desde_fila(r) for r in rows]

    def sugerir_por_categoria(
        self, categoria_codigo: str, *, limite: int = 8
    ) -> list[KnowledgeArticle]:
        """Artículos de la hoja, de la familia o genéricos relacionados."""
        codigo = (categoria_codigo or "").strip()
        if not codigo:
            return []
        familia = codigo.split("/", 1)[0] if "/" in codigo else codigo
        rows = self._db.fetchall(
            """
            SELECT * FROM knowledge_articles
            WHERE activo = 1
              AND (
                    categoria_codigo = ?
                 OR categoria_codigo LIKE ?
                 OR categoria_codigo = ?
                 OR (? != '' AND tags LIKE '%' || lower(?) || '%')
              )
            ORDER BY
                CASE
                    WHEN categoria_codigo = ? THEN 0
                    WHEN categoria_codigo LIKE ? THEN 1
                    ELSE 2
                END,
                titulo COLLATE NOCASE
            LIMIT ?
            """,
            (
                codigo,
                f"{familia}/%",
                familia,
                familia.lower(),
                familia.lower(),
                codigo,
                f"{codigo}/%",
                limite,
            ),
        )
        return [article_desde_fila(r) for r in rows]
