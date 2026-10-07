"""
Repositorio de equipos informáticos.

Persiste y consulta la tabla ``equipos``, incluyendo filtros por usuario
y ámbito demo/real.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.equipo import Equipo, equipo_desde_fila


class EquipoRepository:
    """CRUD de la tabla ``equipos``."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, equipo: Equipo) -> int:
        return self._db.execute(
            """
            INSERT INTO equipos (usuario_id, numero_serie, marca, modelo, sistema_operativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                equipo.usuario_id,
                equipo.numero_serie.upper(),
                equipo.marca,
                equipo.modelo,
                equipo.sistema_operativo,
            ),
            lastrowid=True,
        )

    def actualizar(self, equipo: Equipo) -> None:
        self._db.execute(
            """
            UPDATE equipos
            SET usuario_id = ?, numero_serie = ?, marca = ?, modelo = ?, sistema_operativo = ?
            WHERE id = ?
            """,
            (
                equipo.usuario_id,
                equipo.numero_serie.upper(),
                equipo.marca,
                equipo.modelo,
                equipo.sistema_operativo,
                equipo.id,
            ),
        )

    def eliminar(self, equipo_id: int) -> None:
        self._db.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))

    def _base_select(self) -> str:
        return """
            SELECT e.*, u.nombre AS usuario_nombre, u.es_demo AS propietario_demo
            FROM equipos e
            JOIN usuarios u ON u.id = e.usuario_id
        """

    def obtener_por_id(self, equipo_id: int) -> Optional[Equipo]:
        row = self._db.fetchone(
            self._base_select() + " WHERE e.id = ?", (equipo_id,)
        )
        return equipo_desde_fila(row) if row else None

    def listar(
        self,
        usuario_id: Optional[int] = None,
        es_demo: Optional[bool] = None,
    ) -> list[Equipo]:
        sql = self._base_select() + " WHERE 1=1"
        params: list = []
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY e.marca, e.modelo"
        return [equipo_desde_fila(r) for r in self._db.fetchall(sql, params)]

    def contar(
        self,
        usuario_id: Optional[int] = None,
        es_demo: Optional[bool] = None,
    ) -> int:
        sql = """
            SELECT COUNT(*) AS n
            FROM equipos e
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1
        """
        params: list = []
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        row = self._db.fetchone(sql, params)
        return int(row["n"]) if row else 0
