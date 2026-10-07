"""
Ventana principal de Asist{1d0}.

Muestra un sidebar con las secciones permitidas por rol, un menú
superior (Sesión / Ir / Ayuda) y carga las páginas de forma diferida
para evitar inicializar toda la UI de golpe.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.config import APP_NAME, APP_VERSION
from app.models.enums import Rol
from app.ui.about_dialog import AboutDialog
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.dashboard import DashboardView
from app.ui.equipos import EquiposView
from app.ui.help_dialog import HelpDialog
from app.ui.incidencias import IncidenciasView
from app.ui.informes import InformesView
from app.ui.inventario import InventarioView
from app.ui.panel_tecnico import PanelTecnicoView
from app.ui.resources import apply_window_icon, logo_label
from app.ui.usuarios import UsuariosView


class MainWindow(QMainWindow):
    """Shell de la aplicación autenticada (sidebar + stack de vistas)."""

    # Emitida al pedir cierre de sesión (sidebar, menú o bandeja).
    logout_requested = Signal()

    def __init__(self, ctx: AppContext, session: SessionContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._session = session
        self._logging_out = False
        self._force_quit = False
        self._tray_enabled = False
        self._page_factories: list[Callable[[], QWidget]] = []
        self._page_created: list[bool] = []
        self._page_names: list[str] = []
        self._nav_buttons: list[QPushButton] = []
        self.setWindowTitle(f"{APP_NAME} — Soporte Técnico")
        self.resize(1180, 720)
        apply_window_icon(self)
        self._build()
        self._build_menu()

    @property
    def page_names(self) -> list[str]:
        return list(self._page_names)

    def set_tray_enabled(self, enabled: bool) -> None:
        self._tray_enabled = enabled

    def bring_to_front(self) -> None:
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def navigate_to(self, index: int) -> None:
        self.bring_to_front()
        self._goto_from_menu(index)

    def show_help(self) -> None:
        self.bring_to_front()
        self._show_help()

    def show_about(self) -> None:
        self.bring_to_front()
        self._show_about()

    def open_portal(self) -> None:
        """Arranca la API si hace falta y abre el portal en el navegador."""
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QApplication, QMessageBox

        from app.portal_launcher import is_portal_up, open_portal

        try:
            if not is_portal_up():
                QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                url = open_portal()
            finally:
                QApplication.restoreOverrideCursor()
            QMessageBox.information(
                self,
                "Portal web",
                f"Portal disponible en:\n{url}\n\n"
                "Usa la misma cuenta que en el escritorio.",
            )
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(
                self,
                "Portal web",
                f"No se pudo abrir el portal:\n{exc}",
            )

    def request_logout(self) -> None:
        self._logout()

    def change_own_password(self) -> None:
        self.bring_to_front()
        self._cambiar_password()

    def force_close(self) -> None:
        self._force_quit = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Con bandeja activa, la X oculta la ventana en lugar de cerrar la app.
        if self._force_quit or self._logging_out or not self._tray_enabled:
            event.accept()
            return
        self.hide()
        event.ignore()

    def _build_menu(self) -> None:
        """Menú superior adaptado al rol (Sesión / Ir / Ayuda)."""

        menubar: QMenuBar = self.menuBar()
        menubar.clear()

        menu_sesion = menubar.addMenu("&Sesión")
        act_pwd = QAction("Cambiar mi contraseña…", self)
        act_pwd.triggered.connect(self._cambiar_password)
        menu_sesion.addAction(act_pwd)
        menu_sesion.addSeparator()
        act_logout = QAction("Cerrar sesión", self)
        act_logout.setShortcut(QKeySequence("Ctrl+L"))
        act_logout.triggered.connect(self._logout)
        menu_sesion.addAction(act_logout)

        menu_ir = menubar.addMenu("&Ir")
        for i, name in enumerate(self._page_names):
            action = QAction(name, self)
            action.triggered.connect(
                lambda checked=False, idx=i: self._goto_from_menu(idx)
            )
            menu_ir.addAction(action)

        menu_ayuda = menubar.addMenu("A&yuda")
        act_help = QAction("Guía de uso…", self)
        act_help.setShortcut(QKeySequence.StandardKey.HelpContents)
        act_help.triggered.connect(self._show_help)
        menu_ayuda.addAction(act_help)
        act_portal = QAction("Abrir portal web…", self)
        act_portal.triggered.connect(self.open_portal)
        menu_ayuda.addAction(act_portal)
        act_about = QAction(f"Acerca de {APP_NAME}…", self)
        act_about.triggered.connect(self._show_about)
        menu_ayuda.addAction(act_about)

    def _goto_from_menu(self, index: int) -> None:
        self._goto(index)
        if 0 <= index < len(self._nav_buttons):
            self._nav_buttons[index].setChecked(True)

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _show_help(self) -> None:
        HelpDialog(self._session, self).exec()

    def _cambiar_password(self) -> None:
        from PySide6.QtWidgets import QDialog, QMessageBox

        dlg = ChangePasswordDialog(self._ctx.auth, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self,
                "Contraseña",
                "Tu contraseña se ha actualizado correctamente.",
            )

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        slay = QVBoxLayout(sidebar)
        slay.setContentsMargins(0, 8, 0, 16)
        slay.setSpacing(2)

        logo = logo_label(40)
        if logo is not None:
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slay.addWidget(logo)

        title = QLabel(APP_NAME)
        title.setObjectName("SidebarTitle")
        user = QLabel(
            f"{self._session.usuario.nombre}\n{self._session.rol.etiqueta} · v{APP_VERSION}"
        )
        user.setObjectName("SidebarUser")
        slay.addWidget(title)
        slay.addWidget(user)

        self._stack = QStackedWidget()
        self._stack.setObjectName("ContentArea")
        self._buttons = QButtonGroup(self)
        self._buttons.setExclusive(True)

        if self._session.rol == Rol.USUARIO:
            defs: list[tuple[str, Callable[[], QWidget]]] = [
                ("Dashboard", self._make_dashboard),
                ("Incidencias", lambda: IncidenciasView(self._ctx, self._session)),
                ("Equipos", self._make_equipos),
            ]
        else:
            defs = [
                ("Dashboard", self._make_dashboard),
                ("Incidencias", lambda: IncidenciasView(self._ctx, self._session)),
                ("Equipos", self._make_equipos),
                ("Usuarios", lambda: UsuariosView(self._ctx, self._session)),
                ("Inventario", lambda: InventarioView(self._ctx, self._session)),
                ("Informes", lambda: InformesView(self._ctx, self._session)),
                ("Panel técnico", lambda: PanelTecnicoView(self._ctx, self._session)),
            ]

        first = True
        for label, factory in defs:
            placeholder = QWidget()
            idx = self._stack.addWidget(placeholder)
            self._page_factories.append(factory)
            self._page_created.append(False)
            self._page_names.append(label)
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(first)
            btn.clicked.connect(lambda checked=False, i=idx: self._goto(i))
            self._buttons.addButton(btn)
            self._nav_buttons.append(btn)
            slay.addWidget(btn)
            first = False

        slay.addStretch()
        btn_logout = QPushButton("Cerrar sesión")
        btn_logout.setObjectName("SecondaryButton")
        btn_logout.clicked.connect(self._logout)
        slay.addWidget(btn_logout)

        root.addWidget(sidebar)
        root.addWidget(self._stack, 1)

        self._ensure_page(0)
        self._stack.setCurrentIndex(0)

    def _make_dashboard(self) -> DashboardView:
        dash = DashboardView(self._ctx, self._session)
        dash.abrir_incidencia.connect(self.abrir_incidencia)
        dash.solicitar_nueva_incidencia.connect(self.abrir_nueva_incidencia)
        dash.solicitar_nuevo_equipo.connect(self.abrir_equipos)
        return dash

    def _make_equipos(self) -> EquiposView:
        view = EquiposView(self._ctx, self._session)
        view.abrir_incidencia.connect(self.abrir_incidencia)
        return view

    def _page_index(self, name: str) -> int | None:
        try:
            return self._page_names.index(name)
        except ValueError:
            return None

    def abrir_incidencia(self, incidencia_id: int) -> None:
        idx = self._page_index("Incidencias")
        if idx is None:
            return
        self._goto(idx)
        widget = self._stack.widget(idx)
        if isinstance(widget, IncidenciasView):
            widget.seleccionar_incidencia(incidencia_id)
        if 0 <= idx < len(self._nav_buttons):
            self._nav_buttons[idx].setChecked(True)

    def abrir_nueva_incidencia(self) -> None:
        idx = self._page_index("Incidencias")
        if idx is None:
            return
        self._goto(idx)
        widget = self._stack.widget(idx)
        if isinstance(widget, IncidenciasView):
            widget.nueva_incidencia()
        if 0 <= idx < len(self._nav_buttons):
            self._nav_buttons[idx].setChecked(True)

    def abrir_equipos(self) -> None:
        idx = self._page_index("Equipos")
        if idx is None:
            return
        self._goto(idx)
        if 0 <= idx < len(self._nav_buttons):
            self._nav_buttons[idx].setChecked(True)

    def _ensure_page(self, index: int) -> None:
        """Crea la vista bajo demanda la primera vez que se visita."""
        if self._page_created[index]:
            return
        widget = self._page_factories[index]()
        old = self._stack.widget(index)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(index, widget)
        self._page_created[index] = True

    def _goto(self, index: int) -> None:
        """Navega a una sección y refresca su contenido si aplica."""
        self._ensure_page(index)
        self._stack.setCurrentIndex(index)
        widget = self._stack.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _logout(self) -> None:
        """Cierra sesión y notifica al controlador para volver al login."""
        self._logging_out = True
        self._ctx.auth.logout()
        self.logout_requested.emit()
        self.close()
