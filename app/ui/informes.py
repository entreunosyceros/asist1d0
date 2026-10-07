"""
Vista de informes y exportación CSV.

Muestra KPIs y tablas agregadas (estado, prioridad, técnico) filtradas
por el ámbito demo/real de la sesión.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.config import DATA_DIR
from app.ui.dashboard import KpiCard
from app.ui.page_chrome import apply_page_margins, build_page_header, show_toast


class InformesView(QWidget):
    """Página de estadísticas y exportación de datos."""

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
        btn = QPushButton("Exportar CSV")
        btn.clicked.connect(self._exportar)
        header, self._status = build_page_header(
            "Informes",
            "Estadísticas del ámbito actual (demo o real)",
            actions=[btn],
        )
        layout.addLayout(header)

        self.kpi_media = KpiCard("⏱", "Tiempo medio de cierre (h)")
        layout.addWidget(self.kpi_media)

        self.tabla_estado = QTableWidget(0, 2)
        self.tabla_estado.setHorizontalHeaderLabels(["Estado", "Total"])
        self.tabla_prio = QTableWidget(0, 2)
        self.tabla_prio.setHorizontalHeaderLabels(["Prioridad", "Total"])
        self.tabla_tec = QTableWidget(0, 2)
        self.tabla_tec.setHorizontalHeaderLabels(["Técnico", "Total"])

        for t in (self.tabla_estado, self.tabla_prio, self.tabla_tec):
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setAlternatingRowColors(True)
            t.horizontalHeader().setStretchLastSection(True)
            t.horizontalHeaderItem(1).setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

        row = QHBoxLayout()
        row.setSpacing(14)
        for title, tabla in (
            ("Por estado", self.tabla_estado),
            ("Por prioridad", self.tabla_prio),
            ("Por técnico", self.tabla_tec),
        ):
            col = QVBoxLayout()
            lbl = QLabel(title)
            lbl.setObjectName("PageSubtitle")
            col.addWidget(lbl)
            col.addWidget(tabla)
            row.addLayout(col)
        layout.addLayout(row)

    def _fill(self, tabla: QTableWidget, rows: list[dict], key_a: str, key_b: str) -> None:
        tabla.setRowCount(0)
        for r in rows:
            row = tabla.rowCount()
            tabla.insertRow(row)
            tabla.setItem(row, 0, QTableWidgetItem(str(r[key_a])))
            total_item = QTableWidgetItem(str(r[key_b]))
            total_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            tabla.setItem(row, 1, total_item)

    def refresh(self) -> None:
        ambito = self._session.es_demo
        self._fill(
            self.tabla_estado, self._ctx.informes.por_estado(es_demo=ambito), "estado", "total"
        )
        self._fill(
            self.tabla_prio,
            self._ctx.informes.por_prioridad(es_demo=ambito),
            "prioridad",
            "total",
        )
        self._fill(
            self.tabla_tec, self._ctx.informes.por_tecnico(es_demo=ambito), "tecnico", "total"
        )
        media = self._ctx.informes.tiempo_medio_cierre_horas(es_demo=ambito)
        self.kpi_media.set_value(media if media is not None else "—")

    def _exportar(self) -> None:
        default = str(DATA_DIR / "informe_incidencias.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar informe", default, "CSV (*.csv)"
        )
        if not path:
            return
        try:
            destino = self._ctx.informes.exportar_csv(
                Path(path), es_demo=self._session.es_demo
            )
            show_toast(self._status, f"Exportado: {destino.name}")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)
