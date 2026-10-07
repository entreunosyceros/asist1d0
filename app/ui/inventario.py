"""
Vista de inventario de componentes / repuestos.

Permite a técnico y administrador mantener el stock que luego se
consume al reparar incidencias.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.ui.page_chrome import EmptyState, apply_page_margins, build_page_header, show_toast


class ComponenteDialog(QDialog):
    """Formulario modal de alta/edición de un componente de inventario."""

    def __init__(self, componente=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Componente")
        layout = QFormLayout(self)
        self.nombre = QLineEdit()
        self.stock = QSpinBox()
        self.stock.setRange(0, 100000)
        self.precio = QDoubleSpinBox()
        self.precio.setRange(0, 100000)
        self.precio.setDecimals(2)
        self.precio.setSuffix(" €")
        self.descripcion = QTextEdit()
        self.descripcion.setMaximumHeight(80)

        if componente:
            self.nombre.setText(componente.nombre)
            self.stock.setValue(componente.stock)
            self.precio.setValue(componente.precio)
            self.descripcion.setPlainText(componente.descripcion)

        layout.addRow("Nombre", self.nombre)
        layout.addRow("Stock", self.stock)
        layout.addRow("Precio", self.precio)
        layout.addRow("Descripción", self.descripcion)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class InventarioView(QWidget):
    """Página de inventario: listado de componentes y control de stock."""

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
        can_edit = self._session.puede_gestionar_inventario()
        if can_edit:
            btn_new = QPushButton("+ Nuevo repuesto")
            btn_new.clicked.connect(self._nuevo)
            btn_edit = QPushButton("Editar")
            btn_edit.setObjectName("SecondaryButton")
            btn_edit.clicked.connect(self._editar)
            btn_stock = QPushButton("+ Stock")
            btn_stock.setObjectName("SecondaryButton")
            btn_stock.clicked.connect(self._sumar_stock)
            btn_del = QPushButton("Eliminar")
            btn_del.setObjectName("DangerButton")
            btn_del.clicked.connect(self._eliminar)
            actions.extend([btn_new, btn_edit, btn_stock, btn_del])
        header, self._status = build_page_header(
            "Inventario",
            "Alta y stock de piezas/repuestos disponibles para las reparaciones",
            actions=actions or None,
        )
        layout.addLayout(header)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Stock", "Precio", "Descripción"])
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)
        self.empty = EmptyState(
            "No hay piezas de repuesto en el inventario.",
            "+ Nuevo repuesto" if can_edit else "",
            self._nuevo if can_edit else None,
        )
        layout.addWidget(self.empty)
        self.empty.hide()

    def refresh(self) -> None:
        self.tabla.setRowCount(0)
        comps = self._ctx.inventario.listar(es_demo=self._session.es_demo)
        for c in comps:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            vals = [c.nombre, str(c.stock), f"{c.precio:.2f} €", c.descripcion]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, c.id)
                if c.stock_bajo() and col == 1:
                    item.setForeground(Qt.GlobalColor.red)
                self.tabla.setItem(row, col, item)
        self.tabla.resizeColumnsToContents()
        self.tabla.setVisible(bool(comps))
        self.empty.setVisible(not comps)

    def _seleccionado(self):
        items = self.tabla.selectedItems()
        if not items:
            return None
        cid = items[0].data(Qt.ItemDataRole.UserRole)
        for c in self._ctx.inventario.listar(es_demo=self._session.es_demo):
            if c.id == cid:
                return c
        return None

    def _nuevo(self) -> None:
        if not self._session.puede_gestionar_inventario():
            show_toast(self._status, "No tienes permiso para gestionar el inventario.", error=True)
            return
        dlg = ComponenteDialog(parent=self)
        dlg.stock.setValue(1)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        nombre = dlg.nombre.text().strip()
        if not nombre:
            show_toast(self._status, "Indica el nombre de la pieza.", error=True)
            return
        try:
            creado = self._ctx.inventario.crear(
                nombre=nombre,
                stock=dlg.stock.value(),
                precio=dlg.precio.value(),
                descripcion=dlg.descripcion.toPlainText().strip(),
                es_demo=self._session.es_demo,
            )
            self.refresh()
            show_toast(
                self._status,
                f"Repuesto «{creado.nombre}» añadido (stock {creado.stock}).",
            )
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _editar(self) -> None:
        if not self._session.puede_gestionar_inventario():
            return
        c = self._seleccionado()
        if not c:
            show_toast(self._status, "Selecciona una pieza de la lista.", error=True)
            return
        dlg = ComponenteDialog(componente=c, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        nombre = dlg.nombre.text().strip()
        if not nombre:
            show_toast(self._status, "Indica el nombre de la pieza.", error=True)
            return
        c.nombre = nombre
        c.stock = dlg.stock.value()
        c.precio = dlg.precio.value()
        c.descripcion = dlg.descripcion.toPlainText().strip()
        try:
            self._ctx.inventario.actualizar(c)
            self.refresh()
            show_toast(self._status, f"Repuesto «{c.nombre}» actualizado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _sumar_stock(self) -> None:
        """Incrementa el stock de la pieza seleccionada (entrada rápida)."""
        if not self._session.puede_gestionar_inventario():
            return
        c = self._seleccionado()
        if not c:
            show_toast(self._status, "Selecciona una pieza de la lista.", error=True)
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Añadir stock — {c.nombre}")
        form = QFormLayout(dlg)
        cantidad = QSpinBox()
        cantidad.setRange(1, 100000)
        cantidad.setValue(1)
        form.addRow("Cantidad a añadir", cantidad)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        c.stock = c.stock + cantidad.value()
        try:
            self._ctx.inventario.actualizar(c)
            self.refresh()
            show_toast(
                self._status,
                f"+{cantidad.value()} de «{c.nombre}». Stock actual: {c.stock}.",
            )
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _eliminar(self) -> None:
        if not self._session.puede_gestionar_inventario():
            return
        c = self._seleccionado()
        if not c:
            show_toast(self._status, "Selecciona una pieza de la lista.", error=True)
            return
        if QMessageBox.question(
            self, "Eliminar", f"¿Eliminar {c.nombre}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._ctx.inventario.eliminar(c.id)  # type: ignore[arg-type]
            self.refresh()
            show_toast(self._status, f"Repuesto «{c.nombre}» eliminado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
