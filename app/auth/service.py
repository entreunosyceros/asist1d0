"""
Sesión de usuario y servicio de autenticación.

``SessionContext`` expone el usuario autenticado y helpers de permisos por rol.
``AuthService`` gestiona login, logout y el cambio de contraseña del administrador.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.auth.password import hash_password, verify_password
from app.database.repositories.usuario_repository import UsuarioRepository
from app.models.enums import Rol
from app.models.usuario import Usuario


@dataclass
class SessionContext:
    """Contexto de la sesión activa tras un login correcto."""

    usuario: Usuario

    @property
    def usuario_id(self) -> int:
        """Identificador del usuario en sesión."""
        return self.usuario.id  # type: ignore[return-value]

    @property
    def rol(self) -> Rol:
        """Rol efectivo del usuario (Usuario / Técnico / Administrador)."""
        return self.usuario.rol

    @property
    def es_demo(self) -> bool:
        """True si la sesión es de una cuenta de demostración."""
        return self.usuario.es_demo

    def es_admin(self) -> bool:
        """Indica si el usuario tiene rol administrador."""
        return self.usuario.es_admin()

    def es_tecnico(self) -> bool:
        """Indica si el usuario tiene rol técnico."""
        return self.usuario.es_tecnico()

    def puede_gestionar_usuarios(self) -> bool:
        """Solo el administrador puede crear/editar/eliminar cuentas."""
        return self.es_admin()

    def puede_gestionar_inventario(self) -> bool:
        """Admin y técnico pueden gestionar el stock de repuestos."""
        return self.es_admin() or self.usuario.rol == Rol.TECNICO

    def puede_ver_informes_globales(self) -> bool:
        """Informes globales disponibles para admin y técnico."""
        return self.es_admin() or self.usuario.rol == Rol.TECNICO

    def puede_ver_panel_tecnico(self) -> bool:
        """Acceso al panel de consultas, historial y logs."""
        return self.usuario.puede_ver_panel_tecnico()


class AuthService:
    """Autenticación contra el repositorio de usuarios."""

    def __init__(self, usuario_repo: UsuarioRepository) -> None:
        self._repo = usuario_repo
        self._session: Optional[SessionContext] = None

    @property
    def session(self) -> Optional[SessionContext]:
        """Sesión actual o None si no hay usuario autenticado."""
        return self._session

    def login(self, email: str, password: str) -> SessionContext:
        """Valida credenciales y abre sesión. Lanza PermissionError si fallan."""
        usuario = self._repo.obtener_por_email(email)
        if not usuario or not usuario.activo:
            raise PermissionError("Credenciales incorrectas")
        if not verify_password(password, usuario.password_hash):
            raise PermissionError("Credenciales incorrectas")
        self._session = SessionContext(usuario=usuario)
        return self._session

    def logout(self) -> None:
        """Cierra la sesión en memoria (no afecta a la base de datos)."""
        self._session = None

    def require_session(self) -> SessionContext:
        """Devuelve la sesión o error si no hay usuario autenticado."""
        if not self._session:
            raise PermissionError("No hay sesión activa")
        return self._session

    def cambiar_propia_contraseña(self, actual: str, nueva: str) -> None:
        """
        Permite al usuario autenticado cambiar su propia contraseña.

        Exige la contraseña actual correcta y una nueva distinta (mín. 6 caracteres).
        """
        session = self.require_session()
        if not actual or not nueva:
            raise ValueError("Debes indicar la contraseña actual y la nueva")
        if len(nueva) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres")
        if actual == nueva:
            raise ValueError("La nueva contraseña debe ser distinta de la actual")
        if not verify_password(actual, session.usuario.password_hash):
            raise PermissionError("La contraseña actual no es correcta")
        session.usuario.password_hash = hash_password(nueva)
        self._repo.actualizar(session.usuario)

    def crear_usuario(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: Rol = Rol.USUARIO,
        telefono: str = "",
    ) -> Usuario:
        """Alta rápida de usuario (hash de contraseña incluido)."""
        if self._repo.obtener_por_email(email):
            raise ValueError("Ya existe un usuario con ese email")
        usuario = Usuario(
            _nombre=nombre,
            _email=email.lower(),
            _telefono=telefono,
            _password_hash=hash_password(password),
            _rol=rol,
        )
        usuario.id = self._repo.crear(usuario)
        return usuario
