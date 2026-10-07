"""
Utilidades de UI compartidas: icono de ventana y logo escalado.

Leen el archivo de ``assets/`` (ver ``app.config.resolve_logo_path``)
para ventanas, login, diálogo Acerca de y bandeja del sistema.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from app.config import resolve_logo_path


def load_app_icon() -> QIcon | None:
    """Carga el logo como ``QIcon`` (escalado a 128px) o None si no hay archivo."""
    path = resolve_logo_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    # Escalar evita problemas con PNG grandes en el icono de ventana
    scaled = pixmap.scaled(
        128,
        128,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return QIcon(scaled)


def apply_window_icon(widget: QWidget) -> None:
    icon = load_app_icon()
    if icon is not None:
        widget.setWindowIcon(icon)


def logo_label(max_height: int = 72) -> QLabel | None:
    """QLabel con el logo escalado, o None si no hay archivo en assets/."""
    path = resolve_logo_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    label = QLabel()
    label.setPixmap(
        pixmap.scaledToHeight(max_height, Qt.TransformationMode.SmoothTransformation)
    )
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
