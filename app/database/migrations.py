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

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE SET NULL
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)"
    )

    # Categorías planas legacy → códigos jerárquicos del catálogo.
    for antiguo, nuevo in (
        ("Red", "Red/WiFi"),
        ("Hardware", "Hardware/PC"),
        ("Software", "Software/Aplicaciones"),
        ("Impresora", "Hardware/Impresora"),
    ):
        db.execute(
            "UPDATE incidencias SET categoria = ? WHERE categoria = ?",
            (nuevo, antiguo),
        )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS grupos_soporte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tecnico_grupos (
            usuario_id INTEGER NOT NULL,
            grupo_id INTEGER NOT NULL,
            PRIMARY KEY (usuario_id, grupo_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (grupo_id) REFERENCES grupos_soporte(id) ON DELETE CASCADE
        )
        """
    )
    if "grupo_id" not in _columnas(db, "incidencias"):
        db.execute("ALTER TABLE incidencias ADD COLUMN grupo_id INTEGER")
    db.execute("CREATE INDEX IF NOT EXISTS idx_incidencias_grupo ON incidencias(grupo_id)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tecnico_grupos_usuario ON tecnico_grupos(usuario_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tecnico_grupos_grupo ON tecnico_grupos(grupo_id)"
    )

    from app.models.grupo import GRUPOS_CANONICOS

    for codigo, nombre, descripcion in GRUPOS_CANONICOS:
        row = db.fetchone(
            "SELECT id FROM grupos_soporte WHERE codigo = ?", (codigo,)
        )
        if row:
            db.execute(
                """
                UPDATE grupos_soporte
                SET nombre = ?, descripcion = ?, activo = 1
                WHERE id = ?
                """,
                (nombre, descripcion, row["id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO grupos_soporte (codigo, nombre, descripcion, activo)
                VALUES (?, ?, ?, 1)
                """,
                (codigo, nombre, descripcion),
            )

    # Alias legacy del catálogo textual → grupos reales.
    for legacy, codigo in (
        ("soporte_red", "redes"),
        ("soporte_identidad", "sistemas"),
        ("soporte_general", "sistemas"),
    ):
        legacy_row = db.fetchone(
            "SELECT id FROM grupos_soporte WHERE codigo = ?", (legacy,)
        )
        if legacy_row:
            # Fusionar si se creó por error; las incidencias apuntan por id.
            canon = db.fetchone(
                "SELECT id FROM grupos_soporte WHERE codigo = ?", (codigo,)
            )
            if canon:
                db.execute(
                    "UPDATE incidencias SET grupo_id = ? WHERE grupo_id = ?",
                    (canon["id"], legacy_row["id"]),
                )
                db.execute(
                    """
                    INSERT OR IGNORE INTO tecnico_grupos (usuario_id, grupo_id)
                    SELECT usuario_id, ? FROM tecnico_grupos WHERE grupo_id = ?
                    """,
                    (canon["id"], legacy_row["id"]),
                )
                db.execute(
                    "DELETE FROM tecnico_grupos WHERE grupo_id = ?",
                    (legacy_row["id"],),
                )
                db.execute(
                    "DELETE FROM grupos_soporte WHERE id = ?", (legacy_row["id"],)
                )

    # Técnicos/admins demo sin grupo → todos los grupos canónicos.
    for row in db.fetchall(
        """
        SELECT u.id
        FROM usuarios u
        WHERE u.rol IN ('tecnico', 'administrador')
          AND u.activo = 1
          AND u.email LIKE '%@asist1d0.local'
          AND NOT EXISTS (
              SELECT 1 FROM tecnico_grupos tg WHERE tg.usuario_id = u.id
          )
        """
    ):
        for g in db.fetchall("SELECT id FROM grupos_soporte WHERE activo = 1"):
            db.execute(
                """
                INSERT OR IGNORE INTO tecnico_grupos (usuario_id, grupo_id)
                VALUES (?, ?)
                """,
                (row["id"], g["id"]),
            )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            resumen TEXT NOT NULL DEFAULT '',
            contenido TEXT NOT NULL,
            categoria_codigo TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1,
            es_demo INTEGER NOT NULL DEFAULT 0,
            fecha_creacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            fecha_actualizacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_kb_categoria ON knowledge_articles(categoria_codigo)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_kb_activo ON knowledge_articles(activo)")

    from app.database.seed_knowledge import ensure_knowledge_articles

    ensure_knowledge_articles(db)

    # Especificaciones de equipo + relaciones inventario.
    for col, ddl in (
        ("cpu", "ALTER TABLE equipos ADD COLUMN cpu TEXT NOT NULL DEFAULT ''"),
        ("ram_gb", "ALTER TABLE equipos ADD COLUMN ram_gb INTEGER NOT NULL DEFAULT 0"),
        (
            "almacenamiento",
            "ALTER TABLE equipos ADD COLUMN almacenamiento TEXT NOT NULL DEFAULT ''",
        ),
        ("gpu", "ALTER TABLE equipos ADD COLUMN gpu TEXT NOT NULL DEFAULT ''"),
    ):
        if col not in _columnas(db, "equipos"):
            db.execute(ddl)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS equipo_componentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            componente_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
            notas TEXT NOT NULL DEFAULT '',
            fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (equipo_id) REFERENCES equipos(id) ON DELETE CASCADE,
            FOREIGN KEY (componente_id) REFERENCES componentes(id) ON DELETE RESTRICT
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS equipo_software (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            version TEXT NOT NULL DEFAULT '',
            licencia TEXT NOT NULL DEFAULT '',
            fecha_instalacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (equipo_id) REFERENCES equipos(id) ON DELETE CASCADE
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS equipo_reparaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            tecnico_id INTEGER,
            incidencia_id INTEGER,
            coste REAL NOT NULL DEFAULT 0 CHECK (coste >= 0),
            fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (equipo_id) REFERENCES equipos(id) ON DELETE CASCADE,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE SET NULL,
            FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE SET NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_equipo_componentes_equipo ON equipo_componentes(equipo_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_equipo_software_equipo ON equipo_software(equipo_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_equipo_reparaciones_equipo ON equipo_reparaciones(equipo_id)"
    )

    from app.database.seed_equipo_detalle import ensure_equipo_detalle
    from app.database.seed_dashboard import ensure_dashboard_seed

    ensure_equipo_detalle(db)
    ensure_dashboard_seed(db)
