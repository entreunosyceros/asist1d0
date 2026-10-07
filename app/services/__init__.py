"""
Servicios de negocio de Asist{1d0}.

Cada servicio encapsula casos de uso (CRUD, cambios de estado, informes)
y delega la persistencia en los repositorios SQLite. La UI no habla
directamente con la base de datos.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from app.auth.password import hash_password
from app.database.connection import DatabaseConnection
from app.database.repositories import (
    ComponenteRepository,
    EquipoRepository,
    IncidenciaRepository,
    UsuarioRepository,
)
from app.models.componente import Componente
from app.models.enums import EstadoIncidencia, Prioridad, Rol
from app.models.equipo import Equipo
from app.models.incidencia import Comentario, Incidencia, Intervencion
from app.models.usuario import Usuario
from app.services.notificador import Notificador, NotificadorCompuesto, NotificadorConsola, NotificadorEmail


class UsuarioService:
    """Alta, edición, baja y consulta de cuentas de usuario."""

    def __init__(self, repo: UsuarioRepository) -> None:
        self._repo = repo

    def _contar_administradores(self) -> int:
        """Número de cuentas con rol administrador (demo + reales)."""
        return len(self._repo.listar(rol=Rol.ADMINISTRADOR))

    def listar(
        self,
        solo_activos: bool = False,
        rol: Optional[Rol] = None,
        es_demo: Optional[bool] = None,
    ) -> list[Usuario]:
        return self._repo.listar(solo_activos=solo_activos, rol=rol, es_demo=es_demo)

    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        return self._repo.obtener_por_id(usuario_id)

    def crear(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: Rol = Rol.USUARIO,
        telefono: str = "",
        es_demo: bool = False,
    ) -> Usuario:
        if self._repo.obtener_por_email(email):
            raise ValueError("Ya existe un usuario con ese email")
        u = Usuario(
            _nombre=nombre,
            _email=email.lower(),
            _telefono=telefono,
            _password_hash=hash_password(password),
            _rol=rol,
            _es_demo=es_demo,
        )
        u.id = self._repo.crear(u)
        return u

    def actualizar(
        self,
        usuario: Usuario,
        *,
        nombre: Optional[str] = None,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        rol: Optional[Rol] = None,
        password: Optional[str] = None,
        activo: Optional[bool] = None,
        actor_id: Optional[int] = None,
    ) -> Usuario:
        rol_anterior = usuario.rol
        pierde_admin = usuario.es_admin() and (
            (rol is not None and rol != Rol.ADMINISTRADOR) or activo is False
        )
        # No permitir que el admin se quite a sí mismo el rol/acceso.
        if actor_id is not None and usuario.id == actor_id:
            if rol is not None and rol_anterior == Rol.ADMINISTRADOR and rol != Rol.ADMINISTRADOR:
                raise PermissionError(
                    "No puedes quitarte el rol de administrador a ti mismo."
                )
            if activo is False:
                raise PermissionError("No puedes desactivar tu propia cuenta.")
        # Debe quedar al menos un administrador en el sistema.
        if pierde_admin and self._contar_administradores() <= 1:
            raise ValueError("Debe quedar al menos un administrador en el sistema.")

        if nombre is not None:
            usuario.nombre = nombre
        if email is not None:
            usuario.email = email
        if telefono is not None:
            usuario.telefono = telefono
        if rol is not None:
            usuario._rol = rol
        if password:
            usuario.password_hash = hash_password(password)
        if activo is not None:
            usuario.activo = activo
        self._repo.actualizar(usuario)
        return usuario

    def eliminar(self, usuario_id: int, *, actor_id: Optional[int] = None) -> None:
        if actor_id is not None and actor_id == usuario_id:
            raise PermissionError("No puedes eliminarte a ti mismo.")
        objetivo = self._repo.obtener_por_id(usuario_id)
        if objetivo is None:
            raise ValueError("Usuario no encontrado")
        if objetivo.es_admin() and self._contar_administradores() <= 1:
            raise ValueError("No se puede eliminar al último administrador.")
        self._repo.eliminar(usuario_id)

    def tecnicos(self, es_demo: Optional[bool] = None) -> list[Usuario]:
        return self._repo.listar(
            solo_activos=True, rol=Rol.TECNICO, es_demo=es_demo
        ) + self._repo.listar(
            solo_activos=True, rol=Rol.ADMINISTRADOR, es_demo=es_demo
        )


class EquipoService:
    """Gestión de equipos informáticos vinculados a usuarios."""

    def __init__(self, repo: EquipoRepository) -> None:
        self._repo = repo

    def listar(
        self, usuario_id: Optional[int] = None, es_demo: Optional[bool] = None
    ) -> list[Equipo]:
        return self._repo.listar(usuario_id=usuario_id, es_demo=es_demo)

    def obtener(self, equipo_id: int) -> Optional[Equipo]:
        return self._repo.obtener_por_id(equipo_id)

    def crear(
        self,
        usuario_id: int,
        numero_serie: str,
        marca: str,
        modelo: str,
        sistema_operativo: str = "",
    ) -> Equipo:
        eq = Equipo(
            _usuario_id=usuario_id,
            _numero_serie=numero_serie,
            _marca=marca,
            _modelo=modelo,
            _sistema_operativo=sistema_operativo,
        )
        eq.id = self._repo.crear(eq)
        return eq

    def actualizar(self, equipo: Equipo) -> Equipo:
        self._repo.actualizar(equipo)
        return equipo

    def eliminar(self, equipo_id: int) -> None:
        self._repo.eliminar(equipo_id)

    def contar(
        self, usuario_id: Optional[int] = None, es_demo: Optional[bool] = None
    ) -> int:
        return self._repo.contar(usuario_id=usuario_id, es_demo=es_demo)

class IncidenciaService:
    """Casos de uso de incidencias: alta, estado, asignación e intervenciones."""

    def __init__(
        self,
        repo: IncidenciaRepository,
        notificador: Optional[Notificador] = None,
    ) -> None:
        self._repo = repo
        self._notificador = notificador or NotificadorCompuesto(
            NotificadorConsola(), NotificadorEmail()
        )
        self._tray_notify: Callable[[str, str], None] | None = None
        self._tray_user_id: int | None = None

    def set_tray_notifier(
        self,
        notify: Callable[[str, str], None] | None,
        usuario_id: int | None = None,
    ) -> None:
        """Enlaza avisos de bandeja con el usuario de la sesión activa."""
        self._tray_notify = notify
        self._tray_user_id = usuario_id

    def avisar_bandeja(self, titulo: str, mensaje: str) -> None:
        """Muestra un aviso en la bandeja de la sesión activa (si hay)."""
        if self._tray_notify:
            self._tray_notify(titulo, mensaje)

    def _tray_aviso(
        self,
        destinatarios: list[int],
        titulo: str,
        mensaje: str,
        actor_id: int | None = None,
        *,
        mensaje_actor: str | None = None,
    ) -> None:
        """
        Avisa en bandeja a la sesión actual.

        En escritorio local (una sesión) confirma también al usuario que actúa;
        si el destinatario fuera otro y estuviera en sesión, recibe ``mensaje``.
        """
        if not self._tray_notify or self._tray_user_id is None:
            return
        if actor_id is not None and self._tray_user_id == actor_id:
            self._tray_notify(titulo, mensaje_actor or mensaje)
            return
        if self._tray_user_id in destinatarios:
            self._tray_notify(titulo, mensaje)

    def listar(self, **filtros) -> list[Incidencia]:
        return self._repo.listar(**filtros)

    def obtener(
        self, incidencia_id: int, es_demo: Optional[bool] = None
    ) -> Optional[Incidencia]:
        return self._repo.obtener_por_id(incidencia_id, es_demo=es_demo)

    def crear(
        self,
        equipo_id: int,
        titulo: str,
        descripcion: str = "",
        prioridad: Prioridad = Prioridad.MEDIA,
        actor_id: Optional[int] = None,
        tecnico_id: Optional[int] = None,
    ) -> Incidencia:
        inc = Incidencia(
            _equipo_id=equipo_id,
            _titulo=titulo,
            _descripcion=descripcion,
            _prioridad=prioridad,
            _tecnico_id=tecnico_id,
        )
        with self._repo._db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO incidencias
                    (equipo_id, tecnico_id, titulo, descripcion, estado, prioridad)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    equipo_id,
                    tecnico_id,
                    titulo,
                    descripcion,
                    EstadoIncidencia.ABIERTA.value,
                    prioridad.value,
                ),
            )
            inc_id = cur.lastrowid
            conn.execute(
                "INSERT INTO historial (incidencia_id, accion, usuario_id) VALUES (?, ?, ?)",
                (inc_id, f"Incidencia creada: {titulo}", actor_id),
            )
        inc = self._repo.obtener_por_id(inc_id)  # type: ignore[arg-type]
        assert inc is not None
        self._notificador.notificar(inc, f"Nueva incidencia creada con prioridad {prioridad.value}")
        return inc

    def cambiar_estado(
        self,
        incidencia_id: int,
        nuevo_estado: EstadoIncidencia,
        actor_id: Optional[int] = None,
        *,
        avisar_bandeja: bool = True,
    ) -> Incidencia:
        inc = self._repo.obtener_por_id(incidencia_id, con_detalle=False)
        if not inc:
            raise ValueError("Incidencia no encontrada")
        anterior = inc.estado
        inc.estado = nuevo_estado
        with self._repo._db.transaction() as conn:
            if nuevo_estado == EstadoIncidencia.CERRADA:
                conn.execute(
                    """
                    UPDATE incidencias
                    SET estado = ?,
                        fecha_cierre = COALESCE(fecha_cierre, datetime('now', 'localtime'))
                    WHERE id = ?
                    """,
                    (nuevo_estado.value, incidencia_id),
                )
            else:
                conn.execute(
                    "UPDATE incidencias SET estado = ?, fecha_cierre = NULL WHERE id = ?",
                    (nuevo_estado.value, incidencia_id),
                )
            conn.execute(
                "INSERT INTO historial (incidencia_id, accion, usuario_id) VALUES (?, ?, ?)",
                (
                    incidencia_id,
                    f"Estado: {anterior.value} → {nuevo_estado.value}",
                    actor_id,
                ),
            )
        inc = self._repo.obtener_por_id(incidencia_id)
        assert inc is not None
        self._notificador.notificar(inc, f"Estado actualizado a {nuevo_estado.value}")
        if avisar_bandeja:
            dest = [inc.usuario_id] if inc.usuario_id is not None else []
            texto = f"Estado actualizado a {nuevo_estado.value}"
            self._tray_aviso(
                dest,
                inc.codigo,
                texto,
                actor_id,
                mensaje_actor=texto,
            )
        return inc

    def cambiar_prioridad(
        self,
        incidencia_id: int,
        prioridad: Prioridad,
        actor_id: Optional[int] = None,
    ) -> Incidencia:
        inc = self._repo.obtener_por_id(incidencia_id, con_detalle=False)
        if not inc:
            raise ValueError("Incidencia no encontrada")
        anterior = inc.prioridad
        self._repo._db.execute(
            "UPDATE incidencias SET prioridad = ? WHERE id = ?",
            (prioridad.value, incidencia_id),
        )
        self._repo.agregar_historial(
            incidencia_id,
            f"Prioridad: {anterior.value} → {prioridad.value}",
            actor_id,
        )
        return self._repo.obtener_por_id(incidencia_id)  # type: ignore[return-value]

    def asignar_tecnico(
        self,
        incidencia_id: int,
        tecnico_id: Optional[int],
        actor_id: Optional[int] = None,
        tecnico_nombre: Optional[str] = None,
        *,
        avisar_bandeja: bool = True,
    ) -> Incidencia:
        self._repo._db.execute(
            "UPDATE incidencias SET tecnico_id = ? WHERE id = ?",
            (tecnico_id, incidencia_id),
        )
        if tecnico_id is None:
            accion = "Técnico desasignado"
        else:
            nombre = tecnico_nombre or f"id={tecnico_id}"
            accion = f"Asignada a {nombre}"
        self._repo.agregar_historial(incidencia_id, accion, actor_id)
        inc = self._repo.obtener_por_id(incidencia_id)
        assert inc is not None
        self._notificador.notificar(inc, accion)
        if avisar_bandeja:
            if tecnico_id is not None:
                self._tray_aviso(
                    [tecnico_id],
                    inc.codigo,
                    f"Te han asignado: {inc.titulo}",
                    actor_id,
                    mensaje_actor=accion,
                )
            else:
                self._tray_aviso(
                    [],
                    inc.codigo,
                    accion,
                    actor_id,
                    mensaje_actor=accion,
                )
        return inc

    def agregar_comentario(
        self,
        incidencia_id: int,
        usuario_id: int,
        texto: str,
        *,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> Comentario:
        """Añade un comentario visible en el hilo del ticket."""
        texto = texto.strip()
        if not texto:
            raise ValueError("El comentario no puede estar vacío")
        inc = self._repo.obtener_por_id(
            incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if rol == Rol.USUARIO and inc.usuario_id != usuario_id:
            raise PermissionError("Solo puedes comentar en tus propias incidencias")
        comentario = Comentario(
            _incidencia_id=incidencia_id,
            _usuario_id=usuario_id,
            _texto=texto,
        )
        comentario.id = self._repo.crear_comentario(comentario)
        preview = texto if len(texto) <= 80 else texto[:77] + "..."
        self._repo.agregar_historial(
            incidencia_id,
            f"Comentario añadido: {preview}",
            usuario_id,
        )
        destinatarios: list[int] = []
        if inc.usuario_id is not None and inc.usuario_id != usuario_id:
            destinatarios.append(inc.usuario_id)
        if inc.tecnico_id is not None and inc.tecnico_id != usuario_id:
            destinatarios.append(inc.tecnico_id)
        elif rol == Rol.USUARIO and inc.tecnico_id is None:
            pass
        self._tray_aviso(
            destinatarios,
            inc.codigo,
            f"Nuevo comentario: {preview}",
            usuario_id,
            mensaje_actor="Comentario enviado",
        )
        rows = self._repo.listar_comentarios(incidencia_id)
        return rows[-1] if rows else comentario

    def agregar_intervencion(
        self,
        incidencia_id: int,
        tecnico_id: int,
        descripcion: str,
    ) -> Intervencion:
        iv = Intervencion(
            _incidencia_id=incidencia_id,
            _tecnico_id=tecnico_id,
            _descripcion=descripcion,
        )
        with self._repo._db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO intervenciones (incidencia_id, tecnico_id, descripcion)
                VALUES (?, ?, ?)
                """,
                (incidencia_id, tecnico_id, descripcion),
            )
            iv_id = cur.lastrowid
            conn.execute(
                "INSERT INTO historial (incidencia_id, accion, usuario_id) VALUES (?, ?, ?)",
                (incidencia_id, f"Intervención: {descripcion}", tecnico_id),
            )
            # Si está abierta, pasar a En reparación
            conn.execute(
                """
                UPDATE incidencias SET estado = 'En reparación'
                WHERE id = ? AND estado = 'Abierta'
                """,
                (incidencia_id,),
            )
        iv._id = iv_id
        return iv

    def estadisticas_dashboard(
        self,
        usuario_id: Optional[int] = None,
        es_demo: Optional[bool] = None,
    ) -> dict:
        return {
            "abiertas": self._repo.contar(
                usuario_id=usuario_id, solo_abiertas=True, es_demo=es_demo
            ),
            "pendientes": self._repo.contar(
                usuario_id=usuario_id,
                estado=EstadoIncidencia.PENDIENTE,
                es_demo=es_demo,
            ),
            "alta_prioridad": self._repo.contar(
                usuario_id=usuario_id,
                solo_abiertas=True,
                prioridad=Prioridad.ALTA,
                es_demo=es_demo,
            )
            + self._repo.contar(
                usuario_id=usuario_id,
                solo_abiertas=True,
                prioridad=Prioridad.CRITICA,
                es_demo=es_demo,
            ),
            "total": self._repo.contar(usuario_id=usuario_id, es_demo=es_demo),
        }


