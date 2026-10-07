"""
Dashboard con KPIs, paneles SLA/técnicos y gráficas nativas PySide6.

El usuario ve un resumen personal; técnico y admin ven métricas globales,
cumplimiento SLA y series (día, categoría, prioridad, resolución, técnico).
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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.ui.charts import (
    BarChartWidget,
    ChartCard,
    HorizontalBarChartWidget,
    LineChartWidget,
)
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


class MetricRow(QWidget):
    """Fila etiqueta · valor dentro de un panel de métricas."""

    def __init__(self, etiqueta: str, parent=None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)
        self._label = QLabel(etiqueta)
        self._label.setObjectName("MetricLabel")
        self._value = QLabel("—")
        self._value.setObjectName("MetricValue")
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self._label, 1)
        lay.addWidget(self._value)

    def set_value(self, value, *, emphasize: bool = False) -> None:
        self._value.setText(str(value))
        self._value.setProperty("warn", "true" if emphasize else "false")
        self._value.style().unpolish(self._value)
        self._value.style().polish(self._value)


class MetricsPanel(QFrame):
    """Bloque tipográfico INCIDENCIAS / SLA / TÉCNICOS."""

    def __init__(self, titulo: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricsPanel")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 14, 16, 14)
        self._lay.setSpacing(4)
        title = QLabel(titulo)
        title.setObjectName("MetricsPanelTitle")
        self._lay.addWidget(title)
        line = QFrame()
        line.setObjectName("MetricsDivider")
        line.setFrameShape(QFrame.Shape.HLine)
        self._lay.addWidget(line)
        self._rows: dict[str, MetricRow] = {}
        self._extra = QVBoxLayout()
        self._extra.setSpacing(2)
        self._lay.addLayout(self._extra)

    def add_row(self, key: str, etiqueta: str) -> MetricRow:
        row = MetricRow(etiqueta)
        self._rows[key] = row
        self._extra.addWidget(row)
        return row

    def set_row(self, key: str, value, *, emphasize: bool = False) -> None:
        if key in self._rows:
            self._rows[key].set_value(value, emphasize=emphasize)

    def set_list_rows(self, items: list[tuple[str, str]]) -> None:
        """Sustituye filas dinámicas (p. ej. técnicos)."""
        while self._extra.count():
            item = self._extra.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._rows.clear()
        if not items:
            empty = QLabel("Sin asignaciones abiertas")
            empty.setObjectName("MetricLabel")
            self._extra.addWidget(empty)
            return
        for i, (etiqueta, valor) in enumerate(items):
            key = f"dyn_{i}"
            row = self.add_row(key, etiqueta)
            row.set_value(valor)


class DashboardView(QWidget):
    """Página de resumen; emite ``abrir_incidencia`` al pulsar un ítem."""

    abrir_incidencia = Signal(int)
    solicitar_nueva_incidencia = Signal()
    solicitar_nuevo_equipo = Signal()

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._build()
        self.refresh()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        apply_page_margins(layout)

        header, _ = build_page_header(
            "Dashboard",
            "Métricas, SLA y tendencias"
            if self._session.puede_ver_panel_tecnico()
            else "Resumen de tus incidencias",
        )
        layout.addLayout(header)

        if self._session.puede_ver_panel_tecnico():
            self._build_tech(layout)
        else:
            self._build_user(layout)

        layout.addStretch()

    def _build_user(self, layout: QVBoxLayout) -> None:
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

        own_title = QLabel("Tus incidencias recientes")
        own_title.setObjectName("PageSubtitle")
        layout.addWidget(own_title)
        self.lista_propias = QListWidget()
        self.lista_propias.itemClicked.connect(self._on_propia_clicked)
        layout.addWidget(self.lista_propias)
        self.empty_propias = EmptyState(
            "No tienes incidencias todavía.",
            "+ Nueva incidencia",
            self._cta_nueva_incidencia,
        )
        layout.addWidget(self.empty_propias)
        self.empty_propias.hide()
        self.empty_sin_equipo = EmptyState(
            "Registra primero un equipo para poder abrir incidencias.",
            "+ Nuevo equipo",
            self._cta_nuevo_equipo,
        )
        layout.addWidget(self.empty_sin_equipo)
        self.empty_sin_equipo.hide()

    def _build_tech(self, layout: QVBoxLayout) -> None:
        panels = QHBoxLayout()
        panels.setSpacing(14)

        self.panel_inc = MetricsPanel("INCIDENCIAS")
        self.panel_inc.add_row("abiertas", "Abiertas")
        self.panel_inc.add_row("en_proceso", "En proceso")
        self.panel_inc.add_row("vencidas", "Vencidas")
        self.panel_inc.add_row("resueltas", "Resueltas")
        panels.addWidget(self.panel_inc, 1)

        self.panel_sla = MetricsPanel("SLA")
        self.panel_sla.add_row("cumplimiento", "Cumplimiento")
        self.panel_sla.add_row("tiempo_medio", "Tiempo medio")
        panels.addWidget(self.panel_sla, 1)

        self.panel_tec = MetricsPanel("TÉCNICOS")
        panels.addWidget(self.panel_tec, 1)

        layout.addLayout(panels)

        # KPIs compactos adicionales
        grid = QGridLayout()
        grid.setSpacing(14)
        self.kpi_equipos = KpiCard("💻", "Equipos")
        self.kpi_alta = KpiCard("🟠", "Alta / crítica")
        self.kpi_total = KpiCard("📊", "Total tickets")
        self.kpi_pendientes = KpiCard("⏸", "Pendiente usuario")
        grid.addWidget(self.kpi_equipos, 0, 0)
        grid.addWidget(self.kpi_alta, 0, 1)
        grid.addWidget(self.kpi_total, 0, 2)
        grid.addWidget(self.kpi_pendientes, 0, 3)
        layout.addLayout(grid)

        charts = QGridLayout()
        charts.setSpacing(14)

        self.chart_dia = BarChartWidget()
        self.chart_cat = HorizontalBarChartWidget()
        self.chart_prio = BarChartWidget()
        self.chart_res = LineChartWidget()
        self.chart_tec = HorizontalBarChartWidget()

        charts.addWidget(ChartCard("Incidencias por día", self.chart_dia), 0, 0)
        charts.addWidget(ChartCard("Incidencias por categoría", self.chart_cat), 0, 1)
        charts.addWidget(ChartCard("Incidencias por prioridad", self.chart_prio), 1, 0)
        charts.addWidget(
            ChartCard("Tiempo medio de resolución (h)", self.chart_res), 1, 1
        )
        charts.addWidget(
            ChartCard("Incidencias abiertas por técnico", self.chart_tec), 2, 0, 1, 2
        )
        for r in range(3):
            charts.setRowStretch(r, 1)
        layout.addLayout(charts)

        row = QHBoxLayout()
        row.setSpacing(14)
        left = QVBoxLayout()
        left_title = QLabel("Últimas intervenciones")
        left_title.setObjectName("PageSubtitle")
        left.addWidget(left_title)
        self.lista_intervenciones = QListWidget()
        self.lista_intervenciones.setMaximumHeight(160)
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
        self.lista_stock.setMaximumHeight(160)
        right.addWidget(self.lista_stock)
        self.empty_stock = EmptyState("Stock en buen estado.")
        right.addWidget(self.empty_stock)
        self.empty_stock.hide()

        row.addLayout(left, 2)
        row.addLayout(right, 1)
        layout.addLayout(row)

    def _cta_nueva_incidencia(self) -> None:
        self.solicitar_nueva_incidencia.emit()

    def _cta_nuevo_equipo(self) -> None:
        self.solicitar_nuevo_equipo.emit()

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

        if self._session.puede_ver_panel_tecnico():
            self._refresh_tech(stats, equipos, ambito)
        else:
            self._refresh_user(stats, equipos, ambito)

    def _refresh_user(self, stats: dict, equipos: int, ambito: bool) -> None:
        self.kpi_pendientes.set_value(stats["pendientes"])
        self.kpi_equipos.set_value(equipos)
        self.kpi_abiertas.set_value(stats["abiertas_total"])
        self.kpi_alta.set_value(stats["alta_prioridad"])

        self.lista_propias.clear()
        incs = self._ctx.incidencias.listar(
            usuario_id=self._session.usuario_id, es_demo=ambito
        )[:10]
        for inc in incs:
            item = QListWidgetItem(str(inc))
            item.setData(Qt.ItemDataRole.UserRole, inc.id)
            self.lista_propias.addItem(item)
        tiene_incs = bool(incs)
        sin_equipo = equipos == 0
        self.lista_propias.setVisible(tiene_incs)
        self.empty_propias.setVisible(not tiene_incs and not sin_equipo)
        self.empty_sin_equipo.setVisible(not tiene_incs and sin_equipo)

    def _refresh_tech(self, stats: dict, equipos: int, ambito: bool) -> None:
        self.panel_inc.set_row("abiertas", stats["abiertas"])
        self.panel_inc.set_row("en_proceso", stats["en_proceso"])
        self.panel_inc.set_row(
            "vencidas", stats["vencidas"], emphasize=stats["vencidas"] > 0
        )
        self.panel_inc.set_row("resueltas", stats["resueltas"])

        sla = stats.get("sla_cumplimiento_pct")
        self.panel_sla.set_row(
            "cumplimiento",
            f"{_fmt_num(sla)} %" if sla is not None else "—",
        )
        media = stats.get("tiempo_medio_horas")
        self.panel_sla.set_row(
            "tiempo_medio",
            f"{_fmt_num(media)} h" if media is not None else "—",
        )

        tech_items = [
            (r["tecnico"], str(r["total"])) for r in stats.get("por_tecnico", [])[:8]
        ]
        self.panel_tec.set_list_rows(tech_items)

        self.kpi_equipos.set_value(equipos)
        self.kpi_alta.set_value(stats["alta_prioridad"])
        self.kpi_total.set_value(stats["total"])
        self.kpi_pendientes.set_value(stats["pendientes"])

        informes = self._ctx.informes
        por_dia = informes.por_dia(14, es_demo=ambito)
        self.chart_dia.set_data(
            [r["etiqueta"] for r in por_dia],
            [r["total"] for r in por_dia],
            color="#2563eb",
        )

        por_cat = informes.por_categoria(es_demo=ambito)[:8]
        self.chart_cat.set_data(
            [r["categoria"] for r in por_cat],
            [r["total"] for r in por_cat],
            color="#0d9488",
        )

        por_prio = informes.por_prioridad(es_demo=ambito)
        orden = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
        por_prio = sorted(
            por_prio, key=lambda r: orden.get(str(r["prioridad"]), 9)
        )
        self.chart_prio.set_data(
            [str(r["prioridad"]) for r in por_prio],
            [int(r["total"]) for r in por_prio],
            color="#ea580c",
        )

        por_res = informes.tiempo_medio_por_dia(14, es_demo=ambito)
        self.chart_res.set_data(
            [r["etiqueta"] for r in por_res],
            [r["media"] for r in por_res],
            color="#ca8a04",
        )

        tec = stats.get("por_tecnico", [])[:8]
        self.chart_tec.set_data(
            [r["tecnico"] for r in tec],
            [r["total"] for r in tec],
            color="#1d4ed8",
        )

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

    def _on_interv_clicked(self, item: QListWidgetItem) -> None:
        inc_id = item.data(Qt.ItemDataRole.UserRole)
        if inc_id:
            self.abrir_incidencia.emit(int(inc_id))


def _fmt_num(value) -> str:
    """Formato español ligero (coma decimal)."""
    if value is None:
        return "—"
    if isinstance(value, float):
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        return text.replace(".", ",")
    return str(value)
