"""
Migraciones ligeras de esquema SQLite.

Permiten actualizar una base ya creada (por ejemplo, añadir la columna
``es_demo``) sin borrar datos ni exigir reinstalar la aplicación.
"""

from __future__ import annotations

from app.database.connection import DatabaseConnection


def _columnas(db: DatabaseConnection, tabla: str) -> set[str]:
    """Nombres de columnas de una tabla (vía PRAGMA table_info)."""
    return {row["name"] for row in db.fetchall(f"PRAGMA table_info({tabla})")}


def migrate_schema(db: DatabaseConnection) -> None:
    """Añade columnas/índices nuevos sin romper bases ya existentes."""
    if "es_demo" not in _columnas(db, "usuarios"):
        db.execute(
            "ALTER TABLE usuarios ADD COLUMN es_demo INTEGER NOT NULL DEFAULT 0"
        )
        db.execute(
            "UPDATE usuarios SET es_demo = 1 WHERE email LIKE '%@asist1d0.local'"
        )

    if "es_demo" not in _columnas(db, "componentes"):
        db.execute(
            "ALTER TABLE componentes ADD COLUMN es_demo INTEGER NOT NULL DEFAULT 0"
        )
        db.execute("UPDATE componentes SET es_demo = 1")

    # Por si la BD antigua tenía cuentas demo sin marcar
    db.execute(
        "UPDATE usuarios SET es_demo = 1 WHERE email LIKE '%@asist1d0.local'"
    )

    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_usuarios_demo ON usuarios(es_demo)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_componentes_demo ON componentes(es_demo)"
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_comentarios_incidencia ON comentarios(incidencia_id)"
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS adjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incidencia_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            nombre_original TEXT NOT NULL,
            nombre_archivo TEXT NOT NULL,
            tamano INTEGER NOT NULL DEFAULT 0 CHECK (tamano >= 0),
            fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_adjuntos_incidencia ON adjuntos(incidencia_id)"
    )

    if "categoria" not in _columnas(db, "incidencias"):
        db.execute(
            "ALTER TABLE incidencias ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Otro'"
        )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_incidencias_categoria ON incidencias(categoria)"
    )
