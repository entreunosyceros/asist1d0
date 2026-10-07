"""
Vista de equipos informáticos.

Árbol usuario → equipo → (componentes / software / reparaciones / incidencias)
y panel de ficha con especificaciones. Demuestra relaciones SQLite entre
entidades de inventario.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.enums import Rol
from app.ui.page_chrome import (
    EmptyState,
    apply_page_margins,
    build_page_header,
    show_toast,
)


def _meta_row(grid: QGridLayout, row: int, label: str, value: str) -> None:
    lab = QLabel(label)
    lab.setObjectName("MetaLabel")
    val = QLabel(value)
    val.setObjectName("MetaValue")
    val.setWordWrap(True)
    grid.addWidget(lab, row, 0)
    grid.addWidget(val, row, 1)


class EquipoDialog(QDialog):
    """Formulario modal para registrar o editar un equipo."""

    def __init__(
        self, ctx: AppContext, session: SessionContext, equipo=None, parent=None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Equipo")
        self.setMinimumWidth(440)
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
        self.cpu = QLineEdit()
        self.ram = QSpinBox()
        self.ram.setRange(0, 1024)
        self.ram.setSuffix(" GB")
        self.almacenamiento = QLineEdit()
        self.almacenamiento.setPlaceholderText("SSD 512 GB")
        self.gpu = QLineEdit()

        if equipo:
            idx = self.usuario.findData(equipo.usuario_id)
            if idx >= 0:
                self.usuario.setCurrentIndex(idx)
            self.serie.setText(equipo.numero_serie)
            self.marca.setText(equipo.marca)
            self.modelo.setText(equipo.modelo)
            self.so.setText(equipo.sistema_operativo)
            self.cpu.setText(equipo.cpu)
            self.ram.setValue(equipo.ram_gb)
            self.almacenamiento.setText(equipo.almacenamiento)
            self.gpu.setText(equipo.gpu)

        layout.addRow("Usuario", self.usuario)
        layout.addRow("Nº serie", self.serie)
        layout.addRow("Marca", self.marca)
        layout.addRow("Modelo", self.modelo)
        layout.addRow("Sistema operativo", self.so)
        layout.addRow("CPU", self.cpu)
        layout.addRow("RAM", self.ram)
        layout.addRow("Almacenamiento", self.almacenamiento)
        layout.addRow("GPU", self.gpu)

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
            "cpu": self.cpu.text().strip(),
            "ram_gb": self.ram.value(),
            "almacenamiento": self.almacenamiento.text().strip(),
            "gpu": self.gpu.text().strip(),
        }


class SoftwareDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Añadir software")
        layout = QFormLayout(self)
        self.nombre = QLineEdit()
        self.version = QLineEdit()
        self.licencia = QLineEdit()
        layout.addRow("Nombre", self.nombre)
        layout.addRow("Versión", self.version)
        layout.addRow("Licencia", self.licencia)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class ComponenteEquipoDialog(QDialog):
    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asociar componente del inventario")
        layout = QFormLayout(self)
        self.componente = QComboBox()
        for c in ctx.inventario.listar(es_demo=session.es_demo):
            self.componente.addItem(f"{c.nombre} (stock {c.stock})", c.id)
        self.cantidad = QSpinBox()
        self.cantidad.setRange(1, 99)
        self.notas = QLineEdit()
        self.notas.setPlaceholderText("Ampliación, sustitución…")
        layout.addRow("Componente", self.componente)
        layout.addRow("Cantidad", self.cantidad)
        layout.addRow("Notas", self.notas)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class ReparacionDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registrar reparación")
        layout = QFormLayout(self)
        self.descripcion = QLineEdit()
        self.coste = QSpinBox()
        self.coste.setRange(0, 100000)
        self.coste.setSuffix(" €")
        layout.addRow("Descripción", self.descripcion)
        layout.addRow("Coste", self.coste)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class EquiposView(QWidget):
    """Página de equipos con árbol de relaciones y ficha de detalle."""

    abrir_incidencia = Signal(int)

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._status = None
        self._current_eq_id: int | None = None
        self._build()
        self.refresh()

    def _puede_editar(self) -> bool:
        return self._session.es_tecnico() or self._session.rol == Rol.USUARIO

    def _es_tech(self) -> bool:
        return self._session.es_tecnico()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        actions = []
        if self._puede_editar():
            btn = QPushButton("+ Nuevo equipo")
            btn.clicked.connect(self._nuevo)
            actions.append(btn)
            btn_edit = QPushButton("Editar")
            btn_edit.setObjectName("SecondaryButton")
            btn_edit.clicked.connect(self._editar)
            actions.append(btn_edit)
            if self._es_tech():
                btn_del = QPushButton("Eliminar")
                btn_del.setObjectName("DangerButton")
                btn_del.clicked.connect(self._eliminar)
                actions.append(btn_del)
        header, self._status = build_page_header(
            "Equipos",
            "Inventario físico: specs, componentes, software, reparaciones e incidencias",
            actions=actions or None,
        )
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Elemento", "Detalle"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_lay.addWidget(self.tree)
        self.empty = EmptyState(
            "No hay equipos registrados. Añade el tuyo para poder abrir incidencias.",
            "+ Nuevo equipo",
            self._nuevo if self._puede_editar() else None,
        )
        left_lay.addWidget(self.empty)
        self.empty.hide()
        splitter.addWidget(left)

        detail = QWidget()
        detail.setObjectName("DetailPanel")
        dlay = QVBoxLayout(detail)
        dlay.setContentsMargins(16, 8, 8, 8)
        self.detalle_titulo = QLabel("Selecciona un equipo")
        self.detalle_titulo.setObjectName("DetailHeading")
        dlay.addWidget(self.detalle_titulo)

        self.specs_box = QGroupBox("Especificaciones")
        self.specs_grid = QGridLayout(self.specs_box)
        self.specs_grid.setColumnStretch(1, 1)
        dlay.addWidget(self.specs_box)

        if self._es_tech():
            row = QHBoxLayout()
            self.btn_comp = QPushButton("+ Componente")
            self.btn_comp.setObjectName("SecondaryButton")
            self.btn_comp.clicked.connect(self._add_componente)
            self.btn_sw = QPushButton("+ Software")
            self.btn_sw.setObjectName("SecondaryButton")
            self.btn_sw.clicked.connect(self._add_software)
            self.btn_rep = QPushButton("+ Reparación")
            self.btn_rep.setObjectName("SecondaryButton")
            self.btn_rep.clicked.connect(self._add_reparacion)
            row.addWidget(self.btn_comp)
            row.addWidget(self.btn_sw)
            row.addWidget(self.btn_rep)
            dlay.addLayout(row)

        self.detalle_hint = QLabel(
            "Expande el árbol: Componentes · Software · Reparaciones · Incidencias · Usuario"
        )
        self.detalle_hint.setObjectName("PageSubtitle")
        self.detalle_hint.setWordWrap(True)
        dlay.addWidget(self.detalle_hint)
        dlay.addStretch()
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        self._set_detail_enabled(False)

    def _set_detail_enabled(self, enabled: bool) -> None:
        if self._es_tech():
            self.btn_comp.setEnabled(enabled)
            self.btn_sw.setEnabled(enabled)
            self.btn_rep.setEnabled(enabled)

    def refresh(self) -> None:
        keep = self._current_eq_id
        self.tree.clear()
        uid = self._session.usuario_id if self._session.rol == Rol.USUARIO else None
        equipos = self._ctx.equipos.listar(
            usuario_id=uid, es_demo=self._session.es_demo
        )

        por_usuario: dict[str, list] = {}
        for eq in equipos:
            key = eq.usuario_nombre or f"Usuario #{eq.usuario_id}"
            por_usuario.setdefault(key, []).append(eq)

        select_item = None
        for nombre_usuario, eqs in por_usuario.items():
            user_item = QTreeWidgetItem(
                [f"👤 {nombre_usuario}", f"{len(eqs)} equipo(s)"]
            )
            self.tree.addTopLevelItem(user_item)
            for eq in eqs:
                full = self._ctx.equipos.obtener(eq.id, con_detalle=True) or eq
                eq_item = QTreeWidgetItem(
                    [
                        f"💻 {full.codigo} · {full.nombre_completo}",
                        f"S/N {full.numero_serie}",
                    ]
                )
                eq_item.setData(0, Qt.ItemDataRole.UserRole, ("equipo", full.id))
                user_item.addChild(eq_item)

                # Usuario asignado
                u_node = QTreeWidgetItem(
                    ["👤 Usuario asignado", full.usuario_nombre or "—"]
                )
                eq_item.addChild(u_node)

                # Componentes
                comp_node = QTreeWidgetItem(
                    ["🧩 Componentes", f"{len(full.componentes)}"]
                )
                eq_item.addChild(comp_node)
                for c in full.componentes:
                    child = QTreeWidgetItem(
                        [f"· {c.componente_nombre}", f"× {c.cantidad}"]
                    )
                    child.setData(
                        0, Qt.ItemDataRole.UserRole, ("equipo_comp", c.id, full.id)
                    )
                    comp_node.addChild(child)

                # Software
                sw_node = QTreeWidgetItem(
                    ["📦 Software instalado", f"{len(full.software)}"]
                )
                eq_item.addChild(sw_node)
                for s in full.software:
                    child = QTreeWidgetItem([f"· {s.nombre}", s.version or ""])
                    child.setData(
                        0, Qt.ItemDataRole.UserRole, ("equipo_sw", s.id, full.id)
                    )
                    sw_node.addChild(child)

                # Reparaciones
                rep_node = QTreeWidgetItem(
                    ["🔧 Historial de reparaciones", f"{len(full.reparaciones)}"]
                )
                eq_item.addChild(rep_node)
                for r in full.reparaciones:
                    quien = r.tecnico_nombre or "—"
                    child = QTreeWidgetItem(
                        [
                            f"· {(r.fecha or '')[:10]} {r.descripcion[:40]}",
                            quien,
                        ]
                    )
                    if r.incidencia_id:
                        child.setData(
                            0,
                            Qt.ItemDataRole.UserRole,
                            ("incidencia", r.incidencia_id),
                        )
                    rep_node.addChild(child)

                # Incidencias
                incs = self._ctx.incidencias.listar(
                    equipo_id=full.id, es_demo=self._session.es_demo
                )
                inc_node = QTreeWidgetItem(["🎫 Incidencias", f"{len(incs)}"])
                eq_item.addChild(inc_node)
                for inc in incs:
                    estado = (
                        inc.estado.etiqueta_usuario
                        if self._session.rol == Rol.USUARIO
                        else inc.estado.value
                    )
                    child = QTreeWidgetItem(
                        [
                            f"· {inc.codigo} {inc.prioridad.icono} {inc.titulo}",
                            estado,
                        ]
                    )
                    child.setData(
                        0, Qt.ItemDataRole.UserRole, ("incidencia", inc.id)
                    )
                    inc_node.addChild(child)

                if keep and full.id == keep:
                    select_item = eq_item
            user_item.setExpanded(True)

        self.tree.resizeColumnToContents(0)
        self.tree.setVisible(bool(equipos))
        self.empty.setVisible(not equipos)
        if select_item is not None:
            self.tree.setCurrentItem(select_item)
            select_item.setExpanded(True)
        elif not equipos:
            self._limpiar_detalle()

    def seleccionar_equipo(self, equipo_id: int) -> None:
        """API pública: selecciona un equipo en el árbol (p. ej. desde búsqueda)."""
        self._current_eq_id = equipo_id
        self.refresh()
        item = self.tree.currentItem()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if not (isinstance(data, tuple) and len(data) >= 2 and data[0] == "equipo" and data[1] == equipo_id):
            self._mostrar_equipo(equipo_id)

    def _limpiar_detalle(self) -> None:
        self._current_eq_id = None
        self.detalle_titulo.setText("Selecciona un equipo")
        while self.specs_grid.count():
            item = self.specs_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._set_detail_enabled(False)

    def _mostrar_equipo(self, eq_id: int) -> None:
        eq = self._ctx.equipos.obtener(eq_id, con_detalle=True)
        if not eq:
            self._limpiar_detalle()
            return
        self._current_eq_id = eq_id
        self._set_detail_enabled(True)
        self.detalle_titulo.setText(f"{eq.codigo} — {eq.nombre_completo}")
        while self.specs_grid.count():
            item = self.specs_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        _meta_row(self.specs_grid, 0, "Usuario", eq.usuario_nombre or "—")
        _meta_row(self.specs_grid, 1, "Nº serie", eq.numero_serie)
        _meta_row(self.specs_grid, 2, "CPU", eq.cpu or "—")
        _meta_row(
            self.specs_grid,
            3,
            "RAM",
            f"{eq.ram_gb} GB" if eq.ram_gb else "—",
        )
        _meta_row(self.specs_grid, 4, "Almacenamiento", eq.almacenamiento or "—")
        _meta_row(self.specs_grid, 5, "GPU", eq.gpu or "—")
        _meta_row(self.specs_grid, 6, "SO", eq.sistema_operativo or "—")
        _meta_row(
            self.specs_grid,
            7,
            "Resumen",
            f"{len(eq.componentes)} comp. · {len(eq.software)} apps · "
            f"{len(eq.reparaciones)} reparaciones",
        )

    def _on_select(self) -> None:
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        eq_id = None
        if isinstance(data, tuple) and data:
            if data[0] == "equipo":
                eq_id = data[1]
            elif data[0] in ("equipo_comp", "equipo_sw") and len(data) >= 3:
                eq_id = data[2]
        if eq_id is None:
            # Subir hasta encontrar equipo
            cur = item
            while cur:
                d = cur.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(d, tuple) and d and d[0] == "equipo":
                    eq_id = d[1]
                    break
                cur = cur.parent()
        if eq_id:
            self._mostrar_equipo(int(eq_id))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, tuple):
            return
        if data[0] == "incidencia" and data[1]:
            self.abrir_incidencia.emit(int(data[1]))

    def _equipo_seleccionado(self):
        if self._current_eq_id:
            return self._ctx.equipos.obtener(self._current_eq_id)
        item = self.tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        eq_id = None
        if isinstance(data, tuple) and data and data[0] == "equipo":
            eq_id = data[1]
        if not eq_id:
            parent = item.parent()
            while parent:
                pdata = parent.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(pdata, tuple) and pdata and pdata[0] == "equipo":
                    eq_id = pdata[1]
                    break
                parent = parent.parent()
        if not eq_id:
            return None
        return self._ctx.equipos.obtener(eq_id)

    def _nuevo(self) -> None:
        dlg = EquipoDialog(self._ctx, self._session, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        try:
            creado = self._ctx.equipos.crear(
                **data, actor_id=self._session.usuario_id
            )
            self._current_eq_id = creado.id
            self.refresh()
            show_toast(self._status, f"Equipo {creado.codigo} creado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _editar(self) -> None:
        eq = self._equipo_seleccionado()
        if not eq:
            show_toast(self._status, "Selecciona un equipo.", error=True)
            return
        if self._session.rol == Rol.USUARIO and eq.usuario_id != self._session.usuario_id:
            show_toast(
                self._status, "Solo puedes editar tus propios equipos.", error=True
            )
            return
        dlg = EquipoDialog(self._ctx, self._session, equipo=eq, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        if self._session.rol == Rol.USUARIO:
            data["usuario_id"] = self._session.usuario_id
        eq.usuario_id = data["usuario_id"]
        eq.numero_serie = data["numero_serie"]
        eq.marca = data["marca"]
        eq.modelo = data["modelo"]
        eq.sistema_operativo = data["sistema_operativo"]
        eq.cpu = data["cpu"]
        eq.ram_gb = data["ram_gb"]
        eq.almacenamiento = data["almacenamiento"]
        eq.gpu = data["gpu"]
        try:
            self._ctx.equipos.actualizar(
                eq,
                actor_id=self._session.usuario_id,
                rol=self._session.rol,
            )
            self.refresh()
            show_toast(self._status, "Equipo actualizado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _eliminar(self) -> None:
        if not self._es_tech():
            return
        eq = self._equipo_seleccionado()
        if not eq:
            return
        if (
            QMessageBox.question(self, "Eliminar", f"¿Eliminar {eq}?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._ctx.equipos.eliminar(eq.id, actor_id=self._session.usuario_id)  # type: ignore[arg-type]
        self._current_eq_id = None
        self.refresh()
        show_toast(self._status, "Equipo eliminado.")

    def _add_componente(self) -> None:
        if not self._current_eq_id or not self._es_tech():
            return
        dlg = ComponenteEquipoDialog(self._ctx, self._session, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cid = dlg.componente.currentData()
        if not cid:
            return
        try:
            self._ctx.equipos.anadir_componente(
                self._current_eq_id,
                cid,
                dlg.cantidad.value(),
                dlg.notas.text().strip(),
                actor_id=self._session.usuario_id,
            )
            self.refresh()
            show_toast(self._status, "Componente asociado al equipo.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _add_software(self) -> None:
        if not self._current_eq_id or not self._es_tech():
            return
        dlg = SoftwareDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.nombre.text().strip():
            show_toast(self._status, "Indica el nombre del software.", error=True)
            return
        try:
            self._ctx.equipos.anadir_software(
                self._current_eq_id,
                dlg.nombre.text().strip(),
                dlg.version.text().strip(),
                dlg.licencia.text().strip(),
                actor_id=self._session.usuario_id,
            )
            self.refresh()
            show_toast(self._status, "Software registrado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _add_reparacion(self) -> None:
        if not self._current_eq_id or not self._es_tech():
            return
        dlg = ReparacionDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if not dlg.descripcion.text().strip():
            show_toast(self._status, "Indica la descripción.", error=True)
            return
        try:
            self._ctx.equipos.registrar_reparacion(
                self._current_eq_id,
                dlg.descripcion.text().strip(),
                tecnico_id=self._session.usuario_id,
                coste=float(dlg.coste.value()),
                actor_id=self._session.usuario_id,
            )
            self.refresh()
            show_toast(self._status, "Reparación registrada.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
