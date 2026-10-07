"""
Diálogo para cambiar la contraseña de la cuenta en sesión.

Pide la contraseña actual, la nueva y su confirmación; delega la
validación en ``AuthService.cambiar_propia_contraseña``.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.auth.service import AuthService
from app.ui.resources import apply_window_icon


class ChangePasswordDialog(QDialog):
    """Formulario modal «Cambiar mi contraseña»."""

    def __init__(self, auth: AuthService, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth
        self.setWindowTitle("Cambiar mi contraseña")
        self.setMinimumWidth(400)
        apply_window_icon(self)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Introduce tu contraseña actual y la nueva. "
            "Solo afecta a tu propia cuenta."
        )
        intro.setWordWrap(True)
        intro.setObjectName("PageSubtitle")
        layout.addWidget(intro)

        form = QFormLayout()
        self.actual = QLineEdit()
        self.actual.setEchoMode(QLineEdit.EchoMode.Password)
        self.nueva = QLineEdit()
        self.nueva.setEchoMode(QLineEdit.EchoMode.Password)
        self.nueva.setPlaceholderText("Mínimo 6 caracteres")
        self.confirmacion = QLineEdit()
        self.confirmacion.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Contraseña actual", self.actual)
        form.addRow("Nueva contraseña", self.nueva)
        form.addRow("Confirmar nueva", self.confirmacion)
        layout.addLayout(form)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #dc2626;")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._guardar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _guardar(self) -> None:
        self.error.setText("")
        nueva = self.nueva.text()
        if nueva != self.confirmacion.text():
            self.error.setText("La confirmación no coincide con la nueva contraseña.")
            return
        try:
            self._auth.cambiar_propia_contraseña(self.actual.text(), nueva)
            self.accept()
        except (PermissionError, ValueError) as exc:
            self.error.setText(str(exc))
