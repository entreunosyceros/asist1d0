"""
Icono de bandeja del sistema tras el login.

Muestra el logo de la aplicación y un menú contextual con acciones
típicas: mostrar ventana, navegar por secciones, sesión, ayuda y salir.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.auth.service import SessionContext
from app.config import APP_NAME
from app.ui.resources import load_app_icon


class AppTray(QObject):
    """Controlador del ``QSystemTrayIcon`` y de su menú contextual."""

    show_window_requested = Signal()
    navigate_requested = Signal(int)
    change_password_requested = Signal()
    logout_requested = Signal()
    help_requested = Signal()
    portal_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(self)
        icon = load_app_icon()
        if icon is not None:
            self._tray.setIcon(icon)
        self._tray.setToolTip(APP_NAME)
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def bind(self, session: SessionContext, page_names: list[str]) -> None:
        """Reconstruye el menú contextual según el rol y las secciones visibles."""
        self._menu.clear()
        ambito = "demo" if session.es_demo else "real"
        self._tray.setToolTip(
            f"{APP_NAME}\n{session.usuario.nombre} · {session.rol.etiqueta} · {ambito}"
        )

        act_show = QAction(f"Mostrar {APP_NAME}", self._menu)
        act_show.triggered.connect(self.show_window_requested.emit)
        self._menu.addAction(act_show)

        if page_names:
            menu_ir = self._menu.addMenu("Ir")
            for i, name in enumerate(page_names):
                action = QAction(name, menu_ir)
                action.triggered.connect(
                    lambda checked=False, idx=i: self.navigate_requested.emit(idx)
                )
                menu_ir.addAction(action)

        self._menu.addSeparator()

        act_pwd = QAction("Cambiar mi contraseña…", self._menu)
        act_pwd.triggered.connect(self.change_password_requested.emit)
        self._menu.addAction(act_pwd)

        act_logout = QAction("Cerrar sesión", self._menu)
        act_logout.triggered.connect(self.logout_requested.emit)
        self._menu.addAction(act_logout)

        self._menu.addSeparator()

        act_help = QAction("Guía de uso…", self._menu)
        act_help.triggered.connect(self.help_requested.emit)
        self._menu.addAction(act_help)

        act_portal = QAction("Abrir portal web…", self._menu)
        act_portal.triggered.connect(self.portal_requested.emit)
        self._menu.addAction(act_portal)

        act_about = QAction(f"Acerca de {APP_NAME}…", self._menu)
        act_about.triggered.connect(self.about_requested.emit)
        self._menu.addAction(act_about)

        self._menu.addSeparator()

        act_quit = QAction("Salir", self._menu)
        act_quit.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(act_quit)

    def show(self) -> None:
        if self.available and not self._tray.icon().isNull():
            self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def notify(self, title: str, message: str) -> None:
        """Aviso del sistema; si la bandeja no está visible, no hace nada."""
        if not self._tray.isVisible():
            return
        # show() refuerza el icono en algunos escritorios Linux antes del globo.
        self._tray.show()
        self._tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            4500,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window_requested.emit()
