"""
Repositorio de incidencias, intervenciones, historial y consumos.

Centraliza el SQL de tickets: listados filtrados, cambios de estado,
asignación de técnicos y registro de intervenciones/repuestos.
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.enums import EstadoIncidencia, Prioridad
from app.models.incidencia import (
    Adjunto,
    Comentario,
    HistorialEntrada,
    Incidencia,
    Intervencion,
    adjunto_desde_fila,
    comentario_desde_fila,
    historial_desde_fila,
    incidencia_desde_fila,
    intervencion_desde_fila,
)


class IncidenciaRepository:
    """Persistencia de incidencias y entidades relacionadas."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def _base_select(self) -> str:
        return """
            SELECT i.*,
                   (e.marca || ' ' || e.modelo) AS equipo_nombre,
                   e.usuario_id AS usuario_id,
                   u.nombre AS usuario_nombre,
                   u.email AS usuario_email,
                   t.nombre AS tecnico_nombre,
                   g.nombre AS grupo_nombre
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            LEFT JOIN usuarios t ON t.id = i.tecnico_id
            LEFT JOIN grupos_soporte g ON g.id = i.grupo_id
        """

    def crear(self, incidencia: Incidencia) -> int:
        return self._db.execute(
            """
            INSERT INTO incidencias
                (equipo_id, tecnico_id, grupo_id, titulo, descripcion,
                 categoria, estado, prioridad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incidencia.equipo_id,
                incidencia.tecnico_id,
                incidencia.grupo_id,
                incidencia.titulo,
                incidencia.descripcion,
                str(getattr(incidencia.categoria, "value", incidencia.categoria)),
                incidencia.estado.value,
                incidencia.prioridad.value,
            ),
            lastrowid=True,
        )

    def actualizar(self, incidencia: Incidencia) -> None:
        cat = str(getattr(incidencia.categoria, "value", incidencia.categoria))
        if incidencia.estado == EstadoIncidencia.CERRADA:
            self._db.execute(
                """
                UPDATE incidencias
                SET equipo_id = ?, tecnico_id = ?, grupo_id = ?, titulo = ?,
                    descripcion = ?, categoria = ?, estado = ?, prioridad = ?,
                    fecha_cierre = COALESCE(fecha_cierre, datetime('now', 'localtime'))
                WHERE id = ?
                """,
                (
                    incidencia.equipo_id,
                    incidencia.tecnico_id,
                    incidencia.grupo_id,
                    incidencia.titulo,
                    incidencia.descripcion,
                    cat,
                    incidencia.estado.value,
                    incidencia.prioridad.value,
                    incidencia.id,
                ),
            )
        else:
            self._db.execute(
                """
                UPDATE incidencias
                SET equipo_id = ?, tecnico_id = ?, grupo_id = ?, titulo = ?,
                    descripcion = ?, categoria = ?, estado = ?, prioridad = ?,
                    fecha_cierre = NULL
                WHERE id = ?
                """,
                (
                    incidencia.equipo_id,
                    incidencia.tecnico_id,
                    incidencia.grupo_id,
                    incidencia.titulo,
                    incidencia.descripcion,
                    cat,
                    incidencia.estado.value,
                    incidencia.prioridad.value,
                    incidencia.id,
                ),
            )

    def eliminar(self, incidencia_id: int) -> None:
        self._db.execute("DELETE FROM incidencias WHERE id = ?", (incidencia_id,))

    def obtener_por_id(
        self,
        incidencia_id: int,
        con_detalle: bool = True,
        es_demo: Optional[bool] = None,
    ) -> Optional[Incidencia]:
        sql = self._base_select() + " WHERE i.id = ?"
        params: list = [incidencia_id]
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        row = self._db.fetchone(sql, params)
        if not row:
            return None
        inc = incidencia_desde_fila(row)
        if con_detalle:
            inc._intervenciones = self.listar_intervenciones(incidencia_id)
            inc._historial = self.listar_historial(incidencia_id)
            inc._comentarios = self.listar_comentarios(incidencia_id)
            inc._adjuntos = self.listar_adjuntos(incidencia_id)
        return inc

    def listar(
        self,
        *,
        usuario_id: Optional[int] = None,
        tecnico_id: Optional[int] = None,
        equipo_id: Optional[int] = None,
        estado: Optional[EstadoIncidencia] = None,
        prioridad: Optional[Prioridad] = None,
        categoria: Optional[str] = None,
        grupo_id: Optional[int] = None,
        solo_abiertas: bool = False,
        es_demo: Optional[bool] = None,
        texto: Optional[str] = None,
        sin_asignar: bool = False,
    ) -> list[Incidencia]:
        sql = self._base_select() + " WHERE 1=1"
        params: list = []
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        if sin_asignar:
            sql += " AND i.tecnico_id IS NULL"
        elif tecnico_id is not None:
            sql += " AND i.tecnico_id = ?"
            params.append(tecnico_id)
        if grupo_id is not None:
            sql += " AND i.grupo_id = ?"
            params.append(grupo_id)
        if categoria:
            cat = getattr(categoria, "value", categoria)
            # Grupo (Hardware) o hoja (Hardware/Impresora); legacy exacto.
            sql += " AND (i.categoria = ? OR i.categoria LIKE ? OR i.categoria = ?)"
            params.extend([cat, f"{cat}/%", cat.split("/")[-1] if "/" in str(cat) else cat])
        if equipo_id is not None:
            sql += " AND i.equipo_id = ?"
            params.append(equipo_id)
        if estado is not None:
            sql += " AND i.estado = ?"
            params.append(estado.value)
        if prioridad is not None:
            sql += " AND i.prioridad = ?"
            params.append(prioridad.value)
        if solo_abiertas:
            sql += " AND i.estado != 'Cerrada'"
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        if texto:
            q = f"%{texto.strip()}%"
            sql += """
                AND (
                    i.titulo LIKE ?
                    OR IFNULL(i.descripcion, '') LIKE ?
                    OR printf('INC-%05d', i.id) LIKE ?
                    OR (e.marca || ' ' || e.modelo) LIKE ?
                    OR u.nombre LIKE ?
                )
            """
            params.extend([q, q, q, q, q])
        sql += " ORDER BY i.fecha_creacion DESC"
        return [incidencia_desde_fila(r) for r in self._db.fetchall(sql, params)]

    def contar(
        self,
        *,
        usuario_id: Optional[int] = None,
        solo_abiertas: bool = False,
        prioridad: Optional[Prioridad] = None,
        estado: Optional[EstadoIncidencia] = None,
        es_demo: Optional[bool] = None,
    ) -> int:
        sql = """
            SELECT COUNT(*) AS n
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1
        """
        params: list = []
        if usuario_id is not None:
            sql += " AND e.usuario_id = ?"
            params.append(usuario_id)
        if solo_abiertas:
            sql += " AND i.estado != 'Cerrada'"
        if prioridad is not None:
            sql += " AND i.prioridad = ?"
            params.append(prioridad.value)
        if estado is not None:
            sql += " AND i.estado = ?"
            params.append(estado.value)
        if es_demo is not None:
            sql += " AND u.es_demo = ?"
            params.append(1 if es_demo else 0)
        row = self._db.fetchone(sql, params)
        return int(row["n"]) if row else 0

    # --- Intervenciones ---

    def crear_intervencion(self, intervencion: Intervencion) -> int:
        return self._db.execute(
            """
            INSERT INTO intervenciones (incidencia_id, tecnico_id, descripcion)
            VALUES (?, ?, ?)
            """,
            (
                intervencion.incidencia_id,
                intervencion.tecnico_id,
                intervencion.descripcion,
            ),
            lastrowid=True,
        )

    def listar_intervenciones(self, incidencia_id: int) -> list[Intervencion]:
        rows = self._db.fetchall(
            """
            SELECT iv.*, u.nombre AS tecnico_nombre
            FROM intervenciones iv
            JOIN usuarios u ON u.id = iv.tecnico_id
            WHERE iv.incidencia_id = ?
            ORDER BY iv.fecha ASC
            """,
            (incidencia_id,),
        )
        return [intervencion_desde_fila(r) for r in rows]

    def ultimas_intervenciones(
        self, limite: int = 10, es_demo: Optional[bool] = None
    ) -> list[Intervencion]:
        sql = """
            SELECT iv.*, u.nombre AS tecnico_nombre
            FROM intervenciones iv
            JOIN usuarios u ON u.id = iv.tecnico_id
            JOIN incidencias i ON i.id = iv.incidencia_id
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios du ON du.id = e.usuario_id
            WHERE 1=1
        """
        params: list = []
        if es_demo is not None:
            sql += " AND du.es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY iv.fecha DESC LIMIT ?"
        params.append(limite)
        return [intervencion_desde_fila(r) for r in self._db.fetchall(sql, params)]

    # --- Historial ---

    def agregar_historial(
        self,
        incidencia_id: int,
        accion: str,
        usuario_id: Optional[int] = None,
        conn=None,
    ) -> int:
        sql = """
            INSERT INTO historial (incidencia_id, accion, usuario_id)
            VALUES (?, ?, ?)
        """
        params = (incidencia_id, accion, usuario_id)
        if conn is not None:
            cur = conn.execute(sql, params)
            return cur.lastrowid
        return self._db.execute(sql, params, lastrowid=True)

    def crear_comentario(self, comentario: Comentario) -> int:
        return self._db.execute(
            """
            INSERT INTO comentarios (incidencia_id, usuario_id, texto)
            VALUES (?, ?, ?)
            """,
            (comentario.incidencia_id, comentario.usuario_id, comentario.texto),
            lastrowid=True,
        )

    def listar_comentarios(self, incidencia_id: int) -> list[Comentario]:
        rows = self._db.fetchall(
            """
            SELECT c.*, u.nombre AS usuario_nombre
            FROM comentarios c
            JOIN usuarios u ON u.id = c.usuario_id
            WHERE c.incidencia_id = ?
            ORDER BY c.fecha ASC
            """,
            (incidencia_id,),
        )
        return [comentario_desde_fila(r) for r in rows]

    def crear_adjunto(self, adjunto: Adjunto) -> int:
        return self._db.execute(
            """
            INSERT INTO adjuntos
                (incidencia_id, usuario_id, nombre_original, nombre_archivo, tamano)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                adjunto.incidencia_id,
                adjunto.usuario_id,
                adjunto.nombre_original,
                adjunto.nombre_archivo,
                adjunto.tamano,
            ),
            lastrowid=True,
        )

    def listar_adjuntos(self, incidencia_id: int) -> list[Adjunto]:
        rows = self._db.fetchall(
            """
            SELECT a.*, u.nombre AS usuario_nombre
            FROM adjuntos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.incidencia_id = ?
            ORDER BY a.fecha ASC
            """,
            (incidencia_id,),
        )
        return [adjunto_desde_fila(r) for r in rows]

    def obtener_adjunto(self, adjunto_id: int) -> Optional[Adjunto]:
        row = self._db.fetchone(
            """
            SELECT a.*, u.nombre AS usuario_nombre
            FROM adjuntos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.id = ?
            """,
            (adjunto_id,),
        )
        return adjunto_desde_fila(row) if row else None

    def eliminar_adjunto(self, adjunto_id: int) -> None:
        self._db.execute("DELETE FROM adjuntos WHERE id = ?", (adjunto_id,))

    def listar_historial(self, incidencia_id: int) -> list[HistorialEntrada]:
        rows = self._db.fetchall(
            """
            SELECT h.*, u.nombre AS usuario_nombre
            FROM historial h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            WHERE h.incidencia_id = ?
            ORDER BY h.fecha ASC
            """,
            (incidencia_id,),
        )
        return [historial_desde_fila(r) for r in rows]

    def listar_historial_global(
        self, limite: int = 50, es_demo: Optional[bool] = None
    ) -> list[HistorialEntrada]:
        sql = """
            SELECT h.*, u.nombre AS usuario_nombre
            FROM historial h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            JOIN incidencias i ON i.id = h.incidencia_id
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios du ON du.id = e.usuario_id
            WHERE 1=1
        """
        params: list = []
        if es_demo is not None:
            sql += " AND du.es_demo = ?"
            params.append(1 if es_demo else 0)
        sql += " ORDER BY h.fecha DESC LIMIT ?"
        params.append(limite)
        return [historial_desde_fila(r) for r in self._db.fetchall(sql, params)]
