"""
Widget visual de timeline para la ficha de incidencia.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.timeline import TimelineEvent, TimelineKind

_KIND_COLORS = {
    TimelineKind.CREAR: "#2563eb",
    TimelineKind.ASIGNAR: "#7c3aed",
    TimelineKind.ESTADO: "#d97706",
    TimelineKind.PRIORIDAD: "#ea580c",
    TimelineKind.COMENTARIO: "#059669",
    TimelineKind.INTERVENCION: "#0d9488",
    TimelineKind.ADJUNTO: "#64748b",
    TimelineKind.REPUESTO: "#c2410c",
    TimelineKind.OTRO: "#475569",
}


class _Rail(QWidget):
    """Columna izquierda: punto y trazo vertical."""

    def __init__(self, color: str, *, last: bool, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self._last = last
        self.setFixedWidth(22)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtGui import QColor, QPainter, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        # Línea hacia abajo (excepto último)
        if not self._last:
            pen = QPen(QColor("#d1d5db"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(cx, 14, cx, self.height())
        # Punto
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(cx - 5, 6, 10, 10)


class TimelineWidget(QFrame):
    """Lista vertical de eventos con aspecto de producto."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TimelinePanel")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(10, 10, 12, 10)
        self._lay.setSpacing(0)
        self.setMinimumHeight(160)
        self.clear()

    def clear(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        empty = QLabel("Sin actividad registrada")
        empty.setObjectName("TimelineEmpty")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lay.addWidget(empty)
        self._lay.addStretch(1)

    def set_events(self, events: list[TimelineEvent]) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if not events:
            empty = QLabel("Sin actividad registrada")
            empty.setObjectName("TimelineEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._lay.addWidget(empty)
            self._lay.addStretch(1)
            return

        prev_dia = None
        for i, ev in enumerate(events):
            if ev.dia and ev.dia != prev_dia:
                day = QLabel(ev.dia)
                day.setObjectName("TimelineDay")
                self._lay.addWidget(day)
                prev_dia = ev.dia
            self._lay.addWidget(self._row(ev, last=(i == len(events) - 1)))
        self._lay.addStretch(1)

    def _row(self, ev: TimelineEvent, *, last: bool) -> QWidget:
        row = QWidget()
        row.setObjectName("TimelineRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 10)
        h.setSpacing(8)

        color = _KIND_COLORS.get(ev.kind, "#475569")
        h.addWidget(_Rail(color, last=last), 0, Qt.AlignmentFlag.AlignTop)

        time = QLabel(ev.hora or "—")
        time.setObjectName("TimelineTime")
        time.setFixedWidth(42)
        time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        h.addWidget(time, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(2)
        title = QLabel(ev.titulo)
        title.setObjectName("TimelineTitle")
        title.setWordWrap(True)
        body.addWidget(title)
        if ev.cuerpo:
            quote = ev.cuerpo
            if ev.kind == TimelineKind.COMENTARIO:
                quote = f"«{quote}»"
            detail = QLabel(quote)
            detail.setObjectName("TimelineBody")
            detail.setWordWrap(True)
            body.addWidget(detail)
        h.addLayout(body, 1)
        return row
