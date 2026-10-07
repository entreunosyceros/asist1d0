"""
Vista de incidencias (listado + ficha de detalle).

Incluye búsqueda/filtros, cambio de estado/prioridad, asignación,
intervenciones, uso de repuestos e historial. El rol Usuario solo
crea/consulta las suyas.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.enums import CategoriaIncidencia, EstadoIncidencia, Prioridad, Rol
from app.ui.page_chrome import (
    EmptyState,
    apply_page_margins,
    build_page_header,
    show_toast,
)


class NuevaIncidenciaDialog(QDialog):
    """Alta de una incidencia asociada a un equipo del usuario."""

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self.setWindowTitle("Nueva incidencia")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.equipo = QComboBox()
        if session.rol == Rol.USUARIO:
            equipos = ctx.equipos.listar(
                usuario_id=session.usuario_id, es_demo=session.es_demo
            )
        else:
            equipos = ctx.equipos.listar(es_demo=session.es_demo)
        for eq in equipos:
            self.equipo.addItem(f"{eq.nombre_completo} ({eq.numero_serie})", eq.id)

        self.categoria = QComboBox()
        for c in CategoriaIncidencia:
            self.categoria.addItem(c.value, c.value)
        self.categoria.currentIndexChanged.connect(self._aplicar_plantilla)

        self.titulo = QLineEdit()
        self.descripcion = QTextEdit()
        self.descripcion.setMaximumHeight(100)
        self.prioridad = QComboBox()
        for p in Prioridad:
            self.prioridad.addItem(f"{p.icono} {p.value}", p.value)

        layout.addRow("Equipo", self.equipo)
        layout.addRow("Categoría", self.categoria)
        layout.addRow("Título", self.titulo)
        layout.addRow("Descripción", self.descripcion)
        layout.addRow("Prioridad", self.prioridad)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self._aplicar_plantilla()

    def _aplicar_plantilla(self) -> None:
        cat = CategoriaIncidencia(self.categoria.currentData())
        titulo, desc = cat.plantilla
        # Solo rellena si el usuario no ha escrito aún o coincide con otra plantilla.
        actuales = {t for t, _ in (c.plantilla for c in CategoriaIncidencia)}
        if not self.titulo.text().strip() or self.titulo.text().strip() in actuales:
            self.titulo.setText(titulo)
        descs = {d for _, d in (c.plantilla for c in CategoriaIncidencia)}
        if (
            not self.descripcion.toPlainText().strip()
            or self.descripcion.toPlainText().strip() in descs
        ):
            self.descripcion.setPlainText(desc)

    def datos(self):
        return {
            "equipo_id": self.equipo.currentData(),
            "titulo": self.titulo.text().strip(),
            "descripcion": self.descripcion.toPlainText().strip(),
            "prioridad": Prioridad(self.prioridad.currentData()),
            "categoria": CategoriaIncidencia(self.categoria.currentData()),
        }


class IntervencionDialog(QDialog):
    """Registro de una intervención técnica sobre la incidencia abierta."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nueva intervención")
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.descripcion = QTextEdit()
        layout.addRow("Descripción", self.descripcion)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class UsarRepuestoDialog(QDialog):
    """Selección de componente de inventario a consumir en la reparación."""

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self.setWindowTitle("Usar repuesto")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.componente = QComboBox()
        self._rellenar_componentes()
        self.cantidad = QSpinBox()
        self.cantidad.setRange(1, 999)
        self.cantidad.setValue(1)
        layout.addRow("Componente", self.componente)
        layout.addRow("Cantidad", self.cantidad)
        if session.puede_gestionar_inventario():
            btn_nuevo = QPushButton("+ Añadir pieza al inventario…")
            btn_nuevo.setObjectName("SecondaryButton")
            btn_nuevo.clicked.connect(self._nuevo_repuesto)
            layout.addRow(btn_nuevo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _rellenar_componentes(self, seleccionar_id: int | None = None) -> None:
        self.componente.clear()
        for c in self._ctx.inventario.listar(es_demo=self._session.es_demo):
            if c.stock > 0:
                self.componente.addItem(f"{c.nombre} (stock {c.stock})", c.id)
        if seleccionar_id is not None:
            idx = self.componente.findData(seleccionar_id)
            if idx >= 0:
                self.componente.setCurrentIndex(idx)

    def _nuevo_repuesto(self) -> None:
        from app.ui.inventario import ComponenteDialog

        dlg = ComponenteDialog(parent=self)
        dlg.stock.setValue(1)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        nombre = dlg.nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Repuesto", "Indica el nombre de la pieza.")
            return
        try:
            creado = self._ctx.inventario.crear(
                nombre=nombre,
                stock=dlg.stock.value(),
                precio=dlg.precio.value(),
                descripcion=dlg.descripcion.toPlainText().strip(),
                es_demo=self._session.es_demo,
            )
            self._rellenar_componentes(creado.id)
            if self.componente.count() == 0:
                QMessageBox.information(
                    self,
                    "Repuesto",
                    f"«{creado.nombre}» se creó, pero el stock es 0. "
                    "Añade stock en Inventario para poder usarlo.",
                )
        except Exception as exc:
            QMessageBox.warning(self, "Repuesto", str(exc))

    def datos(self):
        return {
            "componente_id": self.componente.currentData(),
            "cantidad": self.cantidad.value(),
        }


def _meta_row(grid: QGridLayout, row: int, label: str, value: str) -> None:
    lbl = QLabel(label)
    lbl.setObjectName("MetaLabel")
    val = QLabel(value)
    val.setObjectName("MetaValue")
    val.setWordWrap(True)
    grid.addWidget(lbl, row, 0)
    grid.addWidget(val, row, 1)


class IncidenciasView(QWidget):
    """Página principal de incidencias: tabla + panel de detalle."""

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._current_id: int | None = None
        self._status: QLabel | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)

        btn_nueva = QPushButton("+ Nueva incidencia")
        btn_nueva.clicked.connect(self._nueva)
        header, self._status = build_page_header(
            "Incidencias",
            "Busca, filtra y gestiona el ciclo de vida de los tickets",
            actions=[btn_nueva],
        )
        layout.addLayout(header)

        filters = QHBoxLayout()
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar por código, título, equipo…")
        self.busqueda.textChanged.connect(self.refresh)

        self.filtro_estado = QComboBox()
        self.filtro_estado.addItem("Estado: todas", "")
        for e in EstadoIncidencia:
            self.filtro_estado.addItem(e.value, e.value)
        self.filtro_estado.currentIndexChanged.connect(self.refresh)

        self.filtro_prioridad = QComboBox()
        self.filtro_prioridad.addItem("Prioridad: todas", "")
        for p in Prioridad:
            self.filtro_prioridad.addItem(f"{p.icono} {p.value}", p.value)
        self.filtro_prioridad.currentIndexChanged.connect(self.refresh)

        self.filtro_categoria = QComboBox()
        self.filtro_categoria.addItem("Categoría: todas", "")
        for c in CategoriaIncidencia:
            self.filtro_categoria.addItem(c.value, c.value)
        self.filtro_categoria.currentIndexChanged.connect(self.refresh)

        self.chk_mias = QCheckBox("Mis asignadas")
        self.chk_mias.toggled.connect(self._on_mias_toggled)
        self.chk_sin_asignar = QCheckBox("Sin asignar")
        self.chk_sin_asignar.toggled.connect(self._on_sin_asignar_toggled)
        self.filtro_tecnico = QComboBox()
        self.filtro_tecnico.addItem("Técnico: todos", -1)
        for t in self._ctx.usuarios.tecnicos(es_demo=self._session.es_demo):
            self.filtro_tecnico.addItem(t.nombre, t.id)
        self.filtro_tecnico.currentIndexChanged.connect(self.refresh)
        es_tech = self._session.es_tecnico()
        if not es_tech:
            self.chk_mias.setVisible(False)
            self.chk_sin_asignar.setVisible(False)
            self.filtro_tecnico.setVisible(False)

        filters.addWidget(self.busqueda, 2)
        filters.addWidget(self.filtro_estado)
        filters.addWidget(self.filtro_prioridad)
        filters.addWidget(self.filtro_categoria)
        filters.addWidget(self.chk_mias)
        filters.addWidget(self.chk_sin_asignar)
        filters.addWidget(self.filtro_tecnico)
        layout.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Código", "Título", "Categoría", "Prioridad", "Estado", "Equipo"]
        )
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.itemSelectionChanged.connect(self._on_select)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.lista_stack = QStackedWidget()
        self.lista_stack.addWidget(self.tabla)
        self.empty = EmptyState(
            "No hay incidencias. Si aún no tienes equipo, regístralo primero en Equipos.",
            "+ Nueva incidencia",
            self._nueva,
        )
        self.lista_stack.addWidget(self.empty)
        left_lay.addWidget(self.lista_stack)
        splitter.addWidget(left)

        # Detalle con scroll
        detail_wrap = QFrame()
        detail_wrap.setObjectName("DetailPanel")
        detail_outer = QVBoxLayout(detail_wrap)
        detail_outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail = QWidget()
        dlay = QVBoxLayout(detail)
        dlay.setContentsMargins(16, 16, 16, 16)
        dlay.setSpacing(10)

        self.detalle_titulo = QLabel("Selecciona una incidencia")
        self.detalle_titulo.setObjectName("DetailHeading")
        dlay.addWidget(self.detalle_titulo)

        self.meta_box = QGroupBox("Datos")
        self.meta_grid = QGridLayout(self.meta_box)
        self.meta_grid.setColumnStretch(1, 1)
        dlay.addWidget(self.meta_box)

        dlay.addWidget(QLabel("Descripción"))
        self.detalle_desc = QLabel("(sin selección)")
        self.detalle_desc.setWordWrap(True)
        self.detalle_desc.setObjectName("MetaValue")
        dlay.addWidget(self.detalle_desc)
        self.btn_editar_desc = QPushButton("Editar descripción…")
        self.btn_editar_desc.setObjectName("SecondaryButton")
        self.btn_editar_desc.clicked.connect(self._editar_descripcion)
        dlay.addWidget(self.btn_editar_desc)

        self.user_actions = QWidget()
        ua = QHBoxLayout(self.user_actions)
        ua.setContentsMargins(0, 0, 0, 0)
        self.btn_confirmar = QPushButton("Confirmar resolución")
        self.btn_confirmar.clicked.connect(self._confirmar_resolucion)
        self.btn_reabrir = QPushButton("Reabrir incidencia")
        self.btn_reabrir.setObjectName("SecondaryButton")
        self.btn_reabrir.clicked.connect(self._reabrir)
        ua.addWidget(self.btn_confirmar)
        ua.addWidget(self.btn_reabrir)
        dlay.addWidget(self.user_actions)
        if self._session.rol != Rol.USUARIO:
            self.user_actions.hide()

        dlay.addWidget(QLabel("Adjuntos"))
        self.lista_adjuntos = QListWidget()
        self.lista_adjuntos.setObjectName("DetailList")
        self.lista_adjuntos.setMinimumHeight(70)
        self.lista_adjuntos.itemDoubleClicked.connect(self._abrir_adjunto)
        dlay.addWidget(self.lista_adjuntos)
        adj_row = QHBoxLayout()
        self.btn_adjuntar = QPushButton("+ Adjuntar archivo…")
        self.btn_adjuntar.setObjectName("SecondaryButton")
        self.btn_adjuntar.clicked.connect(self._adjuntar)
        self.btn_abrir_adjunto = QPushButton("Abrir")
        self.btn_abrir_adjunto.setObjectName("SecondaryButton")
        self.btn_abrir_adjunto.clicked.connect(self._abrir_adjunto)
        self.btn_eliminar_adjunto = QPushButton("Quitar")
        self.btn_eliminar_adjunto.setObjectName("DangerButton")
        self.btn_eliminar_adjunto.clicked.connect(self._eliminar_adjunto)
        adj_row.addWidget(self.btn_adjuntar)
        adj_row.addWidget(self.btn_abrir_adjunto)
        adj_row.addWidget(self.btn_eliminar_adjunto)
        dlay.addLayout(adj_row)

        dlay.addWidget(QLabel("Comentarios"))
        self.lista_comentarios = QListWidget()
        self.lista_comentarios.setObjectName("DetailList")
        self.lista_comentarios.setMinimumHeight(100)
        dlay.addWidget(self.lista_comentarios)
        self.comentario_input = QTextEdit()
        self.comentario_input.setMaximumHeight(72)
        self.comentario_input.setPlaceholderText(
            "Escribe un comentario para el equipo de soporte…"
        )
        dlay.addWidget(self.comentario_input)
        self.btn_comentario = QPushButton("Enviar comentario")
        self.btn_comentario.setObjectName("SecondaryButton")
        self.btn_comentario.clicked.connect(self._enviar_comentario)
        dlay.addWidget(self.btn_comentario)

        dlay.addWidget(QLabel("Intervenciones"))
        self.lista_intervenciones = QListWidget()
        self.lista_intervenciones.setObjectName("DetailList")
        self.lista_intervenciones.setMinimumHeight(90)
        dlay.addWidget(self.lista_intervenciones)

        dlay.addWidget(QLabel("Historial"))
        self.lista_historial = QListWidget()
        self.lista_historial.setObjectName("DetailList")
        self.lista_historial.setMinimumHeight(90)
        dlay.addWidget(self.lista_historial)

        dlay.addWidget(QLabel("Repuestos usados"))
        self.lista_repuestos = QListWidget()
        self.lista_repuestos.setObjectName("DetailList")
        self.lista_repuestos.setMinimumHeight(70)
        dlay.addWidget(self.lista_repuestos)

        # Panel solo para técnico/admin (oculto al Usuario final).
        self.tech_panel = QWidget()
        tech_lay = QVBoxLayout(self.tech_panel)
        tech_lay.setContentsMargins(0, 8, 0, 0)
        tech_lay.setSpacing(8)
        actions = QGridLayout()
        self.cmb_estado = QComboBox()
        for e in EstadoIncidencia:
            self.cmb_estado.addItem(e.value, e.value)
        self.cmb_prioridad = QComboBox()
        for p in Prioridad:
            self.cmb_prioridad.addItem(f"{p.icono} {p.value}", p.value)
        self.cmb_tecnico = QComboBox()
        self.cmb_tecnico.addItem("Sin asignar", -1)
        for t in self._ctx.usuarios.tecnicos(es_demo=self._session.es_demo):
            self.cmb_tecnico.addItem(t.nombre, t.id)

        actions.addWidget(QLabel("Estado"), 0, 0)
        actions.addWidget(self.cmb_estado, 0, 1)
        actions.addWidget(QLabel("Prioridad"), 1, 0)
        actions.addWidget(self.cmb_prioridad, 1, 1)
        actions.addWidget(QLabel("Técnico"), 2, 0)
        actions.addWidget(self.cmb_tecnico, 2, 1)
        tech_lay.addLayout(actions)

        row_btns = QHBoxLayout()
        self.btn_guardar = QPushButton("Guardar cambios")
        self.btn_guardar.clicked.connect(self._guardar_cambios)
        self.btn_interv = QPushButton("Añadir intervención")
        self.btn_interv.setObjectName("SecondaryButton")
        self.btn_interv.clicked.connect(self._add_intervencion)
        self.btn_repuesto = QPushButton("Usar repuesto")
        self.btn_repuesto.setObjectName("SecondaryButton")
        self.btn_repuesto.clicked.connect(self._usar_repuesto)
        row_btns.addWidget(self.btn_guardar)
        row_btns.addWidget(self.btn_interv)
        row_btns.addWidget(self.btn_repuesto)
        tech_lay.addLayout(row_btns)
        dlay.addWidget(self.tech_panel)
        if self._session.rol == Rol.USUARIO:
            self.tech_panel.hide()
        dlay.addStretch()

        scroll.setWidget(detail)
        detail_outer.addWidget(scroll)
        splitter.addWidget(detail_wrap)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self._set_actions_enabled(False)

    def _set_actions_enabled(
        self,
        enabled: bool,
        *,
        puede_editar_desc: bool = False,
        puede_confirmar: bool = False,
        puede_reabrir: bool = False,
    ) -> None:
        tech = self._session.es_tecnico() and enabled
        self.btn_guardar.setEnabled(tech)
        self.btn_interv.setEnabled(tech)
        self.btn_repuesto.setEnabled(tech)
        self.cmb_estado.setEnabled(tech)
        self.cmb_prioridad.setEnabled(tech)
        self.cmb_tecnico.setEnabled(tech)
        self.btn_comentario.setEnabled(enabled)
        self.comentario_input.setEnabled(enabled)
        self.btn_adjuntar.setEnabled(enabled)
        self.btn_abrir_adjunto.setEnabled(enabled)
        self.btn_eliminar_adjunto.setEnabled(enabled)
        self.btn_editar_desc.setEnabled(puede_editar_desc)
        self.btn_confirmar.setEnabled(puede_confirmar)
        self.btn_confirmar.setVisible(puede_confirmar)
        self.btn_reabrir.setEnabled(puede_reabrir)
        self.btn_reabrir.setVisible(puede_reabrir)

    def _on_mias_toggled(self, checked: bool) -> None:
        if checked:
            self.chk_sin_asignar.setChecked(False)
            self.filtro_tecnico.setCurrentIndex(0)
        self.refresh()

    def _on_sin_asignar_toggled(self, checked: bool) -> None:
        if checked:
            self.chk_mias.setChecked(False)
            self.filtro_tecnico.setCurrentIndex(0)
        self.refresh()

    def refresh(self) -> None:
        keep_id = self._current_id
        kwargs: dict = {"es_demo": self._session.es_demo}
        if self._session.rol == Rol.USUARIO:
            kwargs["usuario_id"] = self._session.usuario_id
        estado_val = self.filtro_estado.currentData()
        if estado_val:
            kwargs["estado"] = EstadoIncidencia(estado_val)
        prio_val = self.filtro_prioridad.currentData()
        if prio_val:
            kwargs["prioridad"] = Prioridad(prio_val)
        cat_val = self.filtro_categoria.currentData()
        if cat_val:
            kwargs["categoria"] = CategoriaIncidencia(cat_val)
        texto = self.busqueda.text().strip()
        if texto:
            kwargs["texto"] = texto
        if self._session.es_tecnico():
            if self.chk_mias.isChecked():
                kwargs["tecnico_id"] = self._session.usuario_id
            elif self.chk_sin_asignar.isChecked():
                kwargs["sin_asignar"] = True
            else:
                tid = self.filtro_tecnico.currentData()
                if tid is not None and tid != -1:
                    kwargs["tecnico_id"] = tid

        incidencias = self._ctx.incidencias.listar(**kwargs)
        self.tabla.setRowCount(0)
        select_row = -1
        warn = QBrush(QColor("#fef2f2"))
        for inc in incidencias:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            estado_col = (
                f"{'⚠ Vencida · ' if inc.vencida else ''}"
                f"{inc.estado.etiqueta_usuario if self._session.rol == Rol.USUARIO else inc.estado.value}"
            )
            vals = [
                inc.codigo,
                f"{inc.prioridad.icono} {inc.titulo}",
                inc.categoria.value,
                inc.prioridad.value,
                estado_col,
                inc.equipo_nombre or "",
            ]
            for col, text in enumerate(vals):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, inc.id)
                if inc.vencida:
                    item.setBackground(warn)
                self.tabla.setItem(row, col, item)
            if keep_id and inc.id == keep_id:
                select_row = row

        self.tabla.resizeColumnsToContents()
        if incidencias:
            self.lista_stack.setCurrentWidget(self.tabla)
        else:
            self.lista_stack.setCurrentWidget(self.empty)
            self._limpiar_detalle()

        if select_row >= 0:
            self.tabla.selectRow(select_row)
        elif keep_id:
            self._limpiar_detalle()

    def seleccionar_incidencia(self, incidencia_id: int) -> None:
        """API pública para abrir un ticket desde el dashboard."""
        self.busqueda.clear()
        self.filtro_estado.setCurrentIndex(0)
        self.filtro_prioridad.setCurrentIndex(0)
        self.filtro_categoria.setCurrentIndex(0)
        self.chk_mias.setChecked(False)
        self.chk_sin_asignar.setChecked(False)
        self.filtro_tecnico.setCurrentIndex(0)
        self.refresh()
        for row in range(self.tabla.rowCount()):
            item = self.tabla.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == incidencia_id:
                self.tabla.selectRow(row)
                self._mostrar(incidencia_id)
                return
        # Si no está en la lista filtrada, mostrar igual
        self._mostrar(incidencia_id)

    def _on_select(self) -> None:
        items = self.tabla.selectedItems()
        if not items:
            return
        inc_id = items[0].data(Qt.ItemDataRole.UserRole)
        self._mostrar(inc_id)

    def _limpiar_detalle(self) -> None:
        self._current_id = None
        self.detalle_titulo.setText("Selecciona una incidencia")
        while self.meta_grid.count():
            item = self.meta_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.detalle_desc.setText("(sin selección)")
        self.lista_adjuntos.clear()
        self.lista_comentarios.clear()
        self.comentario_input.clear()
        self.lista_intervenciones.clear()
        self.lista_historial.clear()
        self.lista_repuestos.clear()
        self._set_actions_enabled(False)

    def _mostrar(self, inc_id: int) -> None:
        inc = self._ctx.incidencias.obtener(inc_id, es_demo=self._session.es_demo)
        if not inc:
            self._limpiar_detalle()
            return
        self._current_id = inc_id
        es_propia = inc.usuario_id == self._session.usuario_id
        puede_desc = self._session.es_tecnico() or (
            self._session.rol == Rol.USUARIO and es_propia and inc.esta_abierta()
        )
        puede_confirmar = (
            self._session.rol == Rol.USUARIO
            and es_propia
            and inc.estado
            in (EstadoIncidencia.PENDIENTE, EstadoIncidencia.EN_REPARACION)
        )
        puede_reabrir = (
            self._session.rol == Rol.USUARIO
            and es_propia
            and inc.estado == EstadoIncidencia.CERRADA
        )
        self._set_actions_enabled(
            True,
            puede_editar_desc=puede_desc,
            puede_confirmar=puede_confirmar,
            puede_reabrir=puede_reabrir,
        )
        titulo = f"{inc.codigo} — {inc.titulo}"
        if inc.vencida:
            titulo += "  ·  ⚠ Vencida"
        self.detalle_titulo.setText(titulo)

        while self.meta_grid.count():
            item = self.meta_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        fecha = (inc.fecha_creacion or "")[:16]
        estado_txt = (
            f"{inc.estado.etiqueta_usuario} ({inc.estado.value})"
            if self._session.rol == Rol.USUARIO
            else inc.estado.value
        )
        limite = inc.fecha_limite
        sla_txt = (
            f"{'⚠ Vencida · ' if inc.vencida else ''}"
            f"límite {(limite.strftime('%Y-%m-%d %H:%M') if limite else '—')}"
        )
        _meta_row(self.meta_grid, 0, "Usuario", inc.usuario_nombre or "—")
        _meta_row(self.meta_grid, 1, "Equipo", inc.equipo_nombre or "—")
        _meta_row(self.meta_grid, 2, "Categoría", inc.categoria.value)
        _meta_row(self.meta_grid, 3, "Prioridad", inc.prioridad.value)
        _meta_row(self.meta_grid, 4, "Estado", estado_txt)
        _meta_row(self.meta_grid, 5, "SLA", sla_txt)
        _meta_row(self.meta_grid, 6, "Fecha", fecha or "—")
        _meta_row(self.meta_grid, 7, "Técnico", inc.tecnico_nombre or "Sin asignar")

        self.detalle_desc.setText(inc.descripcion or "(sin descripción)")

        self.lista_adjuntos.clear()
        if inc.adjuntos:
            for a in inc.adjuntos:
                kb = max(1, a.tamano // 1024) if a.tamano else 0
                item = QListWidgetItem(
                    f"{a.nombre_original} ({kb} KB) · {(a.fecha or '')[:16]}"
                )
                item.setData(Qt.ItemDataRole.UserRole, a.id)
                self.lista_adjuntos.addItem(item)
        else:
            self.lista_adjuntos.addItem("(sin adjuntos)")

        self.lista_comentarios.clear()
        if inc.comentarios:
            for c in inc.comentarios:
                quien = c.usuario_nombre or "usuario"
                self.lista_comentarios.addItem(
                    f"{(c.fecha or '')[:16]} · {quien}: {c.texto}"
                )
        else:
            self.lista_comentarios.addItem("(sin comentarios)")

        self.lista_intervenciones.clear()
        if inc.intervenciones:
            for iv in inc.intervenciones:
                self.lista_intervenciones.addItem(
                    f"{(iv.fecha or '')[:16]} → {iv.descripcion}"
                )
        else:
            self.lista_intervenciones.addItem("(sin intervenciones)")

        self.lista_historial.clear()
        if inc.historial:
            for h in inc.historial:
                who = h.usuario_nombre or "sistema"
                self.lista_historial.addItem(
                    f"{(h.fecha or '')[:16]} · {who}: {h.accion}"
                )
        else:
            self.lista_historial.addItem("(sin historial)")

        self.lista_repuestos.clear()
        usados = self._ctx.inventario.componentes_de_incidencia(inc_id)
        if usados:
            for r in usados:
                self.lista_repuestos.addItem(
                    f"{r['nombre']} × {r['cantidad']}  ({r['precio']:.2f} €)"
                )
        else:
            self.lista_repuestos.addItem("(sin repuestos)")

        self.cmb_estado.setCurrentIndex(self.cmb_estado.findData(inc.estado.value))
        self.cmb_prioridad.setCurrentIndex(
            self.cmb_prioridad.findData(inc.prioridad.value)
        )
        idx = self.cmb_tecnico.findData(
            inc.tecnico_id if inc.tecnico_id is not None else -1
        )
        self.cmb_tecnico.setCurrentIndex(idx if idx >= 0 else 0)

    def _editar_descripcion(self) -> None:
        if not self._current_id:
            return
        inc = self._ctx.incidencias.obtener(
            self._current_id, es_demo=self._session.es_demo
        )
        if not inc:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar descripción")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)
        texto = QTextEdit()
        texto.setPlainText(inc.descripcion or "")
        texto.setMinimumHeight(140)
        form.addRow(texto)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._ctx.incidencias.actualizar_descripcion(
                self._current_id,
                texto.toPlainText(),
                actor_id=self._session.usuario_id,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self._mostrar(self._current_id)
            show_toast(self._status, "Descripción actualizada.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _adjuntar(self) -> None:
        if not self._current_id:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Adjuntar archivo",
            "",
            "Adjuntos (*.png *.jpg *.jpeg *.gif *.webp *.pdf *.txt *.log *.zip)",
        )
        if not ruta:
            return
        try:
            from pathlib import Path

            self._ctx.incidencias.agregar_adjunto(
                self._current_id,
                Path(ruta),
                usuario_id=self._session.usuario_id,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self._mostrar(self._current_id)
            show_toast(self._status, "Archivo adjuntado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _adjunto_seleccionado_id(self) -> int | None:
        item = self.lista_adjuntos.currentItem()
        if not item:
            return None
        aid = item.data(Qt.ItemDataRole.UserRole)
        return int(aid) if aid is not None else None

    def _abrir_adjunto(self, *_args) -> None:
        aid = self._adjunto_seleccionado_id()
        if not aid:
            show_toast(self._status, "Selecciona un adjunto.", error=True)
            return
        adj = self._ctx.incidencia_repo.obtener_adjunto(aid)
        if not adj:
            show_toast(self._status, "Adjunto no encontrado.", error=True)
            return
        ruta = self._ctx.incidencias.ruta_adjunto(adj)
        if not ruta.is_file():
            show_toast(self._status, "El archivo ya no está en disco.", error=True)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta.resolve())))

    def _eliminar_adjunto(self) -> None:
        aid = self._adjunto_seleccionado_id()
        if not aid or not self._current_id:
            show_toast(self._status, "Selecciona un adjunto.", error=True)
            return
        if QMessageBox.question(
            self, "Quitar adjunto", "¿Eliminar este archivo del ticket?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._ctx.incidencias.eliminar_adjunto(
                aid,
                actor_id=self._session.usuario_id,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self._mostrar(self._current_id)
            show_toast(self._status, "Adjunto eliminado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def nueva_incidencia(self) -> None:
        """API pública para abrir el diálogo de alta desde el Dashboard."""
        self._nueva()

    def _confirmar_resolucion(self) -> None:
        if not self._current_id:
            return
        if QMessageBox.question(
            self,
            "Confirmar resolución",
            "¿Confirmas que el problema quedó resuelto? Se cerrará el ticket.",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._ctx.incidencias.confirmar_resolucion(
                self._current_id,
                actor_id=self._session.usuario_id,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self.refresh()
            self._mostrar(self._current_id)
            show_toast(self._status, "Resolución confirmada. Ticket cerrado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _reabrir(self) -> None:
        if not self._current_id:
            return
        if QMessageBox.question(
            self,
            "Reabrir incidencia",
            "¿Reabrir este ticket? Volverá a la cola de soporte.",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self._ctx.incidencias.reabrir(
                self._current_id,
                actor_id=self._session.usuario_id,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self.refresh()
            self._mostrar(self._current_id)
            show_toast(self._status, "Incidencia reabierta.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _enviar_comentario(self) -> None:
        if not self._current_id:
            return
        texto = self.comentario_input.toPlainText().strip()
        if not texto:
            show_toast(self._status, "Escribe un comentario.", error=True)
            return
        try:
            self._ctx.incidencias.agregar_comentario(
                self._current_id,
                self._session.usuario_id,
                texto,
                rol=self._session.rol,
                es_demo=self._session.es_demo,
            )
            self.comentario_input.clear()
            self._mostrar(self._current_id)
            show_toast(self._status, "Comentario enviado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _nueva(self) -> None:
        dlg = NuevaIncidenciaDialog(self._ctx, self._session, self)
        if dlg.equipo.count() == 0:
            show_toast(
                self._status,
                "Registra primero un equipo en la sección Equipos.",
                error=True,
            )
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        if not data["equipo_id"] or not data["titulo"]:
            show_toast(self._status, "Equipo y título son obligatorios.", error=True)
            return
        try:
            creada = self._ctx.incidencias.crear(
                equipo_id=data["equipo_id"],
                titulo=data["titulo"],
                descripcion=data["descripcion"],
                prioridad=data["prioridad"],
                categoria=data["categoria"],
                actor_id=self._session.usuario_id,
            )
            self.refresh()
            self.seleccionar_incidencia(creada.id)  # type: ignore[arg-type]
            show_toast(self._status, f"{creada.codigo} creada.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _guardar_cambios(self) -> None:
        if not self._current_id or not self._session.es_tecnico():
            return
        prev_text = self.btn_guardar.text()
        self.btn_guardar.setEnabled(False)
        self.btn_guardar.setText("Guardando…")
        try:
            estado = EstadoIncidencia(self.cmb_estado.currentData())
            self._ctx.incidencias.cambiar_estado(
                self._current_id,
                estado,
                actor_id=self._session.usuario_id,
                avisar_bandeja=False,
            )
            self._ctx.incidencias.cambiar_prioridad(
                self._current_id,
                Prioridad(self.cmb_prioridad.currentData()),
                actor_id=self._session.usuario_id,
            )
            tecnico_id = self.cmb_tecnico.currentData()
            if tecnico_id == -1 or tecnico_id is None:
                asignacion = "sin técnico"
                self._ctx.incidencias.asignar_tecnico(
                    self._current_id,
                    None,
                    actor_id=self._session.usuario_id,
                    avisar_bandeja=False,
                )
            else:
                nombre = self.cmb_tecnico.currentText()
                asignacion = f"asignada a {nombre}"
                self._ctx.incidencias.asignar_tecnico(
                    self._current_id,
                    tecnico_id,
                    actor_id=self._session.usuario_id,
                    tecnico_nombre=nombre,
                    avisar_bandeja=False,
                )
            self.refresh()
            self._mostrar(self._current_id)
            inc = self._ctx.incidencias.obtener(
                self._current_id, es_demo=self._session.es_demo
            )
            codigo = inc.codigo if inc else "Incidencia"
            resumen = f"{codigo}: {estado.value} · {asignacion}"
            show_toast(self._status, f"Guardado — {resumen}")
            self._ctx.incidencias.avisar_bandeja(codigo, resumen)
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
        finally:
            self.btn_guardar.setText(prev_text)
            self.btn_guardar.setEnabled(True)

    def _add_intervencion(self) -> None:
        if not self._current_id or not self._session.es_tecnico():
            return
        dlg = IntervencionDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        desc = dlg.descripcion.toPlainText().strip()
        if not desc:
            return
        self.btn_interv.setEnabled(False)
        self.btn_interv.setText("Guardando…")
        try:
            self._ctx.incidencias.agregar_intervencion(
                self._current_id, self._session.usuario_id, desc
            )
            self.refresh()
            self._mostrar(self._current_id)
            show_toast(self._status, "Intervención añadida correctamente.")
            self._ctx.incidencias.avisar_bandeja(
                "Intervención", "Se registró una intervención en el ticket."
            )
        finally:
            self.btn_interv.setText("Añadir intervención")
            self.btn_interv.setEnabled(True)

    def _usar_repuesto(self) -> None:
        if not self._current_id or not self._session.es_tecnico():
            return
        dlg = UsarRepuestoDialog(self._ctx, self._session, self)
        if dlg.componente.count() == 0 and not self._session.puede_gestionar_inventario():
            show_toast(self._status, "No hay componentes con stock.", error=True)
            return
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        if not data["componente_id"]:
            show_toast(
                self._status,
                "Selecciona una pieza o añádela al inventario primero.",
                error=True,
            )
            return
        prev = self.btn_repuesto.text()
        self.btn_repuesto.setEnabled(False)
        self.btn_repuesto.setText("Registrando…")
        try:
            self._ctx.inventario.usar_en_incidencia(
                self._current_id,
                data["componente_id"],
                data["cantidad"],
                actor_id=self._session.usuario_id,
                incidencia_repo=self._ctx.incidencia_repo,
            )
            self._mostrar(self._current_id)
            msg = (
                f"Repuesto registrado (×{data['cantidad']}). "
                "Stock actualizado en inventario."
            )
            show_toast(self._status, msg)
            self._ctx.incidencias.avisar_bandeja("Repuesto", msg)
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
        finally:
            self.btn_repuesto.setText(prev)
            self.btn_repuesto.setEnabled(True)
