"""
Vista de la base de conocimiento.

Listado/búsqueda de artículos, lectura para todos los roles y
alta/edición para técnico y administrador.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.auth.service import SessionContext
from app.bootstrap import AppContext
from app.models.catalogo_categorias import etiqueta_categoria, listar_hojas
from app.models.enums import Rol
from app.models.knowledge import KnowledgeArticle
from app.ui.page_chrome import apply_page_margins, build_page_header, show_toast


class ArticuloDialog(QDialog):
    """Alta / edición de un artículo."""

    def __init__(
        self,
        article: KnowledgeArticle | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo artículo" if article is None else "Editar artículo")
        self.setMinimumSize(520, 480)
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.titulo = QLineEdit()
        self.resumen = QLineEdit()
        self.categoria = QComboBox()
        self.categoria.addItem("(sin categoría)", "")
        for hoja in listar_hojas():
            self.categoria.addItem(hoja.etiqueta_ruta(), hoja.codigo)
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("impresora, wifi, cola…")
        self.contenido = QTextEdit()

        if article:
            self.titulo.setText(article.titulo)
            self.resumen.setText(article.resumen)
            idx = self.categoria.findData(article.categoria_codigo)
            if idx >= 0:
                self.categoria.setCurrentIndex(idx)
            self.tags.setText(article.tags)
            self.contenido.setPlainText(article.contenido)

        layout.addRow("Título", self.titulo)
        layout.addRow("Resumen", self.resumen)
        layout.addRow("Categoría", self.categoria)
        layout.addRow("Etiquetas", self.tags)
        layout.addRow("Contenido", self.contenido)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def datos(self) -> dict:
        return {
            "titulo": self.titulo.text().strip(),
            "resumen": self.resumen.text().strip(),
            "categoria_codigo": self.categoria.currentData() or "",
            "tags": self.tags.text().strip(),
            "contenido": self.contenido.toPlainText().strip(),
        }


class ArticuloLecturaDialog(QDialog):
    """Lectura de un artículo (sugerencias / KB)."""

    def __init__(self, article: KnowledgeArticle, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(article.titulo)
        self.setMinimumSize(480, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        cat = etiqueta_categoria(article.categoria_codigo) if article.categoria_codigo else "—"
        meta = QLabel(f"Categoría: {cat}")
        meta.setObjectName("PageSubtitle")
        layout.addWidget(meta)

        if article.resumen:
            res = QLabel(article.resumen)
            res.setWordWrap(True)
            res.setObjectName("PageSubtitle")
            layout.addWidget(res)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(article.contenido)
        layout.addWidget(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)


class ConocimientoView(QWidget):
    """Página de base de conocimiento."""

    def __init__(self, ctx: AppContext, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._session = session
        self._status = None
        self._current_id: int | None = None
        self._build()
        self.refresh()

    def _puede_editar(self) -> bool:
        return self._session.es_tecnico() or self._session.es_admin()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        apply_page_margins(layout)
        actions = []
        if self._puede_editar():
            btn_new = QPushButton("+ Nuevo artículo")
            btn_new.clicked.connect(self._nuevo)
            btn_edit = QPushButton("Editar")
            btn_edit.setObjectName("SecondaryButton")
            btn_edit.clicked.connect(self._editar)
            btn_del = QPushButton("Eliminar")
            btn_del.setObjectName("DangerButton")
            btn_del.clicked.connect(self._eliminar)
            actions.extend([btn_new, btn_edit, btn_del])
        header, self._status = build_page_header(
            "Base de conocimiento",
            "Artículos de ayuda vinculados a categorías de incidencia",
            actions=actions or None,
        )
        layout.addLayout(header)

        filters = QHBoxLayout()
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Buscar en títulos y contenido…")
        self.busqueda.textChanged.connect(self.refresh)
        self.filtro_cat = QComboBox()
        self.filtro_cat.addItem("Todas las categorías", "")
        for hoja in listar_hojas():
            self.filtro_cat.addItem(hoja.etiqueta_ruta(), hoja.codigo)
        self.filtro_cat.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.busqueda, 2)
        filters.addWidget(self.filtro_cat, 1)
        layout.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.lista = QListWidget()
        self.lista.setObjectName("DetailList")
        self.lista.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.lista)

        detail = QWidget()
        dlay = QVBoxLayout(detail)
        dlay.setContentsMargins(8, 0, 0, 0)
        self.detalle_titulo = QLabel("Selecciona un artículo")
        self.detalle_titulo.setObjectName("DetailHeading")
        self.detalle_meta = QLabel("")
        self.detalle_meta.setObjectName("PageSubtitle")
        self.detalle_meta.setWordWrap(True)
        self.detalle_body = QTextEdit()
        self.detalle_body.setReadOnly(True)
        dlay.addWidget(self.detalle_titulo)
        dlay.addWidget(self.detalle_meta)
        dlay.addWidget(self.detalle_body, 1)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

    def seleccionar_articulo(self, article_id: int) -> None:
        """API pública: muestra un artículo (p. ej. desde búsqueda global)."""
        self.busqueda.blockSignals(True)
        self.busqueda.clear()
        self.busqueda.blockSignals(False)
        self.filtro_cat.blockSignals(True)
        self.filtro_cat.setCurrentIndex(0)
        self.filtro_cat.blockSignals(False)
        self._current_id = article_id
        self.refresh()
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == article_id:
                self.lista.setCurrentItem(item)
                return
        # Fuera del listado filtrado: cargar directo.
        art = self._ctx.conocimiento.obtener(article_id)
        if art:
            self._current_id = art.id
            self.detalle_titulo.setText(art.titulo)
            cat = (
                etiqueta_categoria(art.categoria_codigo)
                if art.categoria_codigo
                else "Sin categoría"
            )
            tags = f" · Tags: {art.tags}" if art.tags else ""
            self.detalle_meta.setText(f"{cat}{tags}")
            self.detalle_body.setPlainText(art.contenido)

    def refresh(self) -> None:
        keep = self._current_id
        arts = self._ctx.conocimiento.listar(
            texto=self.busqueda.text().strip() or None,
            categoria_codigo=self.filtro_cat.currentData() or None,
        )
        self.lista.clear()
        select_row = -1
        for i, a in enumerate(arts):
            item = QListWidgetItem(a.titulo)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            if a.resumen:
                item.setToolTip(a.resumen)
            self.lista.addItem(item)
            if keep and a.id == keep:
                select_row = i
        if select_row >= 0:
            self.lista.setCurrentRow(select_row)
        elif arts:
            self.lista.setCurrentRow(0)
        else:
            self._limpiar_detalle()
        show_toast(self._status, f"{len(arts)} artículo(s).")

    def _limpiar_detalle(self) -> None:
        self._current_id = None
        self.detalle_titulo.setText("Selecciona un artículo")
        self.detalle_meta.setText("")
        self.detalle_body.clear()

    def _on_select(self, current: QListWidgetItem | None, _prev=None) -> None:
        if current is None:
            self._limpiar_detalle()
            return
        aid = current.data(Qt.ItemDataRole.UserRole)
        art = self._ctx.conocimiento.obtener(aid)
        if not art:
            self._limpiar_detalle()
            return
        self._current_id = art.id
        self.detalle_titulo.setText(art.titulo)
        cat = (
            etiqueta_categoria(art.categoria_codigo)
            if art.categoria_codigo
            else "Sin categoría"
        )
        tags = f" · Tags: {art.tags}" if art.tags else ""
        self.detalle_meta.setText(f"{cat}{tags}")
        self.detalle_body.setPlainText(art.contenido)

    def _nuevo(self) -> None:
        if not self._puede_editar():
            return
        dlg = ArticuloDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        if not data["titulo"] or not data["contenido"]:
            QMessageBox.warning(self, "Artículo", "Título y contenido son obligatorios.")
            return
        try:
            art = self._ctx.conocimiento.crear(
                data["titulo"],
                data["contenido"],
                resumen=data["resumen"],
                categoria_codigo=data["categoria_codigo"],
                tags=data["tags"],
                es_demo=self._session.es_demo,
                actor_id=self._session.usuario_id,
            )
            self._current_id = art.id
            self.refresh()
            show_toast(self._status, "Artículo creado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _editar(self) -> None:
        if not self._puede_editar() or not self._current_id:
            return
        art = self._ctx.conocimiento.obtener(self._current_id)
        if not art:
            return
        dlg = ArticuloDialog(article=art, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.datos()
        if not data["titulo"] or not data["contenido"]:
            QMessageBox.warning(self, "Artículo", "Título y contenido son obligatorios.")
            return
        art.titulo = data["titulo"]
        art.resumen = data["resumen"]
        art.contenido = data["contenido"]
        art.categoria_codigo = data["categoria_codigo"]
        art._tags = data["tags"]
        try:
            self._ctx.conocimiento.actualizar(
                art, actor_id=self._session.usuario_id
            )
            self.refresh()
            show_toast(self._status, "Artículo actualizado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)

    def _eliminar(self) -> None:
        if not self._puede_editar() or not self._current_id:
            return
        art = self._ctx.conocimiento.obtener(self._current_id)
        if not art:
            return
        if (
            QMessageBox.question(self, "Eliminar", f"¿Eliminar «{art.titulo}»?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self._ctx.conocimiento.eliminar(
                self._current_id, actor_id=self._session.usuario_id
            )
            self._current_id = None
            self.refresh()
            show_toast(self._status, "Artículo eliminado.")
        except Exception as exc:
            show_toast(self._status, str(exc), error=True)


def mostrar_articulo(ctx: AppContext, article_id: int, parent=None) -> None:
    """Abre un diálogo de lectura; útil desde sugerencias al crear ticket."""
    art = ctx.conocimiento.obtener(article_id)
    if art:
        ArticuloLecturaDialog(art, parent=parent).exec()
