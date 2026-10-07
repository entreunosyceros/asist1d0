"""
Panel técnico: historial, logs y consultas predefinidas.

Herramientas de diagnóstico para técnico y administrador (consultas
SQL de apoyo, historial global y lectura del fichero de log).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.config import LOG_FILE
from app.ui.page_chrome import apply_page_margins, build_page_header


class PanelTecnicoView(QWidget):
    """Pestaña de utilidades técnicas y seguimiento."""

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
            "Panel técnico",
            "Consultas predefinidas, historial global y logs de la aplicación",
        )
        layout.addLayout(header)

        tabs = QTabWidget()

        # Consultas
        consultas = QWidget()
        clay = QVBoxLayout(consultas)
        row = QHBoxLayout()
        self.cmb_consulta = QComboBox()
        self._consultas = self._ctx.historial.consultas_predefinidas(
            self._ctx.db, es_demo=self._session.es_demo
        )
        for nombre in self._consultas:
            self.cmb_consulta.addItem(nombre)
        btn = QPushButton("Ejecutar")
        btn.clicked.connect(self._ejecutar_consulta)
        row.addWidget(self.cmb_consulta, 1)
        row.addWidget(btn)
        clay.addLayout(row)
        self.tabla = QTableWidget(0, 0)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        clay.addWidget(self.tabla)
        tabs.addTab(consultas, "Consultas SQL")

        # Historial
        hist = QWidget()
        hlay = QVBoxLayout(hist)
        self.hist_text = QPlainTextEdit()
        self.hist_text.setReadOnly(True)
        hlay.addWidget(self.hist_text)
        btn_h = QPushButton("Actualizar historial")
        btn_h.setObjectName("SecondaryButton")
        btn_h.clicked.connect(self._cargar_historial)
        hlay.addWidget(btn_h)
        tabs.addTab(hist, "Historial")

        # Logs
        logs = QWidget()
        llay = QVBoxLayout(logs)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        llay.addWidget(self.log_text)
        btn_l = QPushButton("Recargar log")
        btn_l.setObjectName("SecondaryButton")
        btn_l.clicked.connect(self._cargar_log)
        llay.addWidget(btn_l)
        tabs.addTab(logs, "Logs")

        layout.addWidget(tabs)
        self._ejecutar_consulta()
        self._cargar_historial()
        self._cargar_log()

    def refresh(self) -> None:
        self._consultas = self._ctx.historial.consultas_predefinidas(
            self._ctx.db, es_demo=self._session.es_demo
        )
        self._ejecutar_consulta()
        self._cargar_historial()
        self._cargar_log()

    def _ejecutar_consulta(self) -> None:
        nombre = self.cmb_consulta.currentText()
        rows = self._consultas.get(nombre, [])
        self.tabla.clear()
        if not rows:
            self.tabla.setRowCount(0)
            self.tabla.setColumnCount(0)
            return
        cols = list(rows[0].keys())
        self.tabla.setColumnCount(len(cols))
        self.tabla.setHorizontalHeaderLabels(cols)
        self.tabla.setRowCount(0)
        for r in rows:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            for col, key in enumerate(cols):
                self.tabla.setItem(row, col, QTableWidgetItem(str(r[key])))
        self.tabla.resizeColumnsToContents()

    def _cargar_historial(self) -> None:
        entradas = self._ctx.historial.global_(80, es_demo=self._session.es_demo)
        lines = []
        for h in entradas:
            who = h.usuario_nombre or "sistema"
            lines.append(f"[{h.fecha}] INC-{h.incidencia_id:05d} · {who}: {h.accion}")
        self.hist_text.setPlainText("\n".join(lines) if lines else "(sin historial)")

    def _cargar_log(self) -> None:
        if LOG_FILE.exists():
            text = LOG_FILE.read_text(encoding="utf-8")
            # últimas líneas
            lines = text.splitlines()[-200:]
            self.log_text.setPlainText("\n".join(lines))
        else:
            self.log_text.setPlainText("(log vacío)")
