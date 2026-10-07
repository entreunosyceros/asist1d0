"""
Artículos iniciales de la base de conocimiento.

Idempotente: solo inserta si no existe un artículo con el mismo título.
"""

from __future__ import annotations

from app.database.connection import DatabaseConnection

# (titulo, resumen, categoria_codigo, tags, contenido)
_ARTICULOS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "¿Cómo conectar una impresora WiFi?",
        "Pasos para añadir una impresora en red inalámbrica",
        "Hardware/Impresora",
        "impresora,wifi,red",
        """1. Comprueba que la impresora está encendida y unida a la misma Wi‑Fi que tu PC.
2. En Windows: Configuración → Bluetooth y dispositivos → Impresoras y escáneres → Añadir dispositivo.
3. En Ubuntu: Configuración → Impresoras → Añadir → Impresora de red.
4. Si no aparece, anota la IP desde el panel de la impresora e instálala por dirección IP.
5. Imprime una página de prueba.""",
    ),
    (
        "La impresora aparece desconectada",
        "Comprobar conexión, cola y estado del dispositivo",
        "Hardware/Impresora",
        "impresora,desconectada,red",
        """1. Verifica cable USB o Wi‑Fi y que la impresora no esté en ahorro profundo.
2. Reinicia impresora y equipo.
3. Abre la cola de impresión y elimina trabajos atascados.
4. En Windows, marca la impresora como predeterminada y desactiva «Usar impresora sin conexión».
5. Reinstala el driver del fabricante si sigue offline.""",
    ),
    (
        "Cómo limpiar la cola de impresión",
        "Vaciar trabajos atascados en el spooler",
        "Hardware/Impresora",
        "impresora,cola,spooler",
        """Windows:
1. Abre services.msc → Detén «Cola de impresión» (Spooler).
2. Borra el contenido de C:\\Windows\\System32\\spool\\PRINTERS.
3. Inicia de nuevo el servicio Spooler.
4. Reintenta la impresión.

Ubuntu:
1. `cancel -a` o abre la cola en Configuración → Impresoras.
2. Reinicia cups: `sudo systemctl restart cups`.""",
    ),
    (
        "Reiniciar servicio de impresión",
        "Reinicio rápido del spooler / CUPS",
        "Hardware/Impresora",
        "impresora,servicio,spooler",
        """Windows: services.msc → Cola de impresión → Reiniciar.
Ubuntu: `sudo systemctl restart cups`.
Tras reiniciar, comprueba que la impresora vuelve a «Lista».""",
    ),
    (
        "¿Cómo restablecer la contraseña?",
        "Reset de cuenta local, correo o dominio",
        "Cuenta",
        "password,cuenta,acceso",
        """1. Si es tu cuenta de Asist{1d0}: menú Sesión → Cambiar mi contraseña.
2. Correo corporativo: usa «¿Olvidaste tu contraseña?» en el portal web o contacta Identidad.
3. Cuenta de dominio Windows: el administrador puede forzar el cambio en Active Directory.
4. Nunca compartas la contraseña temporal por canales no seguros.""",
    ),
    (
        "Windows no detecta la tarjeta de red",
        "Diagnóstico de adaptador Wi‑Fi o Ethernet",
        "Red/Ethernet",
        "windows,red,adaptador,driver",
        """1. Administrador de dispositivos → Adaptadores de red: ¿aparece con signo de aviso?
2. Actualiza o reinstala el driver del fabricante.
3. Desactiva/activa el adaptador; ejecuta el solucionador de problemas de red.
4. Comprueba que no esté deshabilitado en la BIOS.
5. Prueba otro puerto/cable o un dongle USB Wi‑Fi para aislar el fallo.""",
    ),
    (
        "Cómo configurar una VPN",
        "Conexión VPN corporativa paso a paso",
        "Red/VPN",
        "vpn,remoto,acceso",
        """1. Instala el cliente oficial (GlobalProtect, OpenVPN, WireGuard…).
2. Introduce el portal/servidor que te indicó Sistemas.
3. Autentícate con tu usuario corporativo y, si aplica, 2FA.
4. Comprueba que puedes alcanzar recursos internos (intranet, impresoras de sede).
5. Si falla: revisa hora del sistema, certificado y que no haya otro VPN activo.""",
    ),
    (
        "Problemas frecuentes de Wi‑Fi",
        "SSID, IP y alcance de la señal",
        "Red/WiFi",
        "wifi,ssid,conectividad",
        """1. Olvida la red y vuelve a conectar con la clave correcta.
2. Comprueba que obtienes IP (no 169.254.x.x).
3. Acércate al AP; evita microondas y obstáculos metálicos.
4. Prueba otra banda (2,4 / 5 GHz) si el router lo permite.
5. Si afecta a varios usuarios de la zona, abre incidencia a Redes.""",
    ),
    (
        "La aplicación no abre o se cierra sola",
        "Reparar instalación y limpiar caché",
        "Software/Aplicaciones",
        "software,aplicacion,crash",
        """1. Cierra procesos residuales en el administrador de tareas.
2. Repara o reinstala la aplicación desde el instalador corporativo.
3. Borra caché/perfil local si el fabricante lo documenta.
4. Comprueba espacio en disco y permisos de la carpeta de instalación.
5. Anota el mensaje de error exacto antes de abrir el ticket.""",
    ),
    (
        "Activar o renovar una licencia de software",
        "Alta y renovación de licencias",
        "Software/Licencias",
        "licencia,activacion,software",
        """1. Identifica producto y versión.
2. Solicita la licencia a Soporte Software con el justificante.
3. Introduce la clave o inicia sesión en el portal del fabricante.
4. Si aparece error de activación, desconecta VPN temporalmente y reintenta.
5. Conserva el ID de pedido para auditorías.""",
    ),
)


def ensure_knowledge_articles(db: DatabaseConnection) -> None:
    """Inserta artículos canónicos si aún no existen (por título)."""
    for titulo, resumen, categoria, tags, contenido in _ARTICULOS:
        row = db.fetchone(
            "SELECT id FROM knowledge_articles WHERE titulo = ?", (titulo,)
        )
        if row:
            continue
        db.execute(
            """
            INSERT INTO knowledge_articles
                (titulo, resumen, contenido, categoria_codigo, tags, activo, es_demo)
            VALUES (?, ?, ?, ?, ?, 1, 1)
            """,
            (titulo, resumen, contenido, categoria, tags),
        )
