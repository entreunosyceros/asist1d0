"""
Búsqueda global multi-entidad.

Consulta en paralelo incidencias, equipos, usuarios, comentarios y artículos
de conocimiento, respetando el ámbito demo/real y el rol de la sesión.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.database.connection import DatabaseConnection


@dataclass
class SearchHit:
    """Un resultado navegable."""

    kind: str  # incidencia | equipo | usuario | comentario | articulo
    entity_id: int
    title: str
    subtitle: str = ""


@dataclass
class GlobalSearchResults:
    """Resultados agrupados por tipo de entidad."""

    query: str
    incidencias: list[SearchHit] = field(default_factory=list)
    equipos: list[SearchHit] = field(default_factory=list)
    usuarios: list[SearchHit] = field(default_factory=list)
    comentarios: list[SearchHit] = field(default_factory=list)
    articulos: list[SearchHit] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.incidencias)
            + len(self.equipos)
            + len(self.usuarios)
            + len(self.comentarios)
            + len(self.articulos)
        )

    def flat(self) -> list[SearchHit]:
        """Orden de navegación con flechas / Enter."""
        return [
            *self.incidencias,
            *self.equipos,
            *self.usuarios,
            *self.comentarios,
            *self.articulos,
        ]


_INC_RE = re.compile(r"^INC-?0*(\d+)$", re.IGNORECASE)
_PC_RE = re.compile(r"^PC-?0*(\d+)$", re.IGNORECASE)


class SearchService:
    """Búsqueda unificada sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def buscar(
        self,
        query: str,
        *,
        es_demo: Optional[bool] = None,
        usuario_id: Optional[int] = None,
        incluir_usuarios: bool = True,
        limite: int = 6,
    ) -> GlobalSearchResults:
        q = (query or "").strip()
        out = GlobalSearchResults(query=q)
        if len(q) < 2 and not q.isdigit():
            return out

        lim = max(1, min(limite, 20))
        like = f"%{q}%"
        inc_id = _parse_code(_INC_RE, q)
        pc_id = _parse_code(_PC_RE, q)

        out.incidencias = self._incidencias(
            like, inc_id, es_demo=es_demo, usuario_id=usuario_id, limite=lim
        )
        out.equipos = self._equipos(
            like, pc_id, es_demo=es_demo, usuario_id=usuario_id, limite=lim
        )
        if incluir_usuarios:
            out.usuarios = self._usuarios(like, es_demo=es_demo, limite=lim)
        out.comentarios = self._comentarios(
            like, es_demo=es_demo, usuario_id=usuario_id, limite=lim
        )
        out.articulos = self._articulos(like, limite=lim)
        return out

    def _demo_clause(
        self, alias: str, es_demo: Optional[bool], params: list
    ) -> str:
        if es_demo is None:
            return ""
        params.append(1 if es_demo else 0)
        return f" AND {alias}.es_demo = ?"

    def _incidencias(
        self,
        like: str,
        exact_id: Optional[int],
        *,
        es_demo: Optional[bool],
        usuario_id: Optional[int],
        limite: int,
    ) -> list[SearchHit]:
        params: list = []
        sql = """
            SELECT i.id, i.titulo, i.estado, i.prioridad, i.categoria
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1
        """
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        sql += self._demo_clause("u", es_demo, params)

        if exact_id is not None:
            sql += " AND i.id = ?"
            params.append(exact_id)
        else:
            sql += """
                AND (
                    i.titulo LIKE ?
                    OR IFNULL(i.descripcion, '') LIKE ?
                    OR IFNULL(i.categoria, '') LIKE ?
                    OR printf('INC-%05d', i.id) LIKE ?
                )
            """
            params.extend([like, like, like, like])
        sql += " ORDER BY i.id DESC LIMIT ?"
        params.append(limite)

        hits = []
        for r in self._db.fetchall(sql, params):
            codigo = f"INC-{int(r['id']):05d}"
            hits.append(
                SearchHit(
                    kind="incidencia",
                    entity_id=int(r["id"]),
                    title=f"{codigo} · {r['titulo']}",
                    subtitle=f"{r['estado']} · {r['prioridad']} · {r['categoria'] or '—'}",
                )
            )
        return hits

    def _equipos(
        self,
        like: str,
        exact_id: Optional[int],
        *,
        es_demo: Optional[bool],
        usuario_id: Optional[int],
        limite: int,
    ) -> list[SearchHit]:
        params: list = []
        sql = """
            SELECT DISTINCT e.id, e.marca, e.modelo, e.numero_serie,
                   e.cpu, e.almacenamiento, e.gpu, e.sistema_operativo,
                   u.nombre AS usuario_nombre
            FROM equipos e
            JOIN usuarios u ON u.id = e.usuario_id
            LEFT JOIN equipo_componentes ec ON ec.equipo_id = e.id
            LEFT JOIN componentes c ON c.id = ec.componente_id
            LEFT JOIN equipo_software es ON es.equipo_id = e.id
            WHERE 1=1
        """
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        sql += self._demo_clause("u", es_demo, params)

        if exact_id is not None:
            sql += " AND e.id = ?"
            params.append(exact_id)
        else:
            sql += """
                AND (
                    e.marca LIKE ?
                    OR e.modelo LIKE ?
                    OR e.numero_serie LIKE ?
                    OR IFNULL(e.cpu, '') LIKE ?
                    OR IFNULL(e.almacenamiento, '') LIKE ?
                    OR IFNULL(e.gpu, '') LIKE ?
                    OR IFNULL(e.sistema_operativo, '') LIKE ?
                    OR printf('PC-%03d', e.id) LIKE ?
                    OR IFNULL(c.nombre, '') LIKE ?
                    OR IFNULL(es.nombre, '') LIKE ?
                )
            """
            params.extend([like] * 10)
        sql += " ORDER BY e.id LIMIT ?"
        params.append(limite)

        hits = []
        for r in self._db.fetchall(sql, params):
            eid = int(r["id"])
            codigo = f"PC-{eid:03d}"
            hits.append(
                SearchHit(
                    kind="equipo",
                    entity_id=eid,
                    title=f"{codigo} · {r['marca']} {r['modelo']}",
                    subtitle=f"S/N {r['numero_serie']} · {r['usuario_nombre'] or '—'}",
                )
            )
        return hits

    def _usuarios(
        self,
        like: str,
        *,
        es_demo: Optional[bool],
        limite: int,
    ) -> list[SearchHit]:
        params: list = []
        sql = """
            SELECT id, nombre, email, rol
            FROM usuarios
            WHERE (nombre LIKE ? OR email LIKE ? OR IFNULL(telefono, '') LIKE ?)
        """
        params.extend([like, like, like])
        if es_demo is not None:
            # En sesión demo el admin ve todos; el técnico normalmente demo.
            # La UI decide incluir_usuarios; aquí filtramos por ámbito si se pide.
            sql += " AND es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY nombre COLLATE NOCASE LIMIT ?"
        params.append(limite)

        return [
            SearchHit(
                kind="usuario",
                entity_id=int(r["id"]),
                title=str(r["nombre"]),
                subtitle=f"{r['email']} · {r['rol']}",
            )
            for r in self._db.fetchall(sql, params)
        ]

    def _comentarios(
        self,
        like: str,
        *,
        es_demo: Optional[bool],
        usuario_id: Optional[int],
        limite: int,
    ) -> list[SearchHit]:
        params: list = []
        sql = """
            SELECT c.id, c.texto, c.incidencia_id, c.fecha,
                   u.nombre AS autor,
                   i.titulo AS incidencia_titulo
            FROM comentarios c
            JOIN usuarios u ON u.id = c.usuario_id
            JOIN incidencias i ON i.id = c.incidencia_id
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios du ON du.id = e.usuario_id
            WHERE c.texto LIKE ?
        """
        params.append(like)
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        sql += self._demo_clause("du", es_demo, params)
        sql += " ORDER BY c.fecha DESC LIMIT ?"
        params.append(limite)

        hits = []
        for r in self._db.fetchall(sql, params):
            texto = (r["texto"] or "").strip().replace("\n", " ")
            if len(texto) > 72:
                texto = texto[:69] + "…"
            codigo = f"INC-{int(r['incidencia_id']):05d}"
            hits.append(
                SearchHit(
                    kind="comentario",
                    entity_id=int(r["incidencia_id"]),
                    title=texto,
                    subtitle=f"{r['autor']} · {codigo} · {(r['fecha'] or '')[:16]}",
                )
            )
        return hits

    def _articulos(self, like: str, *, limite: int) -> list[SearchHit]:
        rows = self._db.fetchall(
            """
            SELECT id, titulo, resumen, categoria_codigo
            FROM knowledge_articles
            WHERE activo = 1
              AND (
                    titulo LIKE ?
                 OR resumen LIKE ?
                 OR contenido LIKE ?
                 OR tags LIKE ?
                 OR categoria_codigo LIKE ?
              )
            ORDER BY titulo COLLATE NOCASE
            LIMIT ?
            """,
            (like, like, like, like, like, limite),
        )
        hits = []
        for r in rows:
            sub = r["categoria_codigo"] or "Sin categoría"
            if r["resumen"]:
                preview = str(r["resumen"]).strip()
                if len(preview) > 60:
                    preview = preview[:57] + "…"
                sub = f"{sub} · {preview}"
            hits.append(
                SearchHit(
                    kind="articulo",
                    entity_id=int(r["id"]),
                    title=str(r["titulo"]),
                    subtitle=sub,
                )
            )
        return hits


def _parse_code(pattern: re.Pattern[str], query: str) -> Optional[int]:
    m = pattern.match(query.strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None
