"""
Punto de entrada de Asist{1d0}.

Orquesta el ciclo de vida:

1. Mostrar login (modal, sin bordes).
2. Tras autenticarse, abrir la ventana principal y el icono de bandeja.
3. Al cerrar sesión, volver al login (sin bandeja).
4. Si se cierra el login sin entrar, terminar la aplicación.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog

from app.bootstrap import AppContext, bootstrap
from app.config import APP_NAME
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.resources import load_app_icon
from app.ui.styles import STYLESHEET
from app.ui.tray import AppTray


class Application:
    """Controlador de alto nivel: login, ventana principal y bandeja."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        self._main: MainWindow | None = None
        self._tray: AppTray | None = None
        # True solo cuando hay sesión abierta (hace falta para app.exec()).
        self.running = False

    def start(self) -> None:
        """Arranca mostrando la pantalla de acceso."""
        self.show_login()

    def show_login(self) -> None:
        """Cierra la sesión/ventana actual y muestra el diálogo de login."""
        self._hide_tray()
        if self._main is not None:
            self._main.set_tray_enabled(False)
            self._main.force_close()
            self._main.deleteLater()
            self._main = None

        self._ctx.incidencias.set_tray_notifier(None, None)
        self._ctx.auth.logout()
        login = LoginWindow(self._ctx.auth)
        # exec() modal: una sola ventana de acceso; al aceptar abrimos la principal.
        if login.exec() == QDialog.DialogCode.Accepted and login.session is not None:
            self._open_main(login.session)
            self.running = True
        else:
            # Usuario cerró el login (X / Escape) → salir de la app por completo.
            self.running = False
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def _open_main(self, session) -> None:
        """Crea la ventana principal y activa la bandeja del sistema."""
        if self._main is not None:
            self._main.set_tray_enabled(False)
            self._main.force_close()
            self._main.deleteLater()
        self._main = MainWindow(self._ctx, session)
        self._main.logout_requested.connect(self.show_login)
        self._setup_tray(session)
        self._main.show()

    def _setup_tray(self, session) -> None:
        """Configura el menú de bandeja según el rol y muestra el icono."""
        assert self._main is not None
        if self._tray is None:
            self._tray = AppTray()
            self._tray.show_window_requested.connect(self._show_main)
            self._tray.navigate_requested.connect(self._navigate)
            self._tray.change_password_requested.connect(self._password_from_tray)
            self._tray.logout_requested.connect(self._logout_from_tray)
            self._tray.help_requested.connect(self._help_from_tray)
            self._tray.portal_requested.connect(self._portal_from_tray)
            self._tray.about_requested.connect(self._about_from_tray)
            self._tray.quit_requested.connect(self._quit_app)

        self._tray.bind(session, self._main.page_names)
        if self._tray.available:
            self._main.set_tray_enabled(True)
            self._ctx.incidencias.set_tray_notifier(
                self._tray.notify,
                session.usuario_id,
            )
            self._tray.show()
            self._tray.notify(
                APP_NAME,
                f"Sesión iniciada: {session.usuario.nombre}",
            )
        else:
            self._ctx.incidencias.set_tray_notifier(None, None)
            # Escritorios sin bandeja: el cierre de ventana termina con normalidad.
            self._main.set_tray_enabled(False)

    def _hide_tray(self) -> None:
        if self._tray is not None:
            self._tray.hide()

    def _show_main(self) -> None:
        if self._main is not None:
            self._main.bring_to_front()

    def _navigate(self, index: int) -> None:
        if self._main is not None:
            self._main.navigate_to(index)

    def _password_from_tray(self) -> None:
        if self._main is not None:
            self._main.change_own_password()

    def _logout_from_tray(self) -> None:
        if self._main is not None:
            self._main.request_logout()

    def _help_from_tray(self) -> None:
        if self._main is not None:
            self._main.show_help()

    def _about_from_tray(self) -> None:
        if self._main is not None:
            self._main.show_about()

    def _portal_from_tray(self) -> None:
        if self._main is not None:
            self._main.open_portal()

    def _quit_app(self) -> None:
        """Salida completa pedida desde la bandeja (opción «Salir»)."""
        from app.portal_launcher import stop_portal_if_owned

        stop_portal_if_owned()
        self._hide_tray()
        if self._main is not None:
            self._main.set_tray_enabled(False)
            self._main.force_close()
            self._main.deleteLater()
            self._main = None
        self.running = False
        app = QApplication.instance()
        if app is not None:
            app.quit()


def main() -> int:
    """Inicializa Qt, el estilo Fusion claro y el controlador de aplicación."""
    ctx = bootstrap()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    # Con bandeja activa, cerrar la ventana no debe matar el proceso.
    app.setQuitOnLastWindowClosed(False)

    from PySide6.QtGui import QColor, QPalette

    # Paleta clara coherente con el stylesheet de la UI.
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f4f6fb"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f8fafc"))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)

    icon = load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    controller = Application(ctx)
    controller.start()
    # Si el login se cerró antes de arrancar el bucle, no dejar la app colgada.
    if not controller.running:
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
