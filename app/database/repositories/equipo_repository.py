"""
Repositorio de equipos y entidades relacionadas.

Persiste ``equipos`` y las tablas hijas de componentes instalados,
software y reparaciones (relaciones SQLite para el inventario físico).
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.equipo import (
    Equipo,
    EquipoComponente,
    EquipoReparacion,
    EquipoSoftware,
    equipo_componente_desde_fila,
    equipo_desde_fila,
    equipo_reparacion_desde_fila,
    equipo_software_desde_fila,
)


class EquipoRepository:
    """CRUD de equipos y su inventario asociado."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(self, equipo: Equipo) -> int:
        return self._db.execute(
            """
            INSERT INTO equipos
                (usuario_id, numero_serie, marca, modelo, sistema_operativo,
                 cpu, ram_gb, almacenamiento, gpu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipo.usuario_id,
                equipo.numero_serie.upper(),
                equipo.marca,
                equipo.modelo,
                equipo.sistema_operativo,
                equipo.cpu,
                equipo.ram_gb,
                equipo.almacenamiento,
                equipo.gpu,
            ),
            lastrowid=True,
        )

    def actualizar(self, equipo: Equipo) -> None:
        self._db.execute(
            """
            UPDATE equipos
            SET usuario_id = ?, numero_serie = ?, marca = ?, modelo = ?,
                sistema_operativo = ?, cpu = ?, ram_gb = ?,
                almacenamiento = ?, gpu = ?
            WHERE id = ?
            """,
            (
                equipo.usuario_id,
                equipo.numero_serie.upper(),
                equipo.marca,
                equipo.modelo,
                equipo.sistema_operativo,
                equipo.cpu,
                equipo.ram_gb,
                equipo.almacenamiento,
                equipo.gpu,
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

    def obtener_por_id(
        self, equipo_id: int, *, con_detalle: bool = False
    ) -> Optional[Equipo]:
        row = self._db.fetchone(
            self._base_select() + " WHERE e.id = ?", (equipo_id,)
        )
        if not row:
            return None
        eq = equipo_desde_fila(row)
        if con_detalle:
            eq._componentes = self.listar_componentes(equipo_id)
            eq._software = self.listar_software(equipo_id)
            eq._reparaciones = self.listar_reparaciones(equipo_id)
        return eq

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

    # --- Componentes instalados ---

    def anadir_componente(self, item: EquipoComponente) -> int:
        return self._db.execute(
            """
            INSERT INTO equipo_componentes
                (equipo_id, componente_id, cantidad, notas)
            VALUES (?, ?, ?, ?)
            """,
            (item.equipo_id, item.componente_id, item.cantidad, item.notas),
            lastrowid=True,
        )

    def listar_componentes(self, equipo_id: int) -> list[EquipoComponente]:
        rows = self._db.fetchall(
            """
            SELECT ec.*, c.nombre AS componente_nombre
            FROM equipo_componentes ec
            JOIN componentes c ON c.id = ec.componente_id
            WHERE ec.equipo_id = ?
            ORDER BY ec.fecha DESC
            """,
            (equipo_id,),
        )
        return [equipo_componente_desde_fila(r) for r in rows]

    def eliminar_componente(self, item_id: int) -> None:
        self._db.execute("DELETE FROM equipo_componentes WHERE id = ?", (item_id,))

    # --- Software ---

    def anadir_software(self, item: EquipoSoftware) -> int:
        return self._db.execute(
            """
            INSERT INTO equipo_software (equipo_id, nombre, version, licencia)
            VALUES (?, ?, ?, ?)
            """,
            (item.equipo_id, item.nombre, item.version, item.licencia),
            lastrowid=True,
        )

    def listar_software(self, equipo_id: int) -> list[EquipoSoftware]:
        rows = self._db.fetchall(
            """
            SELECT * FROM equipo_software
            WHERE equipo_id = ?
            ORDER BY nombre COLLATE NOCASE
            """,
            (equipo_id,),
        )
        return [equipo_software_desde_fila(r) for r in rows]

    def eliminar_software(self, item_id: int) -> None:
        self._db.execute("DELETE FROM equipo_software WHERE id = ?", (item_id,))

    # --- Reparaciones ---

    def anadir_reparacion(self, item: EquipoReparacion) -> int:
        return self._db.execute(
            """
            INSERT INTO equipo_reparaciones
                (equipo_id, descripcion, tecnico_id, incidencia_id, coste)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item.equipo_id,
                item.descripcion,
                item.tecnico_id,
                item.incidencia_id,
                item.coste,
            ),
            lastrowid=True,
        )

    def listar_reparaciones(self, equipo_id: int) -> list[EquipoReparacion]:
        rows = self._db.fetchall(
            """
            SELECT r.*, u.nombre AS tecnico_nombre
            FROM equipo_reparaciones r
            LEFT JOIN usuarios u ON u.id = r.tecnico_id
            WHERE r.equipo_id = ?
            ORDER BY r.fecha DESC
            """,
            (equipo_id,),
        )
        return [equipo_reparacion_desde_fila(r) for r in rows]
