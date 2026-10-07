"""
Servicios de negocio de Asist{1d0}.

Cada servicio encapsula casos de uso (CRUD, cambios de estado, informes)
y delega la persistencia en los repositorios SQLite. La UI no habla
directamente con la base de datos.
"""

from __future__ import annotations

import csv
import shutil
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.auth.password import hash_password
from app.config import ADJUNTO_EXTENSIONES, ADJUNTO_MAX_BYTES, ADJUNTOS_DIR
from app.database.connection import DatabaseConnection
from app.database.repositories import (
    ComponenteRepository,
    EquipoRepository,
    IncidenciaRepository,
    UsuarioRepository,
)
from app.models.audit import AuditAction, AuditEntity
from app.models.componente import Componente
from app.models.catalogo_categorias import normalizar_codigo, resolver_categoria
from app.models.enums import EstadoIncidencia, Prioridad, Rol
from app.database.repositories.grupo_repository import GrupoRepository
from app.models.equipo import Equipo, EquipoComponente, EquipoReparacion, EquipoSoftware
from app.models.incidencia import Adjunto, Comentario, Incidencia, Intervencion
from app.models.usuario import Usuario
from app.services.audit_service import AuditService
from app.services.notificador import Notificador, NotificadorCompuesto, NotificadorConsola, NotificadorEmail


def _parse_fecha_incidencia(texto: Optional[str]) -> Optional[datetime]:
    """Parsea fechas SQLite ``YYYY-MM-DD[ HH:MM:SS]`` usadas en incidencias."""
    if not texto:
        return None
    raw = texto.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    return None


class UsuarioService:
    """Alta, edición, baja y consulta de cuentas de usuario."""

    def __init__(
        self, repo: UsuarioRepository, audit: Optional[AuditService] = None
    ) -> None:
        self._repo = repo
        self._audit = audit

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
        *,
        actor_id: Optional[int] = None,
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
        if self._audit:
            actor = self._repo.obtener_por_id(actor_id) if actor_id else None
            quien = actor.nombre if actor else "Sistema"
            self._audit.registrar(
                actor_id,
                AuditAction.CREAR,
                AuditEntity.USUARIO,
                u.id,
                f"{quien} creó usuario #{u.id} (rol={u.rol.value})",
            )
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

        cambios: list[str] = []
        if nombre is not None and nombre != usuario.nombre:
            cambios.append("nombre")
            usuario.nombre = nombre
        if email is not None and email.lower() != usuario.email:
            cambios.append("email")
            usuario.email = email
        if telefono is not None:
            usuario.telefono = telefono
            cambios.append("telefono")
        if rol is not None and rol != rol_anterior:
            cambios.append(f"rol={rol_anterior.value}→{rol.value}")
            usuario._rol = rol
        if password:
            usuario.password_hash = hash_password(password)
            cambios.append("password")
        if activo is not None and activo != usuario.activo:
            cambios.append(f"activo={activo}")
            usuario.activo = activo
        self._repo.actualizar(usuario)
        if self._audit and cambios:
            actor = self._repo.obtener_por_id(actor_id) if actor_id else None
            quien = actor.nombre if actor else "Sistema"
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.USUARIO,
                usuario.id,
                f"{quien} actualizó usuario #{usuario.id} ({', '.join(cambios)})",
            )
        return usuario

    def eliminar(self, usuario_id: int, *, actor_id: Optional[int] = None) -> None:
        if actor_id is not None and actor_id == usuario_id:
            raise PermissionError("No puedes eliminarte a ti mismo.")
        objetivo = self._repo.obtener_por_id(usuario_id)
        if objetivo is None:
            raise ValueError("Usuario no encontrado")
        if objetivo.es_admin() and self._contar_administradores() <= 1:
            raise ValueError("No se puede eliminar al último administrador.")
        email = objetivo.email
        self._repo.eliminar(usuario_id)
        if self._audit:
            actor = self._repo.obtener_por_id(actor_id) if actor_id else None
            quien = actor.nombre if actor else "Sistema"
            self._audit.registrar(
                actor_id,
                AuditAction.ELIMINAR,
                AuditEntity.USUARIO,
                usuario_id,
                f"{quien} eliminó usuario #{usuario_id} ({email})",
            )

    def tecnicos(self, es_demo: Optional[bool] = None) -> list[Usuario]:
        return self._repo.listar(
            solo_activos=True, rol=Rol.TECNICO, es_demo=es_demo
        ) + self._repo.listar(
            solo_activos=True, rol=Rol.ADMINISTRADOR, es_demo=es_demo
        )


