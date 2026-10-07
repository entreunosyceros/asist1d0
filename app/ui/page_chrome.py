"""
Chrome visual compartido entre páginas.

Unifica márgenes, cabeceras (título + subtítulo + acciones), mensajes
de estado (toasts) y estados vacíos para que todas las vistas se vean
consistentes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


# Márgenes interiores estándar de cada página del contenido.
PAGE_MARGINS = (24, 24, 24, 24)

_active_banner: QFrame | None = None


def apply_page_margins(layout: QVBoxLayout) -> None:
    """Aplica márgenes y espaciado homogéneos al layout de una página."""
    layout.setContentsMargins(*PAGE_MARGINS)
    layout.setSpacing(14)


def build_page_header(
    title: str,
    subtitle: str = "",
    actions: list[QWidget] | None = None,
) -> tuple[QVBoxLayout, QLabel | None]:
    """Construye cabecera de página. Devuelve ``(header_layout, status_label)``."""
    wrap = QVBoxLayout()
    wrap.setSpacing(4)

    top = QHBoxLayout()
    title_col = QVBoxLayout()
    title_col.setSpacing(2)
    lbl_title = QLabel(title)
    lbl_title.setObjectName("PageTitle")
    title_col.addWidget(lbl_title)
    if subtitle:
        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("PageSubtitle")
        title_col.addWidget(lbl_sub)
    top.addLayout(title_col, 1)

    if actions:
        for w in actions:
            top.addWidget(w)

    wrap.addLayout(top)

    status = QLabel("")
    status.setObjectName("StatusToast")
    status.setVisible(False)
    wrap.addWidget(status)
    return wrap, status


def _show_floating_banner(host: QWidget, message: str, *, error: bool = False) -> None:
    """Banner flotante encima de la ventana para feedback muy visible."""
    global _active_banner
    if _active_banner is not None:
        _active_banner.hide()
        _active_banner.deleteLater()
        _active_banner = None

    banner = QFrame(host)
    banner.setObjectName("ActionBanner")
    banner.setProperty("error", "true" if error else "false")
    banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    lay = QHBoxLayout(banner)
    lay.setContentsMargins(18, 14, 18, 14)
    prefix = QLabel("✗" if error else "✓")
    prefix.setObjectName("ActionBannerIcon")
    text = QLabel(message)
    text.setObjectName("ActionBannerText")
    text.setWordWrap(True)
    lay.addWidget(prefix)
    lay.addWidget(text, 1)
    banner.adjustSize()
    width = min(max(banner.sizeHint().width(), 320), max(host.width() - 48, 280))
    banner.setFixedWidth(width)
    banner.adjustSize()
    x = max(24, (host.width() - banner.width()) // 2)
    y = 28
    banner.move(x, y)
    banner.raise_()
    banner.show()
    _active_banner = banner

    def _clear() -> None:
        global _active_banner
        if _active_banner is banner:
            banner.hide()
            banner.deleteLater()
            _active_banner = None

    QTimer.singleShot(3500, _clear)


def show_toast(label: QLabel | None, message: str, *, error: bool = False) -> None:
    """Toast en cabecera + banner flotante en la ventana (feedback claro)."""
    if label is not None:
        label.setProperty("error", "true" if error else "false")
        label.style().unpolish(label)
        label.style().polish(label)
        label.setText(message)
        label.setVisible(True)
        QTimer.singleShot(3500, lambda: label.setVisible(False))
        host = label.window()
        if host is not None:
            _show_floating_banner(host, message, error=error)
    else:
        # Sin label: intentar sobre la ventana activa no es fiable; no-op.
        pass


class EmptyState(QWidget):
    def __init__(
        self,
        mensaje: str,
        cta_texto: str = "",
        on_cta=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyState")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = QLabel(mensaje)
        msg.setObjectName("EmptyStateMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        lay.addWidget(msg)
        if cta_texto and on_cta:
            btn = QPushButton(cta_texto)
            btn.clicked.connect(on_cta)
            lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
