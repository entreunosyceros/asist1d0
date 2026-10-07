"""
Diálogo de acceso a Asist{1d0}.

Ventana sin marco del sistema: solo se muestra la tarjeta del formulario
sobre fondo transparente. Permite arrastrar, recordar el email y cerrar
con ✕ (sale de la aplicación).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import AuthService, SessionContext
from app.config import APP_NAME
from app.prefs import get_remembered_login, set_remembered_login
from app.ui.resources import apply_window_icon, logo_label


class LoginWindow(QDialog):
    """Formulario de autenticación (email + contraseña)."""

    def __init__(self, auth: AuthService, parent=None) -> None:
        super().__init__(parent)
        self._auth = auth
        self.session: SessionContext | None = None
        self._busy = False
        self._drag_pos: QPoint | None = None
        self.setObjectName("LoginDialog")
        self.setWindowTitle(f"Acceso — {APP_NAME}")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        apply_window_icon(self)
        self._build()
        self._load_remembered()
        self.adjustSize()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Sin barra de título: iniciamos arrastre de la ventana.
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QWidget()
        card.setObjectName("LoginCard")
        card.setFixedWidth(380)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 20, 32, 32)
        card_layout.setSpacing(14)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addStretch()
        btn_cerrar = QPushButton("✕")
        btn_cerrar.setObjectName("LoginCloseButton")
        btn_cerrar.setFixedSize(28, 28)
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setToolTip("Cerrar")
        btn_cerrar.clicked.connect(self.reject)
        top.addWidget(btn_cerrar)
        card_layout.addLayout(top)

        logo = logo_label(72)
        if logo is not None:
            card_layout.addWidget(logo)

        title = QLabel(APP_NAME if logo is not None else f"🛠️ {APP_NAME}")
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Sistema de soporte técnico")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #64748b;")

        form = QFormLayout()
        self.email = QLineEdit()
        self.email.setPlaceholderText("email@asist1d0.local")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Contraseña")
        form.addRow("Email", self.email)
        form.addRow("Contraseña", self.password)

        self.remember = QCheckBox("Recordar usuario")
        self.remember.setToolTip(
            "Guarda el último email en este equipo. La contraseña no se almacena."
        )

        self.error = QLabel("")
        self.error.setStyleSheet("color: #dc2626;")
        self.error.setWordWrap(True)

        self.btn_entrar = QPushButton("Entrar")
        self.btn_entrar.setDefault(True)
        self.btn_entrar.clicked.connect(self._on_login)

        hint = QLabel(
            "Demo: admin@asist1d0.local / admin123\n"
            "tecnico@asist1d0.local / tecnico123\n"
            "juan@asist1d0.local / juan123"
        )
        hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addLayout(form)
        card_layout.addWidget(self.remember)
        card_layout.addWidget(self.error)
        card_layout.addWidget(self.btn_entrar)
        card_layout.addWidget(hint)

        root.addWidget(card)

    def _load_remembered(self) -> None:
        recordar, email = get_remembered_login()
        self.remember.setChecked(recordar)
        if recordar and email:
            self.email.setText(email)
            self.password.clear()
            self.password.setFocus()
        else:
            # Primera vez / sin recordar: atajos demo
            self.email.setText("admin@asist1d0.local")
            self.password.setText("admin123")

    def _on_login(self) -> None:
        if self._busy:
            return
        self._busy = True
        self.btn_entrar.setEnabled(False)
        email = self.email.text().strip()
        password = self.password.text()
        try:
            self.session = self._auth.login(email, password)
            set_remembered_login(self.remember.isChecked(), email)
            self.accept()
        except PermissionError as exc:
            self.error.setText(str(exc))
            self._busy = False
            self.btn_entrar.setEnabled(True)
