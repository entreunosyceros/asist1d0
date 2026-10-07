"""
Vista de auditoría global (solo lectura).

Filtros por usuario, acción, entidad, id, fechas y texto en details.
Visible para Administrador y Técnico.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.audit import AuditAction, AuditEntity
from app.ui.page_chrome import apply_page_margins, build_page_header, show_toast


class AuditoriaView(QWidget):
    """Listado filtrable de ``audit_log``."""

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
        btn = QPushButton("Actualizar")
        btn.clicked.connect(self.refresh)
        header, self._status = build_page_header(
            "Auditoría",
            "Trazabilidad global de acciones (quién hizo qué). "
            "El historial del ticket sigue en la ficha de cada incidencia.",
            actions=[btn],
        )
        layout.addLayout(header)

        filtros = QHBoxLayout()
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        self.cmb_usuario = QComboBox()
        self.cmb_usuario.addItem("Todos", None)
        for u in self._ctx.usuarios.listar(es_demo=self._session.es_demo):
            self.cmb_usuario.addItem(f"{u.nombre} ({u.rol.etiqueta})", u.id)

        self.cmb_accion = QComboBox()
        self.cmb_accion.addItem("Todas", None)
        for a in AuditAction:
            self.cmb_accion.addItem(a.value, a.value)

        self.cmb_entidad = QComboBox()
        self.cmb_entidad.addItem("Todas", None)
        for e in AuditEntity:
            self.cmb_entidad.addItem(e.value, e.value)

        self.txt_entity_id = QLineEdit()
        self.txt_entity_id.setPlaceholderText("ID entidad / incidencia")
        self.txt_entity_id.setClearButtonEnabled(True)

        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.setSpecialValueText("—")
        self.date_desde.setDate(QDate.currentDate().addMonths(-1))

        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.setDate(QDate.currentDate())

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar en details…")
        self.txt_buscar.setClearButtonEnabled(True)

        form.addRow("Usuario", self.cmb_usuario)
        form.addRow("Acción", self.cmb_accion)
        form.addRow("Entidad", self.cmb_entidad)
        form.addRow("ID entidad", self.txt_entity_id)
        form.addRow("Desde", self.date_desde)
        form.addRow("Hasta", self.date_hasta)
        form.addRow("Texto", self.txt_buscar)

        col_f = QVBoxLayout()
        col_f.addLayout(form)
        filtros.addLayout(col_f, 1)

        hint = QLabel(
            "Solo lectura. Combina filtros y pulsa Actualizar. "
            "Para filtrar por incidencia, elige entidad «incidencia» e indica su ID."
        )
        hint.setWordWrap(True)
        hint.setObjectName("PageSubtitle")
        layout.addLayout(filtros)
        layout.addWidget(hint)

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha", "Usuario", "Acción", "Entidad", "ID", "Details", "IP"]
        )
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setColumnWidth(0, 140)
        self.tabla.setColumnWidth(1, 140)
        self.tabla.setColumnWidth(2, 110)
        self.tabla.setColumnWidth(3, 100)
        self.tabla.setColumnWidth(4, 50)
        self.tabla.setColumnWidth(5, 360)
        layout.addWidget(self.tabla, 1)

        for w in (
            self.cmb_usuario,
            self.cmb_accion,
            self.cmb_entidad,
            self.txt_entity_id,
            self.date_desde,
            self.date_hasta,
            self.txt_buscar,
        ):
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self.refresh)  # type: ignore[attr-defined]
            elif hasattr(w, "dateChanged"):
                w.dateChanged.connect(self.refresh)  # type: ignore[attr-defined]
            elif hasattr(w, "returnPressed"):
                w.returnPressed.connect(self.refresh)  # type: ignore[attr-defined]

    def refresh(self) -> None:
        user_id = self.cmb_usuario.currentData()
        action = self.cmb_accion.currentData()
        entity_type = self.cmb_entidad.currentData()
        entity_id = None
        raw_id = self.txt_entity_id.text().strip()
        if raw_id:
            try:
                entity_id = int(raw_id)
            except ValueError:
                show_toast(self._status, "ID de entidad no válido.", error=True)
                return

        desde = self.date_desde.date().toString("yyyy-MM-dd")
        hasta = self.date_hasta.date().toString("yyyy-MM-dd")
        texto = self.txt_buscar.text().strip() or None

        try:
            entradas = self._ctx.audit.listar(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                desde=desde,
                hasta=hasta,
                texto=texto,
                limite=500,
            )
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
            return

        self.tabla.setRowCount(0)
        for e in entradas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            usuario = e.usuario_nombre or (
                f"#{e.user_id}" if e.user_id is not None else "—"
            )
            vals = [
                e.timestamp or "",
                usuario,
                e.action,
                e.entity_type,
                "" if e.entity_id is None else str(e.entity_id),
                e.details or "",
                e.ip_address or "",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.tabla.setItem(row, col, item)

        show_toast(self._status, f"{len(entradas)} registro(s).")
