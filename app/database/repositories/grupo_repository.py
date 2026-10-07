"""
Repositorio de grupos de soporte y pertenencia de técnicos.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.grupo import GrupoSoporte, grupo_desde_fila
from app.models.usuario import Usuario, usuario_desde_fila


class GrupoRepository:
    """CRUD de ``grupos_soporte`` y ``tecnico_grupos``."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, grupo: GrupoSoporte) -> int:
        return self._db.execute(
            """
            INSERT INTO grupos_soporte (codigo, nombre, descripcion, activo)
            VALUES (?, ?, ?, ?)
            """,
            (
                grupo.codigo,
                grupo.nombre,
                grupo.descripcion,
                1 if grupo.activo else 0,
            ),
            lastrowid=True,
        )

    def upsert_por_codigo(
        self, codigo: str, nombre: str, descripcion: str = ""
    ) -> int:
        row = self.obtener_por_codigo(codigo)
        if row:
            self._db.execute(
                """
                UPDATE grupos_soporte
                SET nombre = ?, descripcion = ?, activo = 1
                WHERE id = ?
                """,
                (nombre, descripcion, row.id),
            )
            return row.id  # type: ignore[return-value]
        return self.crear(
            GrupoSoporte(
                _codigo=codigo, _nombre=nombre, _descripcion=descripcion
            )
        )

    def obtener_por_id(self, grupo_id: int) -> Optional[GrupoSoporte]:
        row = self._db.fetchone(
            "SELECT * FROM grupos_soporte WHERE id = ?", (grupo_id,)
        )
        if not row:
            return None
        g = grupo_desde_fila(row)
        g._miembros_ids = self.ids_tecnicos(grupo_id)
        return g

    def obtener_por_codigo(self, codigo: str) -> Optional[GrupoSoporte]:
        row = self._db.fetchone(
            "SELECT * FROM grupos_soporte WHERE codigo = ?", (codigo,)
        )
        if not row:
            return None
        g = grupo_desde_fila(row)
        g._miembros_ids = self.ids_tecnicos(g.id)  # type: ignore[arg-type]
        return g

    def listar(self, solo_activos: bool = True) -> list[GrupoSoporte]:
        sql = "SELECT * FROM grupos_soporte"
        params: list = []
        if solo_activos:
            sql += " WHERE activo = 1"
        sql += " ORDER BY nombre"
        out: list[GrupoSoporte] = []
        for row in self._db.fetchall(sql, params):
            g = grupo_desde_fila(row)
            g._miembros_ids = self.ids_tecnicos(g.id)  # type: ignore[arg-type]
            out.append(g)
        return out

    def ids_tecnicos(self, grupo_id: int) -> list[int]:
        rows = self._db.fetchall(
            "SELECT usuario_id FROM tecnico_grupos WHERE grupo_id = ?",
            (grupo_id,),
        )
        return [int(r["usuario_id"]) for r in rows]

    def grupos_de_usuario(self, usuario_id: int) -> list[GrupoSoporte]:
        rows = self._db.fetchall(
            """
            SELECT g.*
            FROM grupos_soporte g
            JOIN tecnico_grupos tg ON tg.grupo_id = g.id
            WHERE tg.usuario_id = ?
            ORDER BY g.nombre
            """,
            (usuario_id,),
        )
        return [grupo_desde_fila(r) for r in rows]

    def ids_grupos_de_usuario(self, usuario_id: int) -> list[int]:
        rows = self._db.fetchall(
            "SELECT grupo_id FROM tecnico_grupos WHERE usuario_id = ?",
            (usuario_id,),
        )
        return [int(r["grupo_id"]) for r in rows]

    def set_grupos_usuario(self, usuario_id: int, grupo_ids: list[int]) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "DELETE FROM tecnico_grupos WHERE usuario_id = ?", (usuario_id,)
            )
            for gid in grupo_ids:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO tecnico_grupos (usuario_id, grupo_id)
                    VALUES (?, ?)
                    """,
                    (usuario_id, gid),
                )

    def anadir_miembro(self, grupo_id: int, usuario_id: int) -> None:
        self._db.execute(
            """
            INSERT OR IGNORE INTO tecnico_grupos (usuario_id, grupo_id)
            VALUES (?, ?)
            """,
            (usuario_id, grupo_id),
        )

    def tecnicos_del_grupo(
        self,
        grupo_id: int,
        *,
        es_demo: Optional[bool] = None,
        solo_activos: bool = True,
    ) -> list[Usuario]:
        sql = """
            SELECT u.*
            FROM usuarios u
            JOIN tecnico_grupos tg ON tg.usuario_id = u.id
            WHERE tg.grupo_id = ?
              AND u.rol IN ('tecnico', 'administrador')
        """
        params: list = [grupo_id]
        if solo_activos:
            sql += " AND u.activo = 1"
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY u.nombre"
        return [usuario_desde_fila(r) for r in self._db.fetchall(sql, params)]
