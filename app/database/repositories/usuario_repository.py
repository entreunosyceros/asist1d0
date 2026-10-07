"""
Repositorio de usuarios (capa de persistencia SQLite).

Traduce filas SQL al modelo ``Usuario`` y aplica filtros por rol,
actividad y ámbito demo/real.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.enums import Rol
from app.models.usuario import Usuario, usuario_desde_fila


class UsuarioRepository:
    """CRUD de la tabla ``usuarios``."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, usuario: Usuario) -> int:
        return self._db.execute(
            """
            INSERT INTO usuarios
                (nombre, email, telefono, password_hash, rol, activo, es_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario.nombre,
                usuario.email.lower(),
                usuario.telefono,
                usuario.password_hash,
                usuario.rol.value,
                1 if usuario.activo else 0,
                1 if usuario.es_demo else 0,
            ),
            lastrowid=True,
        )

    def actualizar(self, usuario: Usuario) -> None:
        self._db.execute(
            """
            UPDATE usuarios
            SET nombre = ?, email = ?, telefono = ?, password_hash = ?,
                rol = ?, activo = ?, es_demo = ?
            WHERE id = ?
            """,
            (
                usuario.nombre,
                usuario.email.lower(),
                usuario.telefono,
                usuario.password_hash,
                usuario.rol.value,
                1 if usuario.activo else 0,
                1 if usuario.es_demo else 0,
                usuario.id,
            ),
        )

    def eliminar(self, usuario_id: int) -> None:
        self._db.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))

    def obtener_por_id(self, usuario_id: int) -> Optional[Usuario]:
        row = self._db.fetchone("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        return usuario_desde_fila(row) if row else None

    def obtener_por_email(self, email: str) -> Optional[Usuario]:
        row = self._db.fetchone(
            "SELECT * FROM usuarios WHERE email = ?", (email.lower().strip(),)
        )
        return usuario_desde_fila(row) if row else None

    def listar(
        self,
        solo_activos: bool = False,
        rol: Optional[Rol] = None,
        es_demo: Optional[bool] = None,
    ) -> list[Usuario]:
        sql = "SELECT * FROM usuarios WHERE 1=1"
        params: list = []
        if solo_activos:
            sql += " AND activo = 1"
        if rol:
            sql += " AND rol = ?"
            params.append(rol.value)
        if es_demo is not None:
            sql += " AND es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY nombre"
        return [usuario_desde_fila(r) for r in self._db.fetchall(sql, params)]

    def contar(self, es_demo: Optional[bool] = None) -> int:
        sql = "SELECT COUNT(*) AS n FROM usuarios WHERE 1=1"
        params: list = []
        if es_demo is not None:
            sql += " AND es_demo = ?"
            params.append(1 if es_demo else 0)
        row = self._db.fetchone(sql, params)
        return int(row["n"]) if row else 0