class InventarioService:
    """Stock de componentes/repuestos y consumo en reparaciones."""

    def __init__(self, repo: ComponenteRepository) -> None:
        self._repo = repo

    def listar(self, es_demo: Optional[bool] = None) -> list[Componente]:
        return self._repo.listar(es_demo=es_demo)

    def stock_bajo(
        self, umbral: int = 5, es_demo: Optional[bool] = None
    ) -> list[Componente]:
        return self._repo.listar_stock_bajo(umbral, es_demo=es_demo)

    def crear(
        self,
        nombre: str,
        stock: int = 0,
        precio: float = 0.0,
        descripcion: str = "",
        es_demo: bool = False,
    ) -> Componente:
        c = Componente(
            _nombre=nombre,
            _stock=stock,
            _precio=precio,
            _descripcion=descripcion,
            _es_demo=es_demo,
        )
        c.id = self._repo.crear(c)
        return c

    def actualizar(self, componente: Componente) -> Componente:
        self._repo.actualizar(componente)
        return componente

    def eliminar(self, componente_id: int) -> None:
        self._repo.eliminar(componente_id)

    def usar_en_incidencia(
        self,
        incidencia_id: int,
        componente_id: int,
        cantidad: int = 1,
        actor_id: Optional[int] = None,
        incidencia_repo: Optional[IncidenciaRepository] = None,
    ) -> None:
        self._repo.asociar_a_incidencia(incidencia_id, componente_id, cantidad)
        if incidencia_repo is not None:
            comp = self._repo.obtener_por_id(componente_id)
            nombre = comp.nombre if comp else f"#{componente_id}"
            incidencia_repo.agregar_historial(
                incidencia_id,
                f"Repuesto usado: {nombre} × {cantidad}",
                actor_id,
            )

    def componentes_de_incidencia(self, incidencia_id: int) -> list[dict]:
        return self._repo.listar_por_incidencia(incidencia_id)