class EquipoService:
    """Gestión de equipos informáticos vinculados a usuarios."""

    def __init__(
        self, repo: EquipoRepository, audit: Optional[AuditService] = None
    ) -> None:
        self._repo = repo
        self._audit = audit

    def listar(
        self, usuario_id: Optional[int] = None, es_demo: Optional[bool] = None
    ) -> list[Equipo]:
        return self._repo.listar(usuario_id=usuario_id, es_demo=es_demo)

    def obtener(self, equipo_id: int, *, con_detalle: bool = False) -> Optional[Equipo]:
        return self._repo.obtener_por_id(equipo_id, con_detalle=con_detalle)

    def crear(
        self,
        usuario_id: int,
        numero_serie: str,
        marca: str,
        modelo: str,
        sistema_operativo: str = "",
        *,
        cpu: str = "",
        ram_gb: int = 0,
        almacenamiento: str = "",
        gpu: str = "",
        actor_id: Optional[int] = None,
    ) -> Equipo:
        eq = Equipo(
            _usuario_id=usuario_id,
            _numero_serie=numero_serie,
            _marca=marca,
            _modelo=modelo,
            _sistema_operativo=sistema_operativo,
            _cpu=cpu,
            _ram_gb=ram_gb,
            _almacenamiento=almacenamiento,
            _gpu=gpu,
        )
        eq.id = self._repo.crear(eq)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CREAR,
                AuditEntity.EQUIPO,
                eq.id,
                f"Creó equipo {eq.codigo} ({marca} {modelo}, serie={numero_serie})",
            )
        return eq

    def actualizar(
        self,
        equipo: Equipo,
        *,
        actor_id: Optional[int] = None,
        rol: Optional[Rol] = None,
    ) -> Equipo:
        """Actualiza un equipo; el rol Usuario solo puede editar los suyos."""
        if rol == Rol.USUARIO:
            if actor_id is None or equipo.usuario_id != actor_id:
                raise PermissionError("Solo puedes editar tus propios equipos")
        self._repo.actualizar(equipo)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo.id,
                f"Actualizó equipo {equipo.codigo} ({equipo.marca} {equipo.modelo})",
            )
        return equipo

    def eliminar(
        self, equipo_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        eq = self._repo.obtener_por_id(equipo_id)
        self._repo.eliminar(equipo_id)
        if self._audit:
            detalle = f"Eliminó equipo #{equipo_id}"
            if eq:
                detalle = (
                    f"Eliminó equipo {eq.codigo} "
                    f"({eq.marca} {eq.modelo}, serie={eq.numero_serie})"
                )
            self._audit.registrar(
                actor_id,
                AuditAction.ELIMINAR,
                AuditEntity.EQUIPO,
                equipo_id,
                detalle,
            )

    def contar(
        self, usuario_id: Optional[int] = None, es_demo: Optional[bool] = None
    ) -> int:
        return self._repo.contar(usuario_id=usuario_id, es_demo=es_demo)

    def anadir_componente(
        self,
        equipo_id: int,
        componente_id: int,
        cantidad: int = 1,
        notas: str = "",
        *,
        actor_id: Optional[int] = None,
    ) -> EquipoComponente:
        item = EquipoComponente(
            _equipo_id=equipo_id,
            _componente_id=componente_id,
            _cantidad=max(1, cantidad),
            _notas=notas,
        )
        item._id = self._repo.anadir_componente(item)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo_id,
                f"Componente #{componente_id} × {cantidad} en equipo #{equipo_id}",
            )
        rows = self._repo.listar_componentes(equipo_id)
        return rows[0] if rows else item

    def quitar_componente(
        self, item_id: int, equipo_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        self._repo.eliminar_componente(item_id)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo_id,
                f"Quitó componente instalado #{item_id} del equipo #{equipo_id}",
            )

    def anadir_software(
        self,
        equipo_id: int,
        nombre: str,
        version: str = "",
        licencia: str = "",
        *,
        actor_id: Optional[int] = None,
    ) -> EquipoSoftware:
        item = EquipoSoftware(
            _equipo_id=equipo_id,
            _nombre=nombre,
            _version=version,
            _licencia=licencia,
        )
        item._id = self._repo.anadir_software(item)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo_id,
                f"Software «{nombre}» en equipo #{equipo_id}",
            )
        return item

    def quitar_software(
        self, item_id: int, equipo_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        self._repo.eliminar_software(item_id)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo_id,
                f"Quitó software #{item_id} del equipo #{equipo_id}",
            )

    def registrar_reparacion(
        self,
        equipo_id: int,
        descripcion: str,
        *,
        tecnico_id: Optional[int] = None,
        incidencia_id: Optional[int] = None,
        coste: float = 0.0,
        actor_id: Optional[int] = None,
    ) -> EquipoReparacion:
        item = EquipoReparacion(
            _equipo_id=equipo_id,
            _descripcion=descripcion,
            _tecnico_id=tecnico_id,
            _incidencia_id=incidencia_id,
            _coste=coste,
        )
        item._id = self._repo.anadir_reparacion(item)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.EQUIPO,
                equipo_id,
                f"Reparación en equipo #{equipo_id}: {descripcion[:80]}",
            )
        rows = self._repo.listar_reparaciones(equipo_id)
        return next((r for r in rows if r.id == item.id), item)

