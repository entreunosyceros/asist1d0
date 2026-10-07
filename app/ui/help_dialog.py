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
<h3>Búsqueda global</h3>
<ul>
  <li>Cuadro <b>🔎 Buscar…</b> arriba (o <b>Ctrl+K</b>): busca a la vez incidencias, equipos,
      comentarios y artículos (p. ej. <code>INC-0042</code>, <code>PC-023</code>, «impresora», «SSD»).</li>
  <li>Pulsa Enter o haz clic en un resultado para abrir la ficha correspondiente.</li>
</ul>
<h3>Dashboard</h3>
<ul>
  <li>Consulta el resumen de tus incidencias pendientes, abiertas y de alta prioridad.</li>
  <li>Haz clic en una incidencia reciente para abrirla.</li>
  <li>Si no tienes equipo o tickets, verás botones para registrar equipo o abrir tu primera incidencia.</li>
</ul>
<h3>Incidencias</h3>
<ul>
  <li>Crea incidencias eligiendo una <b>categoría</b> del catálogo (Hardware/Software/Red…):
      plantilla, prioridad sugerida, SLA, grupo responsable y campos específicos.</li>
  <li>Filtra por estado, prioridad o categoría y busca por texto.</li>
  <li>Ficha de <b>seguimiento</b>: estado claro, SLA (plazo) y badge <b>Vencida</b> si se supera.</li>
  <li><b>Confirmar resolución</b> cuando el ticket está Pendiente o En reparación; <b>Reabrir</b> si estaba Cerrada.</li>
  <li><b>Adjuntos</b>, editar descripción, <b>comentarios</b> y <b>timeline</b> de actividad en tus tickets.</li>
  <li>Al crear un ticket verás <b>posibles soluciones</b> de la base de conocimiento (doble clic para leer).</li>
  <li>También puedes usar el <b>portal web</b> (misma cuenta): menú <b>Ir → Abrir portal web…</b> o desde la bandeja.</li>
</ul>
<h3>Base de conocimiento</h3>
<ul>
  <li>Consulta artículos de autoayuda filtrados por categoría o texto.</li>
</ul>
<h3>Sesión y bandeja</h3>
<ul>
  <li><b>Cambiar mi contraseña</b> desde el menú Sesión o el menú de la bandeja del sistema.</li>
  <li>La bandeja avisa si cambia el estado de tu incidencia o si hay un comentario nuevo (cuando la app sigue en segundo plano).</li>
</ul>
<h3>Equipos</h3>
<ul>
  <li>Registra y <b>edita</b> tus equipos (marca, modelo, nº de serie, SO, CPU, RAM, disco, GPU).</li>
  <li>En el árbol verás componentes, software, reparaciones e incidencias de cada equipo.</li>
  <li>Doble clic en un ticket del árbol para abrirlo en Incidencias.</li>
</ul>
<p><i>No tienes acceso a Usuarios, Inventario, Informes, Auditoría ni Panel técnico.
   Sí puedes usar la Base de conocimiento.</i></p>
"""


def _ayuda_tecnico() -> str:
    """Texto de ayuda para el rol Técnico."""
    return """
<h2>Guía para Técnico</h2>
<p>Como <b>Técnico</b> resuelves incidencias e intervienes en el ciclo de soporte.</p>
<h3>Búsqueda global</h3>
<ul>
  <li>Cuadro <b>🔎 Buscar…</b> (o <b>Ctrl+K</b> / menú Ir → Buscar): incidencias, equipos,
      usuarios, comentarios y artículos de conocimiento en una sola consulta.</li>
  <li>Acepta códigos (<code>INC-0042</code>, <code>PC-023</code>), nombres, síntomas o piezas («SSD»).</li>
</ul>
<h3>Dashboard</h3>
<ul>
  <li>Paneles <b>INCIDENCIAS</b> (abiertas, en proceso, vencidas, resueltas),
      <b>SLA</b> (cumplimiento % y tiempo medio) y carga por <b>TÉCNICOS</b>.</li>
  <li>Gráficas nativas: incidencias por día, categoría, prioridad,
      tiempo medio de resolución e incidencias por técnico.</li>
  <li>Últimas intervenciones y avisos de stock bajo.</li>
  <li>Clic en una intervención para ir a su incidencia.</li>
