"""
Repositorio de componentes / inventario de repuestos.

Incluye operaciones de stock (entrada/consumo) usadas al asociar
piezas a una incidencia.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.componente import Componente, componente_desde_fila


class ComponenteRepository:
    """CRUD y ajuste de stock de la tabla ``componentes``."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, componente: Componente) -> int:
        return self._db.execute(
            """
            INSERT INTO componentes (nombre, stock, precio, descripcion, es_demo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                componente.nombre,
                componente.stock,
                componente.precio,
                componente.descripcion,
                1 if componente.es_demo else 0,
            ),
            lastrowid=True,
        )

    def actualizar(self, componente: Componente) -> None:
        self._db.execute(
            """
            UPDATE componentes
            SET nombre = ?, stock = ?, precio = ?, descripcion = ?, es_demo = ?
            WHERE id = ?
            """,
            (
                componente.nombre,
                componente.stock,
                componente.precio,
                componente.descripcion,
                1 if componente.es_demo else 0,
                componente.id,
            ),
        )

    def eliminar(self, componente_id: int) -> None:
        self._db.execute("DELETE FROM componentes WHERE id = ?", (componente_id,))

    def obtener_por_id(self, componente_id: int) -> Optional[Componente]:
        row = self._db.fetchone(
            "SELECT * FROM componentes WHERE id = ?", (componente_id,)
        )
        return componente_desde_fila(row) if row else None

    def listar(self, es_demo: Optional[bool] = None) -> list[Componente]:
        sql = "SELECT * FROM componentes WHERE 1=1"
        params: list = []
        if es_demo is not None:
            sql += " AND es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY nombre"
        return [componente_desde_fila(r) for r in self._db.fetchall(sql, params)]

    def listar_stock_bajo(
        self, umbral: int = 5, es_demo: Optional[bool] = None
    ) -> list[Componente]:
        sql = "SELECT * FROM componentes WHERE stock <= ?"
        params: list = [umbral]
        if es_demo is not None:
            sql += " AND es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY stock ASC"
        return [componente_desde_fila(r) for r in self._db.fetchall(sql, params)]

    def asociar_a_incidencia(
        self, incidencia_id: int, componente_id: int, cantidad: int = 1
    ) -> None:
        with self._db.transaction() as conn:
            comp = conn.execute(
                "SELECT stock FROM componentes WHERE id = ?", (componente_id,)
            ).fetchone()
            if not comp:
                raise ValueError("Componente no encontrado")
            if comp["stock"] < cantidad:
                raise ValueError("Stock insuficiente")
            conn.execute(
                """
                INSERT INTO incidencia_componentes (incidencia_id, componente_id, cantidad)
                VALUES (?, ?, ?)
                ON CONFLICT(incidencia_id, componente_id) DO UPDATE
                SET cantidad = cantidad + excluded.cantidad
                """,
                (incidencia_id, componente_id, cantidad),
            )
            conn.execute(
                "UPDATE componentes SET stock = stock - ? WHERE id = ?",
                (cantidad, componente_id),
            )

    def listar_por_incidencia(self, incidencia_id: int) -> list[dict]:
        rows = self._db.fetchall(
            """
            SELECT c.id, c.nombre, c.precio, ic.cantidad, ic.fecha
            FROM incidencia_componentes ic
            JOIN componentes c ON c.id = ic.componente_id
            WHERE ic.incidencia_id = ?
            ORDER BY ic.fecha
            """,
            (incidencia_id,),
        )
        return [dict(r) for r in rows]
