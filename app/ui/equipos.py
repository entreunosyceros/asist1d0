"""
Vista de equipos informáticos.

Árbol usuario → equipo → incidencias, con alta/edición según el rol
(el usuario final solo gestiona sus propios equipos).
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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.enums import Rol
from app.ui.page_chrome import EmptyState, apply_page_margins, build_page_header, show_toast


class EquipoDialog(QDialog):
    """Formulario modal para registrar o editar un equipo."""

    def __init__(self, ctx: AppContext, session: SessionContext, equipo=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Equipo")
        self._equipo = equipo
        layout = QFormLayout(self)

        self.usuario = QComboBox()
        usuarios = ctx.usuarios.listar(solo_activos=True, es_demo=session.es_demo)
        for u in usuarios:
            if u.rol == Rol.USUARIO or u.es_admin():
                self.usuario.addItem(u.nombre, u.id)
        if session.rol == Rol.USUARIO:
            self.usuario.clear()
            self.usuario.addItem(session.usuario.nombre, session.usuario_id)
            self.usuario.setEnabled(False)

        self.serie = QLineEdit()
        self.marca = QLineEdit()
        self.modelo = QLineEdit()
        self.so = QLineEdit()

        if equipo:
            idx = self.usuario.findData(equipo.usuario_id)
            if idx >= 0:
                self.usuario.setCurrentIndex(idx)
            self.serie.setText(equipo.numero_serie)
            self.marca.setText(equipo.marca)
            self.modelo.setText(equipo.modelo)
            self.so.setText(equipo.sistema_operativo)

        layout.addRow("Usuario", self.usuario)
        layout.addRow("Nº serie", self.serie)
        layout.addRow("Marca", self.marca)
        layout.addRow("Modelo", self.modelo)
        layout.addRow("Sistema operativo", self.so)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def datos(self):
        return {
            "usuario_id": self.usuario.currentData(),
            "numero_serie": self.serie.text().strip(),
            "marca": self.marca.text().strip(),
            "modelo": self.modelo.text().strip(),
            "sistema_operativo": self.so.text().strip(),
        }


class EquiposView(QWidget):
    """Página de equipos con árbol jerárquico e incidencias hijas."""

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
        if self._session.es_tecnico() or self._session.rol == Rol.USUARIO:
            btn = QPushButton("+ Nuevo equipo")
            btn.clicked.connect(self._nuevo)
            actions.append(btn)
            if self._session.es_admin() or self._session.es_tecnico():
                btn_edit = QPushButton("Editar")
                btn_edit.setObjectName("SecondaryButton")
                btn_edit.clicked.connect(self._editar)
                btn_del = QPushButton("Eliminar")
                btn_del.setObjectName("DangerButton")
                btn_del.clicked.connect(self._eliminar)
                actions.extend([btn_edit, btn_del])
        header, self._status = build_page_header(
            "Equipos",
            "Inventario de hardware por usuario",
            actions=actions or None,
        )
        layout.addLayout(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Elemento", "Detalle"])
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)
        self.empty = EmptyState(
            "No hay equipos registrados.",
            "+ Nuevo equipo",
            self._nuevo if (self._session.es_tecnico() or self._session.rol == Rol.USUARIO) else None,
        )
        layout.addWidget(self.empty)
        self.empty.hide()

    def refresh(self) -> None:
        self.tree.clear()
        uid = self._session.usuario_id if self._session.rol == Rol.USUARIO else None
        equipos = self._ctx.equipos.listar(
            usuario_id=uid, es_demo=self._session.es_demo
        )

        # Agrupar por usuario
        por_usuario: dict[str, list] = {}
        for eq in equipos:
            key = eq.usuario_nombre or f"Usuario #{eq.usuario_id}"
            por_usuario.setdefault(key, []).append(eq)

        for nombre_usuario, eqs in por_usuario.items():
            user_item = QTreeWidgetItem([f"👤 {nombre_usuario}", f"{len(eqs)} equipo(s)"])
            self.tree.addTopLevelItem(user_item)
            for eq in eqs:
                eq_item = QTreeWidgetItem(
                    [
                        f"💻 {eq.nombre_completo}",
                        f"S/N {eq.numero_serie} · {eq.sistema_operativo}",
                    ]
                )
                eq_item.setData(0, Qt.ItemDataRole.UserRole, eq.id)
                user_item.addChild(eq_item)
                for inc in self._ctx.incidencias.listar(
                    equipo_id=eq.id, es_demo=self._session.es_demo
                ):
                    inc_item = QTreeWidgetItem(
                        [f"🎫 {inc.codigo} {inc.prioridad.icono} {inc.titulo}", inc.estado.value]
                    )
                    eq_item.addChild(inc_item)
            user_item.setExpanded(True)
        self.tree.resizeColumnToContents(0)
        self.tree.setVisible(bool(equipos))
        self.empty.setVisible(not equipos)

    def _equipo_seleccionado(self):
        item = self.tree.currentItem()
        if not item:
            return None
        eq_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not eq_id:
            return None
        return self._ctx.equipos.obtener(eq_id)

    def _nuevo(self) -> None:
        dlg = EquipoDialog(self._ctx, self._session, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        try:
            self._ctx.equipos.crear(**data)
            self.refresh()
            show_toast(self._status, "Equipo creado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _editar(self) -> None:
        eq = self._equipo_seleccionado()
        if not eq:
            show_toast(self._status, "Selecciona un equipo.", error=True)
            return
        dlg = EquipoDialog(self._ctx, self._session, equipo=eq, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        eq.usuario_id = data["usuario_id"]
        eq.numero_serie = data["numero_serie"]
        eq.marca = data["marca"]
        eq.modelo = data["modelo"]
        eq.sistema_operativo = data["sistema_operativo"]
        try:
            self._ctx.equipos.actualizar(eq)
            self.refresh()
            show_toast(self._status, "Equipo actualizado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _eliminar(self) -> None:
        eq = self._equipo_seleccionado()
        if not eq:
            return
        if QMessageBox.question(
            self, "Eliminar", f"¿Eliminar {eq}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self._ctx.equipos.eliminar(eq.id)  # type: ignore[arg-type]
        self.refresh()
        show_toast(self._status, "Equipo eliminado.")
