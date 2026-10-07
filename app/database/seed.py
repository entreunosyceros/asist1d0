"""
Datos de demostración para el primer arranque.

Solo se ejecuta si la tabla de usuarios está vacía. Crea cuentas
``*@asist1d0.local``, equipos, incidencias e inventario demo.
"""

from __future__ import annotations

from app.auth.password import hash_password
from app.database.connection import DatabaseConnection
from app.database.repositories import (
    ComponenteRepository,
    EquipoRepository,
    GrupoRepository,
    IncidenciaRepository,
    UsuarioRepository,
)
from app.models.componente import Componente
from app.models.enums import EstadoIncidencia, Prioridad, Rol
from app.models.equipo import Equipo
from app.models.incidencia import Incidencia, Intervencion
from app.models.usuario import Usuario


def needs_seed(db: DatabaseConnection) -> bool:
    """True si aún no hay usuarios (base recién creada)."""
    row = db.fetchone("SELECT COUNT(*) AS n FROM usuarios")
    return not row or int(row["n"]) == 0


def seed_database(db: DatabaseConnection) -> None:
    """Carga usuarios, equipos, incidencias y componentes de ejemplo."""

    if not needs_seed(db):
        return

    usuarios = UsuarioRepository(db)
    equipos = EquipoRepository(db)
    incidencias = IncidenciaRepository(db)
    componentes = ComponenteRepository(db)

    admin = Usuario(
        _nombre="Ana Admin",
        _email="admin@asist1d0.local",
        _telefono="600111222",
        _password_hash=hash_password("admin123"),
        _rol=Rol.ADMINISTRADOR,
        _es_demo=True,
    )
    admin.id = usuarios.crear(admin)

    tecnico = Usuario(
        _nombre="Carlos Técnico",
        _email="tecnico@asist1d0.local",
        _telefono="600333444",
        _password_hash=hash_password("tecnico123"),
        _rol=Rol.TECNICO,
        _es_demo=True,
    )
    tecnico.id = usuarios.crear(tecnico)

    juan = Usuario(
        _nombre="Juan Pérez",
        _email="juan@asist1d0.local",
        _telefono="600555666",
        _password_hash=hash_password("juan123"),
        _rol=Rol.USUARIO,
        _es_demo=True,
    )
    juan.id = usuarios.crear(juan)

    maria = Usuario(
        _nombre="María López",
        _email="maria@asist1d0.local",
        _telefono="600777888",
        _password_hash=hash_password("maria123"),
        _rol=Rol.USUARIO,
        _es_demo=True,
    )
    maria.id = usuarios.crear(maria)

    assert juan.id and tecnico.id and maria.id and admin.id

    grupos = GrupoRepository(db)
    grupo_ids = [g.id for g in grupos.listar() if g.id is not None]
    # Admin y técnico demo en todos los grupos.
    for uid in (admin.id, tecnico.id):
        grupos.set_grupos_usuario(uid, grupo_ids)

    eq1 = Equipo(
        _usuario_id=juan.id,
        _numero_serie="ABC123",
        _marca="HP",
        _modelo="ProBook 450",
        _sistema_operativo="Ubuntu 24.04",
        _cpu="Intel i5-12400",
        _ram_gb=16,
        _almacenamiento="SSD 512 GB",
        _gpu="Intel UHD Graphics",
    )
    eq1.id = equipos.crear(eq1)

    eq2 = Equipo(
        _usuario_id=juan.id,
        _numero_serie="XYZ789",
        _marca="Dell",
        _modelo="Latitude 5420",
        _sistema_operativo="Windows 11",
        _cpu="Intel i7-1185G7",
        _ram_gb=32,
        _almacenamiento="SSD 1 TB",
        _gpu="Intel Iris Xe",
    )
    eq2.id = equipos.crear(eq2)

    eq3 = Equipo(
        _usuario_id=maria.id,
        _numero_serie="MNO456",
        _marca="Lenovo",
        _modelo="ThinkPad E14",
        _sistema_operativo="Ubuntu 22.04",
        _cpu="AMD Ryzen 5 5500U",
        _ram_gb=16,
        _almacenamiento="SSD 256 GB",
        _gpu="Radeon Graphics",
    )
    eq3.id = equipos.crear(eq3)

    assert eq1.id and eq2.id and eq3.id

    # INC Wi-Fi (ejemplo del enunciado)
    inc_wifi = Incidencia(
        _equipo_id=eq1.id,
        _tecnico_id=tecnico.id,
        _titulo="No funciona el Wi-Fi",
        _descripcion="El equipo no detecta ninguna red Wi-Fi.",
        _categoria="Red/WiFi",
        _estado=EstadoIncidencia.EN_REPARACION,
        _prioridad=Prioridad.ALTA,
    )
    wifi_id = incidencias.crear(inc_wifi)
    incidencias.agregar_historial(wifi_id, "Incidencia creada: No funciona el Wi-Fi", juan.id)
    incidencias.agregar_historial(wifi_id, "Asignada a Carlos Técnico", admin.id)

    for desc in (
        "Reiniciado NetworkManager",
        "Comprobado adaptador",
        "Pendiente actualización de driver",
    ):
        incidencias.crear_intervencion(
            Intervencion(
                _incidencia_id=wifi_id,
                _tecnico_id=tecnico.id,
                _descripcion=desc,
            )
        )
        incidencias.agregar_historial(wifi_id, f"Intervención: {desc}", tecnico.id)

    # Disco lleno
    disco_id = incidencias.crear(
        Incidencia(
            _equipo_id=eq1.id,
            _tecnico_id=tecnico.id,
            _titulo="Disco lleno",
            _descripcion="El disco raíz está al 98% de uso.",
            _categoria="Hardware/PC",
            _estado=EstadoIncidencia.PENDIENTE,
            _prioridad=Prioridad.MEDIA,
        )
    )
    incidencias.agregar_historial(disco_id, "Incidencia creada: Disco lleno", juan.id)

    # Sonido
    sonido_id = incidencias.crear(
        Incidencia(
            _equipo_id=eq1.id,
            _titulo="Problemas de sonido",
            _descripcion="No hay salida de audio por altavoces ni auriculares.",
            _categoria="Hardware/Perifericos",
            _estado=EstadoIncidencia.ABIERTA,
            _prioridad=Prioridad.BAJA,
        )
    )
    incidencias.agregar_historial(sonido_id, "Incidencia creada: Problemas de sonido", juan.id)

    # Otra incidencia cerrada
    cerrada_id = incidencias.crear(
        Incidencia(
            _equipo_id=eq3.id,
            _tecnico_id=tecnico.id,
            _titulo="Impresora configurada",
            _descripcion="Se configuró la impresora de red correctamente.",
            _categoria="Hardware/Impresora",
            _estado=EstadoIncidencia.CERRADA,
            _prioridad=Prioridad.BAJA,
        )
    )
    incidencias.agregar_historial(cerrada_id, "Incidencia creada y resuelta", maria.id)
    db.execute(
        "UPDATE incidencias SET fecha_cierre = datetime('now', 'localtime') WHERE id = ?",
        (cerrada_id,),
    )

    for nombre, stock, precio, desc in (
        ("Adaptador Wi-Fi USB", 8, 24.90, "USB 802.11ac"),
        ("Disco SSD 512GB", 3, 59.90, "SATA III"),
        ("Memoria RAM 8GB DDR4", 12, 32.50, "SODIMM"),
        ("Cable HDMI 2m", 20, 6.90, "Alta velocidad"),
        ("Batería portátil genérica", 2, 45.00, "Stock bajo"),
    ):
        componentes.crear(
            Componente(
                _nombre=nombre,
                _stock=stock,
                _precio=precio,
                _descripcion=desc,
                _es_demo=True,
            )
        )

    from app.database.seed_equipo_detalle import ensure_equipo_detalle
    from app.database.seed_dashboard import ensure_dashboard_seed

    ensure_equipo_detalle(db)
    ensure_dashboard_seed(db)
