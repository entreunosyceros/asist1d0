"""
Cuadro de búsqueda global con resultados agrupados.

Atajo Ctrl+K: enfoca el campo. Enter abre el resultado resaltado.
El panel flota bajo el input (sin robar foco) para mostrar todos los hits.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.enums import Rol
from app.services.search_service import GlobalSearchResults, SearchHit


_SECTION_LABELS = (
    ("incidencias", "Incidencias"),
    ("equipos", "Equipos"),
    ("usuarios", "Usuarios"),
    ("comentarios", "Comentarios"),
    ("articulos", "Artículos"),
)


class _HitRow(QFrame):
    clicked = Signal(object)

    def __init__(self, hit: SearchHit, parent=None) -> None:
        super().__init__(parent)
        self.hit = hit
        self.setObjectName("SearchHitRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", "false")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        title = QLabel(hit.title)
        title.setObjectName("SearchHitTitle")
        title.setWordWrap(True)
        lay.addWidget(title)
        if hit.subtitle:
            sub = QLabel(hit.subtitle)
            sub.setObjectName("SearchHitSub")
            sub.setWordWrap(True)
            lay.addWidget(sub)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.hit)
        super().mousePressEvent(event)


class SearchResultsPanel(QFrame):
    """Desplegable flotante bajo la barra (no acepta foco)."""

    activated = Signal(object)

    def __init__(self, parent=None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self.setObjectName("SearchResultsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumWidth(420)
        self.setMinimumHeight(120)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        root.addWidget(self._scroll)

        self._body = QWidget()
        self._body.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._lay = QVBoxLayout(self._body)
        self._lay.setContentsMargins(8, 8, 8, 8)
        self._lay.setSpacing(2)
        self._scroll.setWidget(self._body)

        self._rows: list[_HitRow] = []
        self._index = -1

    def show_results(self, results: GlobalSearchResults) -> None:
        self._rebuild_empty()
        self._index = -1

        if not results.query:
            hint = QLabel("Escribe para buscar incidencias, equipos, usuarios…")
            hint.setObjectName("SearchHint")
            hint.setWordWrap(True)
            self._lay.insertWidget(0, hint)
            return

        if results.total == 0:
            hint = QLabel(f"Sin resultados para «{results.query}»")
            hint.setObjectName("SearchHint")
            hint.setWordWrap(True)
            self._lay.insertWidget(0, hint)
            return

        for attr, label in _SECTION_LABELS:
            hits: list[SearchHit] = getattr(results, attr)
            if not hits:
                continue
            header = QLabel(label.upper())
            header.setObjectName("SearchSectionTitle")
            self._lay.insertWidget(self._lay.count() - 1, header)
            for hit in hits:
                row = _HitRow(hit)
                row.clicked.connect(self.activated.emit)
                self._lay.insertWidget(self._lay.count() - 1, row)
                self._rows.append(row)

        if self._rows:
            self._set_index(0)

    def preferred_height(self, max_height: int = 420) -> int:
        """Altura según contenido, con tope para no tapar toda la ventana."""
        self._body.adjustSize()
        content_h = self._body.sizeHint().height() + 16
        return max(120, min(max_height, content_h))

    def _rebuild_empty(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._rows.clear()
        self._lay.addStretch()

    def move_selection(self, delta: int) -> None:
        if not self._rows:
            return
        nxt = 0 if self._index < 0 else self._index + delta
        nxt = max(0, min(len(self._rows) - 1, nxt))
        self._set_index(nxt)

    def current_hit(self) -> SearchHit | None:
        if 0 <= self._index < len(self._rows):
            return self._rows[self._index].hit
        return None

    def _set_index(self, index: int) -> None:
        for i, row in enumerate(self._rows):
            row.set_selected(i == index)
        self._index = index
        if 0 <= index < len(self._rows):
            self._scroll.ensureWidgetVisible(self._rows[index])


class GlobalSearchBar(QWidget):
    """Campo 🔎 Buscar… con desplegable de resultados bajo el input."""

    activated = Signal(object)  # SearchHit

    def __init__(
        self, ctx: AppContext, session: SessionContext, parent=None
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self.setObjectName("GlobalSearchBar")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.input = QLineEdit()
        self.input.setObjectName("GlobalSearchInput")
        self.input.setPlaceholderText("🔎 Buscar…  (Ctrl+K)")
        self.input.setClearButtonEnabled(True)
        self.input.textChanged.connect(self._on_text)
        self.input.installEventFilter(self)
        lay.addWidget(self.input)

        # Padre = ventana principal para coordenadas globales estables.
        self._panel = SearchResultsPanel(self.window() if self.window() else self)
        self._panel.activated.connect(self._emit_hit)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._run_search)

        self._last: GlobalSearchResults | None = None
        self._app_filter_installed = False

    def focus_search(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.input.selectAll()
        if self.input.text().strip():
            self._run_search()
        else:
            self._panel.show_results(GlobalSearchResults(query=""))
            self._place_panel()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # Reparentar al top-level cuando la ventana ya existe.
        top = self.window()
        if top is not None and self._panel.parent() is not top:
            self._panel.setParent(top, self._panel.windowFlags())
        self._install_app_filter()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._panel.hide()
        super().hideEvent(event)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.input:
            et = event.type()
            if et == QEvent.Type.KeyPress:
                key = event.key()  # type: ignore[attr-defined]
                if key == Qt.Key.Key_Down:
                    self._place_panel()
                    self._panel.move_selection(1)
                    return True
                if key == Qt.Key.Key_Up:
                    self._place_panel()
                    self._panel.move_selection(-1)
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    hit = self._panel.current_hit()
                    if hit and self._panel.isVisible():
                        self._emit_hit(hit)
                        return True
                if key == Qt.Key.Key_Escape:
                    self._panel.hide()
                    self.input.clearFocus()
                    return True
            elif et == QEvent.Type.FocusIn:
                if self.input.text().strip():
                    self._place_panel()
            elif et == QEvent.Type.Resize or et == QEvent.Type.Move:
                if self._panel.isVisible():
                    self._place_panel()
        # Clic fuera → cerrar panel
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and self._panel.isVisible()
            and isinstance(event, QMouseEvent)
        ):
            if not self._click_inside_search(event.globalPosition().toPoint()):
                self._panel.hide()
        return super().eventFilter(obj, event)

    def _install_app_filter(self) -> None:
        if self._app_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._app_filter_installed = True

    def _click_inside_search(self, global_pos: QPoint) -> bool:
        input_rect = QRect(
            self.input.mapToGlobal(QPoint(0, 0)), self.input.size()
        )
        if input_rect.contains(global_pos):
            return True
        if self._panel.isVisible():
            panel_rect = QRect(
                self._panel.mapToGlobal(QPoint(0, 0)), self._panel.size()
            )
            if panel_rect.contains(global_pos):
                return True
        return False

    def _on_text(self, _text: str) -> None:
        self._timer.start()

    def _run_search(self) -> None:
        q = self.input.text().strip()
        if len(q) < 2 and not q.isdigit():
            self._last = GlobalSearchResults(query=q)
            if q:
                self._panel.show_results(self._last)
                self._place_panel()
            else:
                self._panel.hide()
            return

        uid = (
            self._session.usuario_id
            if self._session.rol == Rol.USUARIO
            else None
        )
        incluir_usuarios = self._session.rol != Rol.USUARIO
        es_demo = None if (self._session.es_demo and self._session.es_admin()) else (
            self._session.es_demo
        )
        if self._session.rol == Rol.USUARIO:
            es_demo = self._session.es_demo

        results = self._ctx.busqueda.buscar(
            q,
            es_demo=es_demo,
            usuario_id=uid,
            incluir_usuarios=incluir_usuarios,
        )
        self._last = results
        self._panel.show_results(results)
        self._place_panel()
        if not self.input.hasFocus():
            self.input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _place_panel(self) -> None:
        if self._last is None and not self.input.text().strip():
            self._panel.show_results(GlobalSearchResults(query=""))
        width = max(self.input.width(), 480)
        # Espacio disponible bajo el input hasta el borde de la ventana.
        top = self.window()
        max_h = 420
        if top is not None:
            bottom = top.mapToGlobal(QPoint(0, top.height())).y()
            input_bottom = self.input.mapToGlobal(
                QPoint(0, self.input.height())
            ).y()
            max_h = max(160, min(420, bottom - input_bottom - 16))
        height = self._panel.preferred_height(max_h)
        pos = self.input.mapToGlobal(QPoint(0, self.input.height() + 6))
        self._panel.setFixedWidth(width)
        self._panel.setFixedHeight(height)
        self._panel.move(pos)
        self._panel.show()
        self._panel.raise_()

    def _emit_hit(self, hit: SearchHit) -> None:
        self._panel.hide()
        self.input.blockSignals(True)
        self.input.clear()
        self.input.blockSignals(False)
        self._last = None
        self.input.clearFocus()
        self.activated.emit(hit)
