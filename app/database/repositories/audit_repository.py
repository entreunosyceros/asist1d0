"""
Repositorio de auditoría global (``audit_log``).
"""

from __future__ import annotations

from typing import Optional

from app.database.connection import DatabaseConnection
from app.models.audit import AuditEntry, audit_desde_fila


class AuditRepository:
    """Persistencia y consulta del registro de auditoría."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def crear(
        self,
        *,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[int],
        details: str,
        ip_address: Optional[str],
    ) -> int:
        return self._db.execute(
            """
            INSERT INTO audit_log
                (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, entity_type, entity_id, details, ip_address),
            lastrowid=True,
        )

    def listar(
        self,
        *,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        texto: Optional[str] = None,
        limite: int = 500,
    ) -> list[AuditEntry]:
        clauses: list[str] = ["1=1"]
        params: list = []

        if user_id is not None:
            clauses.append("a.user_id = ?")
            params.append(user_id)
        if action:
            clauses.append("a.action = ?")
            params.append(action)
        if entity_type:
            clauses.append("a.entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            clauses.append("a.entity_id = ?")
            params.append(entity_id)
        if desde:
            clauses.append("a.timestamp >= ?")
            params.append(desde)
        if hasta:
            # Incluye el día completo si solo se pasa fecha (YYYY-MM-DD)
            if len(hasta) == 10:
                clauses.append("a.timestamp < datetime(?, '+1 day')")
            else:
                clauses.append("a.timestamp <= ?")
            params.append(hasta)
        if texto:
            clauses.append("a.details LIKE ?")
            params.append(f"%{texto}%")

        where = " AND ".join(clauses)
        params.append(max(1, min(limite, 5000)))
        rows = self._db.fetchall(
            f"""
            SELECT a.*,
                   u.nombre AS usuario_nombre,
                   u.rol AS usuario_rol
            FROM audit_log a
            LEFT JOIN usuarios u ON u.id = a.user_id
            WHERE {where}
            ORDER BY a.timestamp DESC, a.id DESC
            LIMIT ?
            """,
            params,
        )
        return [audit_desde_fila(r) for r in rows]
