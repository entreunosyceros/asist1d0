"""
Dashboard inicial con KPIs según el rol.

El usuario ve un resumen de sus incidencias; técnico y admin ven
indicadores globales, últimas intervenciones y avisos de stock.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.ui.page_chrome import EmptyState, apply_page_margins, build_page_header


class KpiCard(QFrame):
    """Tarjeta compacta de indicador (icono + etiqueta + valor)."""

    def __init__(self, icono: str, etiqueta: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        top = QLabel(icono)
        top.setAlignment(Qt.AlignmentFlag.AlignLeft)
        top.setStyleSheet("font-size: 20px;")
        self.value = QLabel("0")
        self.value.setObjectName("KpiValue")
        label = QLabel(etiqueta)
        label.setObjectName("KpiLabel")
        layout.addWidget(top)
        layout.addWidget(self.value)
        layout.addWidget(label)

    def set_value(self, value) -> None:
        self.value.setText(str(value))


class DashboardView(QWidget):
    """Página de resumen; emite ``abrir_incidencia`` al pulsar un ítem."""

    abrir_incidencia = Signal(int)

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        header, _ = build_page_header(
            "Dashboard",
            "Resumen técnico"
            if self._session.puede_ver_panel_tecnico()
            else "Resumen de tus incidencias",
        )
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.kpi_pendientes = KpiCard("🔴", "Problemas pendientes")
        self.kpi_equipos = KpiCard("💻", "Equipos registrados")
        self.kpi_abiertas = KpiCard("🎫", "Incidencias abiertas")
        self.kpi_alta = KpiCard("🟡", "Prioridad alta / crítica")
        grid.addWidget(self.kpi_pendientes, 0, 0)
        grid.addWidget(self.kpi_equipos, 0, 1)
        grid.addWidget(self.kpi_abiertas, 0, 2)
        grid.addWidget(self.kpi_alta, 0, 3)
        layout.addLayout(grid)

        if self._session.puede_ver_panel_tecnico():
            row = QHBoxLayout()
            row.setSpacing(14)
            left = QVBoxLayout()
            left_title = QLabel("Últimas intervenciones")
            left_title.setObjectName("PageSubtitle")
            left.addWidget(left_title)
            self.lista_intervenciones = QListWidget()
            self.lista_intervenciones.itemClicked.connect(self._on_interv_clicked)
            left.addWidget(self.lista_intervenciones)
            self.empty_interv = EmptyState("Aún no hay intervenciones registradas.")
            left.addWidget(self.empty_interv)
            self.empty_interv.hide()

            right = QVBoxLayout()
            right_title = QLabel("Stock bajo")
            right_title.setObjectName("PageSubtitle")
            right.addWidget(right_title)
            self.lista_stock = QListWidget()
            right.addWidget(self.lista_stock)
            self.empty_stock = EmptyState("Stock en buen estado.")
            right.addWidget(self.empty_stock)
            self.empty_stock.hide()

            row.addLayout(left, 2)
            row.addLayout(right, 1)
            layout.addLayout(row)
        else:
            own_title = QLabel("Tus incidencias recientes")
            own_title.setObjectName("PageSubtitle")
            layout.addWidget(own_title)
            self.lista_propias = QListWidget()
            self.lista_propias.itemClicked.connect(self._on_propia_clicked)
            layout.addWidget(self.lista_propias)
            self.empty_propias = EmptyState(
                "No tienes incidencias todavía.",
            )
            layout.addWidget(self.empty_propias)
            self.empty_propias.hide()

        layout.addStretch()

    def _on_propia_clicked(self, item: QListWidgetItem) -> None:
        inc_id = item.data(Qt.ItemDataRole.UserRole)
        if inc_id:
            self.abrir_incidencia.emit(int(inc_id))

    def refresh(self) -> None:
        uid = None if self._session.es_tecnico() else self._session.usuario_id
        ambito = self._session.es_demo
        stats = self._ctx.incidencias.estadisticas_dashboard(
            usuario_id=uid, es_demo=ambito
        )
        equipos = self._ctx.equipos.contar(usuario_id=uid, es_demo=ambito)

        self.kpi_pendientes.set_value(stats["pendientes"])
        self.kpi_equipos.set_value(equipos)
        self.kpi_abiertas.set_value(stats["abiertas"])
        self.kpi_alta.set_value(stats["alta_prioridad"])

        if self._session.puede_ver_panel_tecnico():
            self.lista_intervenciones.clear()
            items = self._ctx.incidencia_repo.ultimas_intervenciones(8, es_demo=ambito)
            for iv in items:
                item = QListWidgetItem(
                    f"{iv.fecha or ''} — {iv.tecnico_nombre}: {iv.descripcion}"
                )
                item.setData(Qt.ItemDataRole.UserRole, iv.incidencia_id)
                self.lista_intervenciones.addItem(item)
            self.lista_intervenciones.setVisible(bool(items))
            self.empty_interv.setVisible(not items)

            self.lista_stock.clear()
            stock = self._ctx.inventario.stock_bajo(es_demo=ambito)
            for c in stock:
                self.lista_stock.addItem(f"{c.nombre}: {c.stock} uds.")
            self.lista_stock.setVisible(bool(stock))
            self.empty_stock.setVisible(not stock)
        else:
            self.lista_propias.clear()
            incs = self._ctx.incidencias.listar(
                usuario_id=self._session.usuario_id, es_demo=ambito
            )[:10]
            for inc in incs:
                item = QListWidgetItem(str(inc))
                item.setData(Qt.ItemDataRole.UserRole, inc.id)
                self.lista_propias.addItem(item)
            self.lista_propias.setVisible(bool(incs))
            self.empty_propias.setVisible(not incs)

    def _on_interv_clicked(self, item: QListWidgetItem) -> None:
        inc_id = item.data(Qt.ItemDataRole.UserRole)
        if inc_id:
            self.abrir_incidencia.emit(int(inc_id))