</ul>
<h3>Incidencias</h3>
<ul>
  <li>Busca y filtra (estado, prioridad, categoría, «Mis asignadas», «Sin asignar», por técnico).</li>
  <li>Los tickets <b>Vencidos</b> (SLA) se resaltan en el listado.</li>
  <li>Pon el ticket en <b>Pendiente</b> para pedir confirmación al usuario.</li>
  <li>Cambia estado y prioridad; asigna a un <b>grupo</b> (cola) y luego a un técnico del grupo.</li>
  <li>La ficha muestra una <b>timeline</b> unificada (creación, asignación, estados, comentarios, intervenciones, repuestos).</li>
  <li>Puedes añadir comentarios; técnicos también intervenciones y repuestos.</li>
  <li><b>Base de conocimiento</b>: consulta y edita artículos ligados a categorías; se sugieren al crear tickets.</li>
</ul>
<h3>Sesión y bandeja</h3>
<ul>
  <li><b>Cambiar mi contraseña</b> desde Sesión o la bandeja.</li>
  <li>Recibes aviso en bandeja al asignarte una incidencia, al cambiar su estado o al comentar el usuario (si no eres tú quien actúa).</li>
</ul>
<h3>Equipos</h3>
<ul>
  <li>Ficha con especificaciones (CPU/RAM/SSD/GPU) y árbol de relaciones:
      componentes del inventario, software instalado, historial de reparaciones e incidencias.</li>
  <li>Puedes asociar piezas del inventario, registrar software y reparaciones desde la ficha.</li>
  <li>Al usar un repuesto en un ticket, también se registra en el equipo y en su historial de reparaciones.</li>
</ul>
<h3>Usuarios</h3>
<ul>
  <li>Consulta de usuarios en solo lectura.</li>
</ul>
<h3>Inventario</h3>
<ul>
  <li>Añade piezas con «+ Nuevo repuesto», edítalas o suma stock con «+ Stock».</li>
  <li>Las piezas con stock &gt; 0 aparecen al usar un repuesto en una incidencia.</li>
</ul>
<h3>Informes</h3>
<ul>
  <li>Estadísticas por estado, prioridad y técnico; exporta CSV.</li>
</ul>
<h3>Auditoría</h3>
<ul>
  <li>Trazabilidad global: quién creó/editó usuarios, incidencias, equipos o stock.</li>
  <li>Filtra por usuario, acción, entidad, ID, fechas o texto en el detalle.</li>
  <li>Solo lectura. El <b>historial del ticket</b> sigue en la ficha de cada incidencia
      (línea de tiempo del caso); Auditoría es la vista transversal para compliance.</li>
</ul>
<h3>Panel técnico</h3>
<ul>
  <li>Consultas predefinidas, historial global de tickets y logs de la aplicación.</li>
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
  <li><b>Inventario</b>: + Nuevo repuesto, editar, + Stock o eliminar piezas disponibles para las reparaciones.</li>
  <li>Desde una incidencia → «Usar repuesto» también puedes <b>añadir una pieza nueva</b> al inventario.</li>
  <li><b>Cambiar mi contraseña</b>: desde Sesión, la bandeja o Usuarios → «Mi contraseña» (cualquier rol; pide la actual y la nueva).</li>
  <li>Las cuentas <b>demo</b> no ven los datos de usuarios <b>reales</b> (y viceversa).</li>
  <li>Si entras con admin demo, puedes crear usuarios reales; sus incidencias/equipos no serán visibles para demos.</li>
</ul>
<h3>Buenas prácticas</h3>
<ul>
  <li>Crea un administrador real para el día a día y deja las cuentas demo solo para pruebas.</li>
  <li>Revisa Informes, Auditoría y Panel técnico para el seguimiento del servicio.</li>
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
      <li><b>Ir</b>: secciones, búsqueda global y <b>Abrir portal web…</b>.</li>
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