class IncidenciaService:
    """Casos de uso de incidencias: alta, estado, asignación e intervenciones."""

    def __init__(
        self,
        repo: IncidenciaRepository,
        notificador: Optional[Notificador] = None,
        audit: Optional[AuditService] = None,
        grupos: Optional[GrupoRepository] = None,
    ) -> None:
        self._repo = repo
        self._notificador = notificador or NotificadorCompuesto(
            NotificadorConsola(), NotificadorEmail()
        )
        self._audit = audit
        self._grupos = grupos
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
        categoria: str = "Otro",
        actor_id: Optional[int] = None,
        tecnico_id: Optional[int] = None,
        grupo_id: Optional[int] = None,
    ) -> Incidencia:
        cat_codigo = normalizar_codigo(
            getattr(categoria, "value", categoria) if categoria else "Otro"
        )
        # Si no se indica grupo, tomar el de la categoría del catálogo.
        if grupo_id is None and self._grupos is not None:
            hoja = resolver_categoria(cat_codigo)
            if hoja is not None:
                g = self._grupos.obtener_por_codigo(hoja.perfil.grupo.codigo)
                if g is not None:
                    grupo_id = g.id
        with self._repo._db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO incidencias
                    (equipo_id, tecnico_id, grupo_id, titulo, descripcion,
                     categoria, estado, prioridad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipo_id,
                    tecnico_id,
                    grupo_id,
                    titulo,
                    descripcion,
                    cat_codigo,
                    EstadoIncidencia.ABIERTA.value,
                    prioridad.value,
                ),
            )
            inc_id = cur.lastrowid
            hist = f"Incidencia creada: {titulo} [{cat_codigo}]"
            if grupo_id is not None and self._grupos is not None:
                g = self._grupos.obtener_por_id(grupo_id)
                if g:
                    hist += f" → grupo {g.nombre}"
            conn.execute(
                "INSERT INTO historial (incidencia_id, accion, usuario_id) VALUES (?, ?, ?)",
                (inc_id, hist, actor_id),
            )
        inc = self._repo.obtener_por_id(inc_id)  # type: ignore[arg-type]
        assert inc is not None
        self._notificador.notificar(inc, f"Nueva incidencia creada con prioridad {prioridad.value}")
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CREAR,
                AuditEntity.INCIDENCIA,
                inc.id,
                f"Creó incidencia #{inc.id}: {titulo} [{cat_codigo}]",
            )
        return inc

    def confirmar_resolucion(
        self,
        incidencia_id: int,
        *,
        actor_id: int,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> Incidencia:
        """El usuario dueño confirma que el problema quedó resuelto → Cerrada."""
        if rol != Rol.USUARIO:
            raise PermissionError("Solo el usuario final confirma la resolución")
        inc = self._repo.obtener_por_id(
            incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if inc.usuario_id != actor_id:
            raise PermissionError("Solo puedes confirmar tus propias incidencias")
        if inc.estado not in (
            EstadoIncidencia.PENDIENTE,
            EstadoIncidencia.EN_REPARACION,
        ):
            raise ValueError(
                "Solo puedes confirmar cuando el ticket está En reparación o Pendiente"
            )
        resultado = self.cambiar_estado(
            incidencia_id, EstadoIncidencia.CERRADA, actor_id=actor_id
        )
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CONFIRMAR,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                f"Confirmó resolución de incidencia #{incidencia_id}",
            )
        return resultado

    def reabrir(
        self,
        incidencia_id: int,
        *,
        actor_id: int,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> Incidencia:
        """El usuario dueño reabre un ticket cerrado."""
        if rol != Rol.USUARIO:
            raise PermissionError("Solo el usuario final puede reabrir desde el portal/ficha")
        inc = self._repo.obtener_por_id(
            incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if inc.usuario_id != actor_id:
            raise PermissionError("Solo puedes reabrir tus propias incidencias")
        if inc.estado != EstadoIncidencia.CERRADA:
            raise ValueError("Solo se pueden reabrir incidencias cerradas")
        resultado = self.cambiar_estado(
            incidencia_id, EstadoIncidencia.ABIERTA, actor_id=actor_id
        )
        self._repo.agregar_historial(
            incidencia_id, "Reabierta por el usuario", actor_id
        )
        self._notificador.notificar(resultado, "Incidencia reabierta por el usuario")
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.REABRIR,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                f"Reabrió incidencia #{incidencia_id}",
            )
        return resultado

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
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CAMBIAR_ESTADO,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                f"Estado: {anterior.value} → {nuevo_estado.value}",
            )
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
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                f"Prioridad: {anterior.value} → {prioridad.value}",
            )
        return self._repo.obtener_por_id(incidencia_id)  # type: ignore[return-value]

    def asignar_grupo(
        self,
        incidencia_id: int,
        grupo_id: Optional[int],
        actor_id: Optional[int] = None,
        *,
        limpiar_tecnico: bool = False,
        avisar_bandeja: bool = True,
    ) -> Incidencia:
        """Asigna la incidencia a un grupo (cola). Opcionalmente quita el técnico."""
        if grupo_id is not None and self._grupos is not None:
            if self._grupos.obtener_por_id(grupo_id) is None:
                raise ValueError("Grupo no encontrado")
        if limpiar_tecnico:
            self._repo._db.execute(
                "UPDATE incidencias SET grupo_id = ?, tecnico_id = NULL WHERE id = ?",
                (grupo_id, incidencia_id),
            )
        else:
            self._repo._db.execute(
                "UPDATE incidencias SET grupo_id = ? WHERE id = ?",
                (grupo_id, incidencia_id),
            )
        if grupo_id is None:
            accion = "Grupo desasignado"
        else:
            nombre = f"id={grupo_id}"
            if self._grupos is not None:
                g = self._grupos.obtener_por_id(grupo_id)
                if g:
                    nombre = g.nombre
            accion = f"Asignada al grupo {nombre}"
        self._repo.agregar_historial(incidencia_id, accion, actor_id)
        inc = self._repo.obtener_por_id(incidencia_id)
        assert inc is not None
        self._notificador.notificar(inc, accion)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ASIGNAR,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                accion,
            )
        if avisar_bandeja:
            self._tray_aviso(
                [],
                inc.codigo,
                accion,
                actor_id,
                mensaje_actor=accion,
            )
        return inc

    def asignar_tecnico(
        self,
        incidencia_id: int,
        tecnico_id: Optional[int],
        actor_id: Optional[int] = None,
        tecnico_nombre: Optional[str] = None,
        *,
        grupo_id: Optional[int] = None,
        avisar_bandeja: bool = True,
    ) -> Incidencia:
        """
        Asigna un técnico. Si se pasa ``grupo_id``, actualiza también el grupo
        (flujo Grupo → Técnico).
        """
        if grupo_id is not None:
            self._repo._db.execute(
                "UPDATE incidencias SET tecnico_id = ?, grupo_id = ? WHERE id = ?",
                (tecnico_id, grupo_id, incidencia_id),
            )
        else:
            self._repo._db.execute(
                "UPDATE incidencias SET tecnico_id = ? WHERE id = ?",
                (tecnico_id, incidencia_id),
            )
        if tecnico_id is None:
            accion = "Técnico desasignado"
        else:
            nombre = tecnico_nombre or f"id={tecnico_id}"
            accion = f"Asignada a {nombre}"
            if grupo_id is not None and self._grupos is not None:
                g = self._grupos.obtener_por_id(grupo_id)
                if g:
                    accion = f"Asignada a {nombre} (grupo {g.nombre})"
        self._repo.agregar_historial(incidencia_id, accion, actor_id)
        inc = self._repo.obtener_por_id(incidencia_id)
        assert inc is not None
        self._notificador.notificar(inc, accion)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ASIGNAR,
                AuditEntity.INCIDENCIA,
                incidencia_id,
                accion,
            )
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
        if self._audit:
            self._audit.registrar(
                usuario_id,
                AuditAction.COMENTAR,
                AuditEntity.COMENTARIO,
                comentario.id,
                f"Comentario en incidencia #{incidencia_id}: {preview}",
            )
        rows = self._repo.listar_comentarios(incidencia_id)
        return rows[-1] if rows else comentario

    def actualizar_descripcion(
        self,
        incidencia_id: int,
        descripcion: str,
        *,
        actor_id: int,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> Incidencia:
        """Permite ampliar/corregir la descripción de un ticket no cerrado."""
        inc = self._repo.obtener_por_id(
            incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if rol == Rol.USUARIO:
            if inc.usuario_id != actor_id:
                raise PermissionError("Solo puedes editar tus propias incidencias")
            if inc.estado == EstadoIncidencia.CERRADA:
                raise PermissionError(
                    "No puedes editar la descripción de un ticket cerrado"
                )
        texto = (descripcion or "").strip()
        inc.descripcion = texto
        self._repo.actualizar(inc)
        self._repo.agregar_historial(
            incidencia_id, "Descripción actualizada", actor_id
        )
        return self._repo.obtener_por_id(incidencia_id)  # type: ignore[return-value]

    def agregar_adjunto(
        self,
        incidencia_id: int,
        origen: Path,
        *,
        usuario_id: int,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> Adjunto:
        """Copia un fichero a data/adjuntos/{incidencia_id}/ y registra metadatos."""
        origen = Path(origen)
        if not origen.is_file():
            raise ValueError("El archivo no existe")
        ext = origen.suffix.lower()
        if ext not in ADJUNTO_EXTENSIONES:
            permitidas = ", ".join(sorted(ADJUNTO_EXTENSIONES))
            raise ValueError(f"Tipo no permitido. Usa: {permitidas}")
        tamano = origen.stat().st_size
        if tamano > ADJUNTO_MAX_BYTES:
            raise ValueError("El archivo supera el límite de 10 MB")
        inc = self._repo.obtener_por_id(
            incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if rol == Rol.USUARIO and inc.usuario_id != usuario_id:
            raise PermissionError("Solo puedes adjuntar en tus propias incidencias")

        carpeta = ADJUNTOS_DIR / str(incidencia_id)
        carpeta.mkdir(parents=True, exist_ok=True)
        seguro = "".join(
            ch if ch.isalnum() or ch in "._- " else "_" for ch in origen.name
        ).strip() or "archivo"
        nombre_archivo = f"{uuid.uuid4().hex[:12]}_{seguro}"
        destino = carpeta / nombre_archivo
        shutil.copy2(origen, destino)

        adjunto = Adjunto(
            _incidencia_id=incidencia_id,
            _usuario_id=usuario_id,
            _nombre_original=origen.name,
            _nombre_archivo=nombre_archivo,
            _tamano=tamano,
        )
        adjunto.id = self._repo.crear_adjunto(adjunto)
        self._repo.agregar_historial(
            incidencia_id,
            f"Adjunto añadido: {origen.name}",
            usuario_id,
        )
        if self._audit:
            self._audit.registrar(
                usuario_id,
                AuditAction.ADJUNTAR,
                AuditEntity.ADJUNTO,
                adjunto.id,
                f"Adjunto en incidencia #{incidencia_id}: {origen.name}",
            )
        return adjunto

    def ruta_adjunto(self, adjunto: Adjunto) -> Path:
        return ADJUNTOS_DIR / str(adjunto.incidencia_id) / adjunto.nombre_archivo

    def eliminar_adjunto(
        self,
        adjunto_id: int,
        *,
        actor_id: int,
        rol: Rol,
        es_demo: Optional[bool] = None,
    ) -> None:
        adj = self._repo.obtener_adjunto(adjunto_id)
        if not adj:
            raise ValueError("Adjunto no encontrado")
        inc = self._repo.obtener_por_id(
            adj.incidencia_id, con_detalle=False, es_demo=es_demo
        )
        if not inc:
            raise ValueError("Incidencia no encontrada")
        if rol == Rol.USUARIO and (
            inc.usuario_id != actor_id or adj.usuario_id != actor_id
        ):
            raise PermissionError("Solo puedes eliminar tus propios adjuntos")
        ruta = self.ruta_adjunto(adj)
        self._repo.eliminar_adjunto(adjunto_id)
        if ruta.is_file():
            ruta.unlink()
        self._repo.agregar_historial(
            adj.incidencia_id,
            f"Adjunto eliminado: {adj.nombre_original}",
            actor_id,
        )
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ELIMINAR,
                AuditEntity.ADJUNTO,
                adjunto_id,
                f"Adjunto eliminado de incidencia #{adj.incidencia_id}: {adj.nombre_original}",
            )

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
        """KPIs del dashboard: estados, SLA, técnicos y compatibilidad legacy."""
        abiertas = self._repo.contar(
            usuario_id=usuario_id,
            estado=EstadoIncidencia.ABIERTA,
            es_demo=es_demo,
        )
        en_proceso = self._repo.contar(
            usuario_id=usuario_id,
            estado=EstadoIncidencia.EN_REPARACION,
            es_demo=es_demo,
        )
        pendientes = self._repo.contar(
            usuario_id=usuario_id,
            estado=EstadoIncidencia.PENDIENTE,
            es_demo=es_demo,
        )
        resueltas = self._repo.contar(
            usuario_id=usuario_id,
            estado=EstadoIncidencia.CERRADA,
            es_demo=es_demo,
        )
        abiertas_total = self._repo.contar(
            usuario_id=usuario_id, solo_abiertas=True, es_demo=es_demo
        )

        abiertas_list = self._repo.listar(
            usuario_id=usuario_id, solo_abiertas=True, es_demo=es_demo
        )
        vencidas = sum(1 for inc in abiertas_list if inc.vencida)

        cerradas = self._repo.listar(
            usuario_id=usuario_id,
            estado=EstadoIncidencia.CERRADA,
            es_demo=es_demo,
        )
        sla_ok = 0
        sla_medidas = 0
        for inc in cerradas:
            limite = inc.fecha_limite
            cierre = _parse_fecha_incidencia(inc.fecha_cierre)
            if limite is None or cierre is None:
                continue
            sla_medidas += 1
            if cierre <= limite:
                sla_ok += 1
        sla_pct = (
            round(100.0 * sla_ok / sla_medidas, 1) if sla_medidas else None
        )

        horas: list[float] = []
        for inc in cerradas:
            ini = _parse_fecha_incidencia(inc.fecha_creacion)
            fin = _parse_fecha_incidencia(inc.fecha_cierre)
            if ini and fin and fin >= ini:
                horas.append((fin - ini).total_seconds() / 3600.0)
        tiempo_medio = round(sum(horas) / len(horas), 1) if horas else None

        tech_counts: dict[str, int] = {}
        for inc in abiertas_list:
            nombre = (inc.tecnico_nombre or "").strip() or "Sin asignar"
            tech_counts[nombre] = tech_counts.get(nombre, 0) + 1
        por_tecnico = [
            {"tecnico": k, "total": v}
            for k, v in sorted(
                tech_counts.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ]

        return {
            "abiertas": abiertas,
            "en_proceso": en_proceso,
            "pendientes": pendientes,
            "vencidas": vencidas,
            "resueltas": resueltas,
            "abiertas_total": abiertas_total,
            "sla_cumplimiento_pct": sla_pct,
            "tiempo_medio_horas": tiempo_medio,
            "por_tecnico": por_tecnico,
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

    def __init__(
        self, repo: ComponenteRepository, audit: Optional[AuditService] = None
    ) -> None:
        self._repo = repo
        self._audit = audit

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
        *,
        actor_id: Optional[int] = None,
    ) -> Componente:
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("El nombre del repuesto es obligatorio")
        if stock < 0:
            raise ValueError("El stock no puede ser negativo")
        c = Componente(
            _nombre=nombre,
            _stock=stock,
            _precio=precio,
            _descripcion=descripcion,
            _es_demo=es_demo,
        )
        c.id = self._repo.crear(c)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.CREAR,
                AuditEntity.COMPONENTE,
                c.id,
                f"Creó componente #{c.id} ({nombre}, stock={stock})",
            )
        return c

    def actualizar(
        self, componente: Componente, *, actor_id: Optional[int] = None
    ) -> Componente:
        self._repo.actualizar(componente)
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.ACTUALIZAR,
                AuditEntity.COMPONENTE,
                componente.id,
                f"Actualizó componente #{componente.id} "
                f"({componente.nombre}, stock={componente.stock})",
            )
        return componente

    def eliminar(
        self, componente_id: int, *, actor_id: Optional[int] = None
    ) -> None:
        comp = self._repo.obtener_por_id(componente_id)
        self._repo.eliminar(componente_id)
        if self._audit:
            nombre = comp.nombre if comp else f"#{componente_id}"
            self._audit.registrar(
                actor_id,
                AuditAction.ELIMINAR,
                AuditEntity.COMPONENTE,
                componente_id,
                f"Eliminó componente #{componente_id} ({nombre})",
            )

    def usar_en_incidencia(
        self,
        incidencia_id: int,
        componente_id: int,
        cantidad: int = 1,
        actor_id: Optional[int] = None,
        incidencia_repo: Optional[IncidenciaRepository] = None,
        equipo_repo: Optional[EquipoRepository] = None,
    ) -> None:
        self._repo.asociar_a_incidencia(incidencia_id, componente_id, cantidad)
        comp = self._repo.obtener_por_id(componente_id)
        nombre = comp.nombre if comp else f"#{componente_id}"
        if incidencia_repo is not None:
            incidencia_repo.agregar_historial(
                incidencia_id,
                f"Repuesto usado: {nombre} × {cantidad}",
                actor_id,
            )
            # Relaciona el repuesto también con el equipo del ticket.
            if equipo_repo is not None:
                inc = incidencia_repo.obtener_por_id(
                    incidencia_id, con_detalle=False
                )
                if inc is not None:
                    equipo_repo.anadir_componente(
                        EquipoComponente(
                            _equipo_id=inc.equipo_id,
                            _componente_id=componente_id,
                            _cantidad=max(1, cantidad),
                            _notas=f"Instalado vía {getattr(inc, 'codigo', incidencia_id)}",
                        )
                    )
                    equipo_repo.anadir_reparacion(
                        EquipoReparacion(
                            _equipo_id=inc.equipo_id,
                            _descripcion=f"Repuesto instalado: {nombre} × {cantidad}",
                            _tecnico_id=actor_id,
                            _incidencia_id=incidencia_id,
                        )
                    )
        if self._audit:
            self._audit.registrar(
                actor_id,
                AuditAction.USAR_REPUESTO,
                AuditEntity.COMPONENTE,
                componente_id,
                f"Usó repuesto {nombre} × {cantidad} en incidencia #{incidencia_id}",
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

    def por_dia(self, dias: int = 14, es_demo: Optional[bool] = None) -> list[dict]:
        """Incidencias creadas por día (últimos ``dias``, rellenando ceros)."""
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT date(i.fecha_creacion) AS dia, COUNT(*) AS total
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE date(i.fecha_creacion) >= date('now', 'localtime', ?)
            {extra}
            GROUP BY date(i.fecha_creacion)
            ORDER BY dia
            """,
            [f"-{max(dias - 1, 0)} days", *params],
        )
        by_day = {str(r["dia"]): int(r["total"]) for r in rows}
        hoy = datetime.now().date()
        out: list[dict] = []
        for offset in range(dias - 1, -1, -1):
            d = hoy - timedelta(days=offset)
            key = d.isoformat()
            out.append(
                {
                    "dia": key,
                    "etiqueta": d.strftime("%d/%m"),
                    "total": by_day.get(key, 0),
                }
            )
        return out

    def por_categoria(self, es_demo: Optional[bool] = None) -> list[dict]:
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT COALESCE(NULLIF(i.categoria, ''), 'Otro') AS categoria,
                   COUNT(*) AS total
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE 1=1{extra}
            GROUP BY COALESCE(NULLIF(i.categoria, ''), 'Otro')
            ORDER BY total DESC
            """,
            params,
        )
        result = []
        for r in rows:
            cat = str(r["categoria"])
            # Mostrar hoja del catálogo si viene como Familia/Hoja.
            etiqueta = cat.split("/")[-1] if "/" in cat else cat
            result.append({"categoria": etiqueta, "total": int(r["total"])})
        return result

    def tiempo_medio_por_dia(
        self, dias: int = 14, es_demo: Optional[bool] = None
    ) -> list[dict]:
        """Media de horas de resolución de tickets cerrados cada día."""
        extra, params = self._filtro_demo_sql(es_demo)
        rows = self._db.fetchall(
            f"""
            SELECT date(i.fecha_cierre) AS dia,
                   AVG(
                       (julianday(i.fecha_cierre) - julianday(i.fecha_creacion)) * 24.0
                   ) AS media
            FROM incidencias i
            JOIN equipos e ON e.id = i.equipo_id
            JOIN usuarios u ON u.id = e.usuario_id
            WHERE i.fecha_cierre IS NOT NULL
              AND date(i.fecha_cierre) >= date('now', 'localtime', ?)
            {extra}
            GROUP BY date(i.fecha_cierre)
            ORDER BY dia
            """,
            [f"-{max(dias - 1, 0)} days", *params],
        )
        by_day = {
            str(r["dia"]): round(float(r["media"]), 1)
            for r in rows
            if r["media"] is not None
        }
        hoy = datetime.now().date()
        out: list[dict] = []
        for offset in range(dias - 1, -1, -1):
            d = hoy - timedelta(days=offset)
            key = d.isoformat()
            out.append(
                {
                    "dia": key,
                    "etiqueta": d.strftime("%d/%m"),
                    "media": by_day.get(key, 0.0),
                }
            )
        return out

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