class ReportService:
    """Consultas agregadas y exportación CSV para el módulo Informes."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def _filtro_demo_sql(self, es_demo: Optional[bool]) -> tuple[str, list]:
        if es_demo is None:
            return "", []
        return " AND u.es_demo = ?", [1 if es_demo else 0]

    def por_estado(self, es_demo: Optional[bool] = None) -> list[dict]:
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT i.estado, COUNT(*) AS total
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1{extra}
            GROUP BY i.estado
            ORDER BY total DESC
            """,
            params,
        )
        return [dict(r) for r in rows]

    def por_prioridad(self, es_demo: Optional[bool] = None) -> list[dict]:
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT i.prioridad, COUNT(*) AS total
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1{extra}
            GROUP BY i.prioridad
            ORDER BY total DESC
            """,
            params,
        )
        return [dict(r) for r in rows]

    def por_tecnico(self, es_demo: Optional[bool] = None) -> list[dict]:
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT COALESCE(t.nombre, 'Sin asignar') AS tecnico, COUNT(*) AS total
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            LEFT JOIN usuarios t ON t.id = i.tecnico_id
            WHERE 1=1{extra}
            GROUP BY i.tecnico_id
            ORDER BY total DESC
            """,
            params,
        )
        return [dict(r) for r in rows]

    def tiempo_medio_cierre_horas(self, es_demo: Optional[bool] = None) -> Optional[float]:
        extra, params = self._filtro_demo_sql(es_demo)
        row = self._db.fetchone(
            f"""
            SELECT AVG(
                (julianday(i.fecha_cierre) - julianday(i.fecha_creacion)) * 24.0
            ) AS media
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE i.fecha_cierre IS NOT NULL{extra}
            """,
            params,
        )
        if row and row["media"] is not None:
            return round(float(row["media"]), 2)
        return None

    def exportar_csv(self, destino: Path, es_demo: Optional[bool] = None) -> Path:
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT i.id, i.titulo, i.estado, i.prioridad, i.fecha_creacion, i.fecha_cierre,
                   (e.marca || ' ' || e.modelo) AS equipo,
                   u.nombre AS usuario,
                   t.nombre AS tecnico
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            LEFT JOIN usuarios t ON t.id = i.tecnico_id
            WHERE 1=1{extra}
            ORDER BY i.id
            """,
            params,
        )
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "id",
                    "titulo",
                    "estado",
                    "prioridad",
                    "fecha_creacion",
                    "fecha_cierre",
                    "equipo",
                    "usuario",
                    "tecnico",
                ]
            )
            for r in rows:
                writer.writerow(
                    [
                        r["id"],
                        r["titulo"],
                        r["estado"],
                        r["prioridad"],
                        r["fecha_creacion"],
                        r["fecha_cierre"] or "",
                        r["equipo"],
                        r["usuario"],
                        r["tecnico"] or "",
                    ]
                )
        return destino


class HistorialService:
    """Acceso al historial de cambios de incidencias."""

    def __init__(self, repo: IncidenciaRepository) -> None:
        self._repo = repo

    def de_incidencia(self, incidencia_id: int):
        return self._repo.listar_historial(incidencia_id)

    def global_(self, limite: int = 50, es_demo: Optional[bool] = None):
        return self._repo.listar_historial_global(limite, es_demo=es_demo)

    def consultas_predefinidas(
        self, db: DatabaseConnection, es_demo: Optional[bool] = None
    ) -> dict[str, list[dict]]:
        """Consultas de solo lectura para el panel técnico."""
        demo_clause = ""
        params: list = []
        if es_demo is not None:
            demo_clause = " AND u.es_demo = ?"
            params = [1 if es_demo else 0]
        return {
            "Incidencias abiertas por prioridad": [
                dict(r)
                for r in db.fetchall(
                    f"""
                    SELECT i.prioridad, COUNT(*) AS total
                    FROM incidencias i
                    JOIN equipos e ON e.id = i.equipo_id
                    JOIN usuarios u ON u.id = e.usuario_id
                    WHERE i.estado != 'Cerrada'{demo_clause}
                    GROUP BY i.prioridad
                    """,
                    params,
                )
            ],
            "Equipos con más incidencias": [
                dict(r)
                for r in db.fetchall(
                    f"""
                    SELECT e.marca || ' ' || e.modelo AS equipo,
                           e.numero_serie,
                           COUNT(i.id) AS incidencias
                    FROM equipos e
                    JOIN usuarios u ON u.id = e.usuario_id
                    LEFT JOIN incidencias i ON i.equipo_id = e.id
                    WHERE 1=1{demo_clause}
                    GROUP BY e.id
                    ORDER BY incidencias DESC
                    LIMIT 10
                    """,
                    params,
                )
            ],
            "Últimas 15 intervenciones": [
                dict(r)
                for r in db.fetchall(
                    f"""
                    SELECT iv.fecha, tu.nombre AS tecnico, iv.descripcion,
                           i.id AS incidencia_id
                    FROM intervenciones iv
                    JOIN usuarios tu ON tu.id = iv.tecnico_id
                    JOIN incidencias i ON i.id = iv.incidencia_id
                    JOIN equipos e ON e.id = i.equipo_id
                    JOIN usuarios u ON u.id = e.usuario_id
                    WHERE 1=1{demo_clause}
                    ORDER BY iv.fecha DESC
                    LIMIT 15
                    """,
                    params,
                )
            ],
            "Componentes con stock bajo": [
                dict(r)
                for r in db.fetchall(
                    """
                    SELECT nombre, stock, precio FROM componentes
                    WHERE stock <= 5 AND es_demo = ?
                    ORDER BY stock
                    """,
                    [1 if es_demo else 0] if es_demo is not None else [0],
                )
            ],
        }
