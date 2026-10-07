"""
Gráficas ligeras con QPainter (sin QtCharts ni frameworks web).

Soporta barras verticales, barras horizontales y líneas con área.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QLabel, QWidget


class ChartCard(QFrame):
    """Contenedor con título para una gráfica."""

    def __init__(self, titulo: str, chart: QWidget, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        title = QLabel(titulo)
        title.setObjectName("ChartTitle")
        lay.addWidget(title)
        lay.addWidget(chart, 1)


class _BaseChart(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._labels: list[str] = []
        self._values: list[float] = []
        self._color = QColor("#2563eb")
        self._empty = "Sin datos"
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(
        self,
        labels: list[str],
        values: list[float],
        *,
        color: str = "#2563eb",
    ) -> None:
        self._labels = list(labels)
        self._values = [float(v) for v in values]
        self._color = QColor(color)
        self.update()

    def _max_value(self) -> float:
        if not self._values:
            return 1.0
        return max(max(self._values), 1.0)


class BarChartWidget(_BaseChart):
    """Barras verticales (categorías / días)."""

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)

        if not self._values:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._empty)
            return

        n = len(self._values)
        label_h = 22
        top_pad = 6
        plot = QRectF(
            rect.left(),
            rect.top() + top_pad,
            rect.width(),
            rect.height() - label_h - top_pad,
        )
        max_v = self._max_value()
        gap = max(4.0, plot.width() * 0.04)
        bar_w = max(6.0, (plot.width() - gap * (n + 1)) / n)

        font = QFont(self.font())
        font.setPointSize(9)
        painter.setFont(font)

        for i, (label, value) in enumerate(zip(self._labels, self._values)):
            x = plot.left() + gap + i * (bar_w + gap)
            h = (value / max_v) * (plot.height() - 4)
            y = plot.bottom() - h
            bar = QRectF(x, y, bar_w, h)

            grad = QLinearGradient(bar.topLeft(), bar.bottomLeft())
            c = self._color
            grad.setColorAt(0.0, c.lighter(118))
            grad.setColorAt(1.0, c)
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar, 4, 4)

            painter.setPen(QColor("#6b7280"))
            text = label if len(label) <= 8 else label[:7] + "…"
            painter.drawText(
                QRectF(x - 4, plot.bottom() + 2, bar_w + 8, label_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                text,
            )

            if value > 0:
                painter.setPen(QColor("#374151"))
                painter.drawText(
                    QRectF(x - 6, y - 16, bar_w + 12, 14),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                    _fmt_short(value),
                )


class HorizontalBarChartWidget(_BaseChart):
    """Barras horizontales (técnicos, categorías)."""

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 4, -8, -4)

        if not self._values:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._empty)
            return

        n = len(self._values)
        max_v = self._max_value()
        row_h = max(22.0, (rect.height() - 4) / n)
        label_w = min(110.0, rect.width() * 0.32)
        value_w = 36.0
        bar_area = rect.width() - label_w - value_w - 12

        font = QFont(self.font())
        font.setPointSize(10)
        painter.setFont(font)

        for i, (label, value) in enumerate(zip(self._labels, self._values)):
            y = rect.top() + i * row_h
            painter.setPen(QColor("#374151"))
            text = label if len(label) <= 16 else label[:15] + "…"
            painter.drawText(
                QRectF(rect.left(), y, label_w, row_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )

            bw = (value / max_v) * bar_area if max_v else 0
            bar = QRectF(rect.left() + label_w + 6, y + row_h * 0.22, bw, row_h * 0.56)
            painter.setBrush(self._color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar, 3, 3)

            painter.setPen(QColor("#6b7280"))
            painter.drawText(
                QRectF(rect.right() - value_w, y, value_w, row_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                _fmt_short(value),
            )


class LineChartWidget(_BaseChart):
    """Línea con área (tendencias / tiempo medio)."""

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)

        if not self._values:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._empty)
            return

        n = len(self._values)
        label_h = 20
        plot = QRectF(
            rect.left() + 4,
            rect.top() + 4,
            rect.width() - 8,
            rect.height() - label_h - 8,
        )
        max_v = self._max_value()
        pts: list[QPointF] = []
        for i, value in enumerate(self._values):
            if n == 1:
                x = plot.left() + plot.width() / 2
            else:
                x = plot.left() + (i / (n - 1)) * plot.width()
            y = plot.bottom() - (value / max_v) * plot.height()
            pts.append(QPointF(x, y))

        # Área bajo la curva
        if len(pts) >= 2:
            poly = QPolygonF(pts)
            poly.append(QPointF(pts[-1].x(), plot.bottom()))
            poly.append(QPointF(pts[0].x(), plot.bottom()))
            fill = QColor(self._color)
            fill.setAlpha(40)
            painter.setBrush(fill)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(poly)

        pen = QPen(self._color, 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(1, len(pts)):
            painter.drawLine(pts[i - 1], pts[i])

        painter.setBrush(self._color)
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        for p in pts:
            painter.drawEllipse(p, 3.5, 3.5)

        font = QFont(self.font())
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#6b7280"))
        step = max(1, n // 6)
        for i, label in enumerate(self._labels):
            if i % step != 0 and i != n - 1:
                continue
            x = pts[i].x()
            painter.drawText(
                QRectF(x - 24, plot.bottom() + 2, 48, label_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )


def _fmt_short(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}".replace(".", ",")
