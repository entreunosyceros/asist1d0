"""
Datos demo adicionales para poblar el dashboard (métricas y gráficas).

Idempotente: solo inserta si hay pocas incidencias demo.
"""

from __future__ import annotations

from app.auth.password import hash_password
from app.database.connection import DatabaseConnection
from app.models.enums import EstadoIncidencia, Prioridad, Rol


# Título marcador en historial / detección de lote.
_SEED_TAG = "seed-dashboard-v1"

_TICKETS = (
    # dias_atras, horas_abierto (si cerrada), estado, prioridad, categoria, titulo, tecnico_key
    (13, 6, "Cerrada", "Baja", "Software/Aplicaciones", "Outlook lento al abrir", "carlos"),
    (12, 30, "Cerrada", "Media", "Hardware/PC", "Portátil no enciende", "laura"),
    (11, 4, "Cerrada", "Alta", "Red/Internet", "Sin acceso a Internet en planta 2", "pedro"),
    (10, 18, "Cerrada", "Media", "Hardware/Impresora", "Atasco papel sala reuniones", "carlos"),
    (9, 72, "Cerrada", "Baja", "Software/Licencias", "Activación Office pendiente", "laura"),
    (8, 10, "Cerrada", "Crítica", "Red/WiFi", "Caída Wi‑Fi sede norte", "pedro"),
    (7, 20, "Cerrada", "Media", "Hardware/Monitor", "Pantalla parpadea", "carlos"),
    (6, 8, "Cerrada", "Alta", "Software/SO", "Pantallazo azul al arrancar", "laura"),
    (5, 14, "Cerrada", "Media", "Cuenta", "Reset contraseña VPN", "pedro"),
    (4, None, "En reparación", "Alta", "Hardware/PC", "Sobrecalentamiento CPU", "carlos"),
    (4, None, "Abierta", "Media", "Software/Aplicaciones", "Teams no abre cámara", "laura"),
    (3, None, "Pendiente", "Baja", "Hardware/Perifericos", "Ratón inalámbrico falla", "pedro"),
    (3, None, "Abierta", "Crítica", "Red/VPN", "VPN desconecta cada 5 min", "carlos"),
    (2, None, "En reparación", "Media", "Hardware/Impresora", "Impresora de red offline", "laura"),
    (2, None, "Abierta", "Alta", "Software/SO", "Actualización Windows bloqueada", "pedro"),
    (1, None, "Abierta", "Baja", "Otro", "Consulta sobre backup", None),
    (1, None, "En reparación", "Media", "Red/Cableada", "Puerto Ethernet sin link", "carlos"),
    (0, None, "Abierta", "Alta", "Hardware/PC", "Disco al 95% de uso", "laura"),
    (0, None, "Abierta", "Media", "Software/Aplicaciones", "Error al firmar PDF", "pedro"),
    (0, None, "Pendiente", "Alta", "Red/Internet", "DNS interno no resuelve", "carlos"),
)


