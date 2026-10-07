"""
Diálogo de ayuda contextual según el rol del usuario.

Genera HTML con lo que puede hacer cada rol en cada módulo y lo muestra
en una ventana con ``QTextBrowser``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.auth.service import SessionContext
from app.config import APP_NAME
from app.models.enums import Rol
from app.ui.resources import apply_window_icon


def _ayuda_usuario() -> str:
    """Texto de ayuda para el rol Usuario."""
    return """
<h2>Guía para Usuario</h2>
<p>Como <b>Usuario</b> gestionas tus propios equipos e incidencias.</p>
<h3>Dashboard</h3>
<ul>
  <li>Consulta el resumen de tus incidencias pendientes, abiertas y de alta prioridad.</li>
  <li>Haz clic en una incidencia reciente para abrirla.</li>
</ul>
<h3>Incidencias</h3>
<ul>
  <li>Crea nuevas incidencias asociadas a tus equipos.</li>
  <li>Filtra por estado o prioridad y busca por texto.</li>
  <li>Consulta el detalle, intervenciones e historial (sin modificar estado ni asignaciones).</li>
  <li><b>Comentarios</b>: escribe en el hilo del ticket para aportar información al soporte.</li>
</ul>
<h3>Sesión y bandeja</h3>
<ul>
  <li><b>Cambiar mi contraseña</b> desde el menú Sesión o el menú de la bandeja del sistema.</li>
  <li>La bandeja avisa si cambia el estado de tu incidencia o si hay un comentario nuevo (cuando la app sigue en segundo plano).</li>
</ul>
<h3>Equipos</h3>
<ul>
  <li>Registra tus equipos (marca, modelo, nº de serie, sistema operativo).</li>
  <li>Revisa el árbol de incidencias de cada equipo.</li>
</ul>
<p><i>No tienes acceso a Usuarios, Inventario, Informes ni Panel técnico.</i></p>
"""


def _ayuda_tecnico() -> str:
    """Texto de ayuda para el rol Técnico."""
    return """
<h2>Guía para Técnico</h2>
<p>Como <b>Técnico</b> resuelves incidencias e intervienes en el ciclo de soporte.</p>
<h3>Dashboard</h3>
<ul>
  <li>KPIs globales del ámbito (demo o real).</li>
  <li>Últimas intervenciones y avisos de stock bajo.</li>
  <li>Clic en una intervención para ir a su incidencia.</li>
</ul>
<h3>Incidencias</h3>
<ul>
  <li>Busca y filtra (estado, prioridad, «Mis asignadas», «Sin asignar», por técnico).</li>
  <li>Cambia estado y prioridad; asigna o desasigna técnicos.</li>
  <li><b>Comentarios</b> en el hilo del ticket (usuario y técnico).</li>
  <li>Añade intervenciones y usa repuestos del inventario.</li>
  <li>Consulta historial y componentes consumidos.</li>
</ul>
<h3>Sesión y bandeja</h3>
<ul>
  <li><b>Cambiar mi contraseña</b> desde Sesión o la bandeja.</li>
  <li>Recibes aviso en bandeja al asignarte una incidencia, al cambiar su estado o al comentar el usuario (si no eres tú quien actúa).</li>
</ul>
<h3>Equipos</h3>
<ul>
  <li>Alta, edición y baja de equipos del ámbito.</li>
</ul>
<h3>Usuarios</h3>
<ul>
  <li>Consulta de usuarios en solo lectura.</li>
</ul>
<h3>Inventario</h3>
<ul>
  <li>Gestiona stock de componentes/repuestos.</li>
</ul>
<h3>Informes</h3>
<ul>
  <li>Estadísticas por estado, prioridad y técnico; exporta CSV.</li>
</ul>
<h3>Panel técnico</h3>
<ul>
  <li>Consultas predefinidas, historial global y logs de la aplicación.</li>
</ul>
"""


def _ayuda_admin() -> str:
    """Texto de ayuda específico del Administrador (se combina con el de técnico)."""
    return """
<h2>Guía para Administrador</h2>
<p>Como <b>Administrador</b> tienes el control completo del sistema.</p>
<h3>Todo lo del técnico, y además:</h3>
<ul>
  <li><b>Usuarios</b>: crear, editar y eliminar cuentas con roles Usuario, Técnico o Administrador.</li>
  <li><b>Cambiar mi contraseña</b>: desde Sesión, la bandeja o Usuarios → «Mi contraseña» (cualquier rol; pide la actual y la nueva).</li>
  <li>Las cuentas <b>demo</b> no ven los datos de usuarios <b>reales</b> (y viceversa).</li>
  <li>Si entras con admin demo, puedes crear usuarios reales; sus incidencias/equipos no serán visibles para demos.</li>
</ul>
<h3>Buenas prácticas</h3>
<ul>
  <li>Crea un administrador real para el día a día y deja las cuentas demo solo para pruebas.</li>
  <li>Revisa Informes y Panel técnico para el seguimiento del servicio.</li>
  <li>Mantén el inventario al día para poder asociar repuestos a las reparaciones.</li>
</ul>
"""


def texto_ayuda_para(session: SessionContext) -> str:
    """Compone el HTML completo de ayuda para la sesión actual."""
    intro = f"""
    <h1>Ayuda de {APP_NAME}</h1>
    <p>Sesión actual: <b>{session.usuario.nombre}</b>
    ({session.rol.etiqueta}
    {"· cuenta demo" if session.es_demo else "· cuenta real"})</p>
    <hr/>
    """
    if session.rol == Rol.USUARIO:
        cuerpo = _ayuda_usuario()
    elif session.rol == Rol.TECNICO:
        cuerpo = _ayuda_tecnico()
    else:
        cuerpo = _ayuda_admin() + "<hr/>" + _ayuda_tecnico()
    comun = """
    <hr/>
    <h3>Menú superior</h3>
    <ul>
      <li><b>Sesión</b>: cambiar contraseña (admin) y cerrar la sesión actual.</li>
      <li><b>Ir</b>: navega a las secciones disponibles para tu rol.</li>
      <li><b>Ayuda</b>: esta guía y la ventana Acerca de.</li>
    </ul>
    """
    return intro + cuerpo + comun


class HelpDialog(QDialog):
    """Ventana «Guía de uso» adaptada al rol de la sesión."""

    def __init__(self, session: SessionContext, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ayuda — {APP_NAME}")
        self.resize(560, 640)
        apply_window_icon(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        titulo = QLabel(f"Qué puedes hacer como {session.rol.etiqueta}")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(texto_ayuda_para(session))
        layout.addWidget(browser)

        btn = QPushButton("Cerrar")
        btn.setObjectName("SecondaryButton")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
