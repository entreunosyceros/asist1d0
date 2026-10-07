"""
Vista de usuarios.

El administrador gestiona altas/edición/bajas y puede cambiar su propia
contraseña. El técnico solo consulta el listado (solo lectura).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.enums import Rol
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.page_chrome import apply_page_margins, build_page_header, show_toast


class UsuarioDialog(QDialog):
    """Formulario modal para crear o editar una cuenta."""

    def __init__(self, usuario=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo usuario" if usuario is None else "Editar usuario")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        self.nombre = QLineEdit()
        self.email = QLineEdit()
        self.telefono = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(
            "Dejar vacío para no cambiar" if usuario else "Obligatoria"
        )
        self.rol = QComboBox()
        for r in Rol:
            self.rol.addItem(r.etiqueta, r.value)

        if usuario:
            self.nombre.setText(usuario.nombre)
            self.email.setText(usuario.email)
            self.telefono.setText(usuario.telefono)
            idx = self.rol.findData(usuario.rol.value)
            if idx >= 0:
                self.rol.setCurrentIndex(idx)

        layout.addRow("Nombre", self.nombre)
        layout.addRow("Email", self.email)
        layout.addRow("Teléfono", self.telefono)
        layout.addRow("Contraseña", self.password)
        layout.addRow("Rol", self.rol)

        if usuario is None:
            nota = QLabel(
                "Los usuarios creados aquí son cuentas reales (no demo).\n"
                "Roles: Usuario · Técnico · Administrador"
            )
            nota.setStyleSheet("color: #6b7280; font-size: 11px;")
            nota.setWordWrap(True)
            layout.addRow(nota)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def rol_seleccionado(self) -> Rol:
        return Rol(self.rol.currentData())


class UsuariosView(QWidget):
    """Página de listado y gestión de usuarios según permisos de la sesión."""

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._status = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        actions = []
        can_edit = self._session.puede_gestionar_usuarios()
        if can_edit:
            btn_new = QPushButton("+ Nuevo usuario")
            btn_new.clicked.connect(self._nuevo)
            btn_edit = QPushButton("Editar")
            btn_edit.setObjectName("SecondaryButton")
            btn_edit.clicked.connect(self._editar)
            btn_pwd = QPushButton("Mi contraseña")
            btn_pwd.setObjectName("SecondaryButton")
            btn_pwd.clicked.connect(self._cambiar_mi_password)
            btn_del = QPushButton("Eliminar")
            btn_del.setObjectName("DangerButton")
            btn_del.clicked.connect(self._eliminar)
            actions.extend([btn_new, btn_edit, btn_pwd, btn_del])
        header, self._status = build_page_header(
            "Usuarios",
            "Gestión de cuentas, roles y tu propia contraseña"
            if can_edit
            else "Consulta de usuarios (solo lectura)",
            actions=actions or None,
        )
        layout.addLayout(header)

        if self._session.es_demo and self._session.es_admin():
            aviso = QLabel(
                "Modo demostración: puedes crear usuarios reales con cualquier rol. "
                "Sus equipos e incidencias no serán visibles para las cuentas demo."
            )
            aviso.setWordWrap(True)
            aviso.setObjectName("PageSubtitle")
            layout.addWidget(aviso)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Nombre", "Email", "Teléfono", "Rol", "Tipo", "Activo"]
        )
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)

    def refresh(self) -> None:
        # Admin demo ve todos (para gestionar altas); admin real solo usuarios reales.
        if self._session.es_demo:
            usuarios = self._ctx.usuarios.listar()
        else:
            usuarios = self._ctx.usuarios.listar(es_demo=False)
        self.tabla.setRowCount(0)
        for u in usuarios:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            valores = [
                u.nombre,
                u.email,
                u.telefono,
                u.rol.etiqueta,
                "Demo" if u.es_demo else "Real",
                "Sí" if u.activo else "No",
            ]
            for col, val in enumerate(valores):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, u.id)
                self.tabla.setItem(row, col, item)
        self.tabla.resizeColumnsToContents()

    def _seleccionado(self):
        items = self.tabla.selectedItems()
        if not items:
            return None
        uid = items[0].data(Qt.ItemDataRole.UserRole)
        return self._ctx.usuarios.obtener(uid)

    def _cambiar_mi_password(self) -> None:
        dlg = ChangePasswordDialog(self._ctx.auth, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            show_toast(self._status, "Tu contraseña se ha actualizado correctamente.")

    def _nuevo(self) -> None:
        dlg = UsuarioDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.password.text():
            QMessageBox.warning(self, "Usuario", "La contraseña es obligatoria.")
            return
        try:
            creado = self._ctx.usuarios.crear(
                nombre=dlg.nombre.text().strip(),
                email=dlg.email.text().strip(),
                password=dlg.password.text(),
                rol=dlg.rol_seleccionado(),
                telefono=dlg.telefono.text().strip(),
                es_demo=False,
            )
            self.refresh()
            show_toast(
                self._status,
                f"Cuenta real creada: {creado.email} ({creado.rol.etiqueta})",
            )
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _editar(self) -> None:
        u = self._seleccionado()
        if not u:
            return
        if self._session.es_demo and not u.es_demo and not self._session.es_admin():
            QMessageBox.warning(self, "Usuarios", "No puedes editar esa cuenta.")
            return
        dlg = UsuarioDialog(usuario=u, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        nuevo_rol = dlg.rol_seleccionado()
        if (
            u.id == self._session.usuario_id
            and u.es_admin()
            and nuevo_rol != Rol.ADMINISTRADOR
        ):
            QMessageBox.warning(
                self,
                "Usuarios",
                "No puedes quitarte el rol de administrador a ti mismo.",
            )
            return
        try:
            # No permitir convertir demo↔real desde la UI
            self._ctx.usuarios.actualizar(
                u,
                nombre=dlg.nombre.text().strip(),
                email=dlg.email.text().strip(),
                telefono=dlg.telefono.text().strip(),
                rol=nuevo_rol,
                password=dlg.password.text() or None,
                actor_id=self._session.usuario_id,
            )
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _eliminar(self) -> None:
        u = self._seleccionado()
        if not u:
            return
        if u.id == self._session.usuario_id:
            QMessageBox.warning(self, "Usuarios", "No puedes eliminarte a ti mismo.")
            return
        # Admin real no gestiona demos; admin demo puede borrar demos y reales que creó
        if not self._session.es_demo and u.es_demo:
            QMessageBox.warning(
                self, "Usuarios", "No puedes eliminar cuentas de demostración."
            )
            return
        if QMessageBox.question(
            self, "Eliminar", f"¿Eliminar a {u.nombre}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self._ctx.usuarios.eliminar(u.id, actor_id=self._session.usuario_id)  # type: ignore[arg-type]
        self.refresh()