def ensure_dashboard_seed(db: DatabaseConnection) -> None:
    """Amplía incidencias demo para que las gráficas tengan volumen."""
    row = db.fetchone(
        """
        SELECT COUNT(*) AS n
        FROM incidencias i
        JOIN equipos e ON e.id = i.equipo_id
        JOIN usuarios u ON u.id = e.usuario_id
        WHERE u.es_demo = 1
        """
    )
    already = row and int(row["n"]) >= 20

    # Evitar duplicar el lote si ya se insertó parcialmente.
    tagged = db.fetchone(
        "SELECT COUNT(*) AS n FROM historial WHERE accion LIKE ?",
        (f"%{_SEED_TAG}%",),
    )
    if already or (tagged and int(tagged["n"]) > 0):
        _ensure_demo_comentarios(db)
        return

    users = {
        r["email"]: dict(r)
        for r in db.fetchall("SELECT id, email, nombre, rol FROM usuarios WHERE es_demo = 1")
    }
    if "tecnico@asist1d0.local" not in users or "juan@asist1d0.local" not in users:
        return

    laura = _ensure_tecnico(
        db,
        email="laura@asist1d0.local",
        nombre="Laura Méndez",
        password="laura123",
    )
    pedro = _ensure_tecnico(
        db,
        email="pedro@asist1d0.local",
        nombre="Pedro Ruiz",
        password="pedro123",
    )
    carlos_id = int(users["tecnico@asist1d0.local"]["id"])
    tech_map = {
        "carlos": carlos_id,
        "laura": laura,
        "pedro": pedro,
    }

    # Añadir técnicos a grupos existentes.
    grupo_ids = [int(r["id"]) for r in db.fetchall("SELECT id FROM grupos_soporte")]
    for tid in (laura, pedro, carlos_id):
        for gid in grupo_ids:
            db.execute(
                """
                INSERT OR IGNORE INTO tecnico_grupos (usuario_id, grupo_id)
                VALUES (?, ?)
                """,
                (tid, gid),
            )

    equipos = db.fetchall(
        """
        SELECT e.id
        FROM equipos e
        JOIN usuarios u ON u.id = e.usuario_id
        WHERE u.es_demo = 1
        ORDER BY e.id
        """
    )
    if not equipos:
        return
    eq_ids = [int(r["id"]) for r in equipos]
    juan_id = int(users["juan@asist1d0.local"]["id"])

    for i, spec in enumerate(_TICKETS):
        dias, horas_abierto, estado, prioridad, categoria, titulo, tech_key = spec
        eq_id = eq_ids[i % len(eq_ids)]
        tecnico_id = tech_map.get(tech_key) if tech_key else None
        estado_enum = EstadoIncidencia(estado)
        prio_enum = Prioridad(prioridad)

        new_id = db.execute(
            """
            INSERT INTO incidencias
                (equipo_id, tecnico_id, titulo, descripcion, categoria, estado, prioridad,
                 fecha_creacion, fecha_cierre)
            VALUES (?, ?, ?, ?, ?, ?, ?,
                    datetime('now', 'localtime', ?),
                    ?)
            """,
            (
                eq_id,
                tecnico_id,
                titulo,
                f"Caso demo dashboard ({_SEED_TAG}).",
                categoria,
                estado_enum.value,
                prio_enum.value,
                f"-{dias} days",
                None,
            ),
            lastrowid=True,
        )

        if estado_enum == EstadoIncidencia.CERRADA and horas_abierto is not None:
            db.execute(
                """
                UPDATE incidencias
                SET fecha_cierre = datetime(fecha_creacion, ?)
                WHERE id = ?
                """,
                (f"+{horas_abierto} hours", new_id),
            )

        db.execute(
            """
            INSERT INTO historial (incidencia_id, accion, usuario_id)
            VALUES (?, ?, ?)
            """,
            (new_id, f"Incidencia creada ({_SEED_TAG})", juan_id),
        )

    _ensure_demo_comentarios(db)


def _ensure_demo_comentarios(db: DatabaseConnection) -> None:
    """Comentarios de ejemplo para la búsqueda global."""
    tagged = db.fetchone(
        "SELECT COUNT(*) AS n FROM comentarios WHERE texto LIKE ?",
        (f"%{_SEED_TAG}%",),
    )
    if tagged and int(tagged["n"]) > 0:
        return

    users = {
        r["email"]: int(r["id"])
        for r in db.fetchall("SELECT id, email FROM usuarios WHERE es_demo = 1")
    }
    juan = users.get("juan@asist1d0.local")
    carlos = users.get("tecnico@asist1d0.local")
    if not juan or not carlos:
        return

    inc = db.fetchone(
        """
        SELECT i.id FROM incidencias i
        JOIN equipos e ON e.id = i.equipo_id
        JOIN usuarios u ON u.id = e.usuario_id
        WHERE u.es_demo = 1
        ORDER BY i.id
        LIMIT 1
        """
    )
    if not inc:
        return
    iid = int(inc["id"])
    for autor, texto in (
        (juan, f"Sigue sin detectar redes Wi‑Fi tras reiniciar. ({_SEED_TAG})"),
        (carlos, f"Probaremos otro adaptador SSD/USB y drivers. ({_SEED_TAG})"),
        (juan, f"La impresora de red también falla desde este PC. ({_SEED_TAG})"),
    ):
        db.execute(
            """
            INSERT INTO comentarios (incidencia_id, usuario_id, texto)
            VALUES (?, ?, ?)
            """,
            (iid, autor, texto),
        )


def _ensure_tecnico(
    db: DatabaseConnection, *, email: str, nombre: str, password: str
) -> int:
    row = db.fetchone("SELECT id FROM usuarios WHERE email = ?", (email,))
    if row:
        return int(row["id"])
    return int(
        db.execute(
            """
            INSERT INTO usuarios
                (nombre, email, telefono, password_hash, rol, activo, es_demo)
            VALUES (?, ?, '', ?, ?, 1, 1)
            """,
            (
                nombre,
                email,
                hash_password(password),
                Rol.TECNICO.value,
            ),
            lastrowid=True,
        )
    )
