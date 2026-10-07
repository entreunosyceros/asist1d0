"""
Enriquece equipos demo con specs, software, componentes y reparaciones.

Idempotente: solo rellena si el equipo aún no tiene detalle.
"""

from __future__ import annotations

from app.database.connection import DatabaseConnection

# numero_serie → specs + software
_SPECS: dict[str, dict] = {
    "ABC123": {
        "cpu": "Intel i5-12400",
        "ram_gb": 16,
        "almacenamiento": "SSD 512 GB",
        "gpu": "Intel UHD Graphics",
        "software": [
            ("Ubuntu", "24.04", "GPL"),
            ("Firefox", "128", ""),
            ("LibreOffice", "24.2", ""),
        ],
    },
    "XYZ789": {
        "cpu": "Intel i7-1185G7",
        "ram_gb": 32,
        "almacenamiento": "SSD 1 TB",
        "gpu": "Intel Iris Xe",
        "software": [
            ("Windows", "11 Pro", "OEM"),
            ("Microsoft 365", "2024", "suscripción"),
            ("Cisco AnyConnect", "5.1", "corporativa"),
        ],
    },
    "MNO456": {
        "cpu": "AMD Ryzen 5 5500U",
        "ram_gb": 16,
        "almacenamiento": "SSD 256 GB",
        "gpu": "Radeon Graphics",
        "software": [
            ("Ubuntu", "22.04", "GPL"),
            ("Chrome", "stable", ""),
        ],
    },
}


def ensure_equipo_detalle(db: DatabaseConnection) -> None:
    """Aplica specs/software/componentes/reparaciones a equipos conocidos."""
    for serie, data in _SPECS.items():
        row = db.fetchone(
            "SELECT id, cpu, ram_gb FROM equipos WHERE numero_serie = ?",
            (serie,),
        )
        if not row:
            continue
        eq_id = int(row["id"])
        if not (row["cpu"] or "").strip() and int(row["ram_gb"] or 0) == 0:
            db.execute(
                """
                UPDATE equipos
                SET cpu = ?, ram_gb = ?, almacenamiento = ?, gpu = ?
                WHERE id = ?
                """,
                (
                    data["cpu"],
                    data["ram_gb"],
                    data["almacenamiento"],
                    data["gpu"],
                    eq_id,
                ),
            )

        sw_n = db.fetchone(
            "SELECT COUNT(*) AS n FROM equipo_software WHERE equipo_id = ?",
            (eq_id,),
        )
        if sw_n and int(sw_n["n"]) == 0:
            for nombre, version, licencia in data["software"]:
                db.execute(
                    """
                    INSERT INTO equipo_software (equipo_id, nombre, version, licencia)
                    VALUES (?, ?, ?, ?)
                    """,
                    (eq_id, nombre, version, licencia),
                )

        comp_n = db.fetchone(
            "SELECT COUNT(*) AS n FROM equipo_componentes WHERE equipo_id = ?",
            (eq_id,),
        )
        if comp_n and int(comp_n["n"]) == 0:
            # Asocia repuestos existentes del inventario demo si hay.
            for nombre in ("Disco SSD 512GB", "Memoria RAM 8GB DDR4", "Adaptador Wi-Fi USB"):
                c = db.fetchone(
                    "SELECT id FROM componentes WHERE nombre = ?", (nombre,)
                )
                if not c:
                    continue
                db.execute(
                    """
                    INSERT INTO equipo_componentes
                        (equipo_id, componente_id, cantidad, notas)
                    VALUES (?, ?, 1, 'Instalado de fábrica / ampliación')
                    """,
                    (eq_id, c["id"]),
                )
                break  # al menos uno por equipo

        rep_n = db.fetchone(
            "SELECT COUNT(*) AS n FROM equipo_reparaciones WHERE equipo_id = ?",
            (eq_id,),
        )
        if rep_n and int(rep_n["n"]) == 0:
            # Vincula intervenciones históricas si existen.
            iv = db.fetchone(
                """
                SELECT iv.descripcion, iv.tecnico_id, i.id AS incidencia_id
                FROM intervenciones iv
                JOIN incidencias i ON i.id = iv.incidencia_id
                WHERE i.equipo_id = ?
                ORDER BY iv.fecha
                LIMIT 1
                """,
                (eq_id,),
            )
            if iv:
                db.execute(
                    """
                    INSERT INTO equipo_reparaciones
                        (equipo_id, descripcion, tecnico_id, incidencia_id, coste)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (
                        eq_id,
                        iv["descripcion"],
                        iv["tecnico_id"],
                        iv["incidencia_id"],
                    ),
                )
            elif serie == "ABC123":
                tec = db.fetchone(
                    "SELECT id FROM usuarios WHERE email = 'tecnico@asist1d0.local'"
                )
                db.execute(
                    """
                    INSERT INTO equipo_reparaciones
                        (equipo_id, descripcion, tecnico_id, coste)
                    VALUES (?, ?, ?, 24.90)
                    """,
                    (
                        eq_id,
                        "Sustitución de adaptador Wi‑Fi USB",
                        tec["id"] if tec else None,
                    ),
                )
