"""
Diálogo «Acerca de» Asist{1d0}.

Muestra el logo, la versión, una breve descripción del programa y un
botón que abre el repositorio en el navegador.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.config import APP_DESCRIPTION, APP_NAME, APP_REPO_URL, APP_VERSION
from app.ui.resources import apply_window_icon, logo_label


class AboutDialog(QDialog):
    """Ventana modal con información del producto y enlace a GitHub."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {APP_NAME}")
        self.setMinimumSize(520, 420)
        self.resize(560, 460)
        apply_window_icon(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(16)

        logo = logo_label(128)
        if logo is not None:
            layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Versión {APP_VERSION}")
        version.setObjectName("PageSubtitle")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        desc = QLabel(APP_DESCRIPTION)
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setObjectName("MetaValue")
        desc.setMinimumHeight(72)
        layout.addWidget(desc)

        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_github = QPushButton("Ver en GitHub")
        btn_github.setMinimumWidth(140)
        btn_github.clicked.connect(self._open_github)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("SecondaryButton")
        btn_cerrar.setMinimumWidth(100)
        btn_cerrar.clicked.connect(self.accept)
        buttons.addWidget(btn_github)
        buttons.addWidget(btn_cerrar)
        layout.addLayout(buttons)

    def _open_github(self) -> None:
        QDesktopServices.openUrl(QUrl(APP_REPO_URL))
