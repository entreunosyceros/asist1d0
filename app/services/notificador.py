"""
Notificadores polimórficos de eventos de incidencias.

La interfaz ``Notificador`` permite combinar implementaciones
(consola, email SMTP / outbox, compuesto) sin acoplar la lógica de negocio.
"""

from __future__ import annotations

import json
import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from app.config import LOGS_DIR, SMTP_CONFIG_PATH
from app.models.incidencia import Incidencia

logger = logging.getLogger("asist1d0.notificaciones")


class Notificador(ABC):
    """Contrato común para avisar de cambios en una incidencia."""

    @abstractmethod
    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        raise NotImplementedError


class NotificadorConsola(Notificador):
    """Escribe el aviso por stdout y en el logger de la aplicación."""

    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        texto = f"[Asist{{1d0}}] {incidencia.codigo}: {mensaje}"
        print(texto)
        logger.info(texto)


def cargar_smtp_config(ruta: Path | None = None) -> dict[str, Any] | None:
    """Lee ``data/smtp.json`` si existe y tiene host+from válidos."""
    path = ruta or SMTP_CONFIG_PATH
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo leer SMTP config: %s", exc)
        return None
    if not data.get("host") or not data.get("from"):
        return None
    return data


class NotificadorEmail(Notificador):
    """
    Envía email real por SMTP si hay config; si no, escribe en outbox local.

    Destinatario: ``incidencia.usuario_email`` (o nombre como fallback en outbox).
    """

    def __init__(
        self,
        bandeja: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        self._bandeja = bandeja or (LOGS_DIR / "email_outbox.log")
        self._bandeja.parent.mkdir(parents=True, exist_ok=True)
        self._config_path = config_path or SMTP_CONFIG_PATH

    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        destinatario = incidencia.usuario_email or ""
        asunto = f"{incidencia.codigo} - {incidencia.titulo}"
        cuerpo = (
            f"Incidencia: {incidencia.codigo}\n"
            f"Título: {incidencia.titulo}\n"
            f"Estado: {incidencia.estado.value}\n\n"
            f"{mensaje}\n"
        )
        cfg = cargar_smtp_config(self._config_path)
        if cfg and destinatario and "@" in destinatario:
            try:
                self._enviar_smtp(cfg, destinatario, asunto, cuerpo)
                logger.info("Email SMTP enviado a %s (%s)", destinatario, asunto)
                return
            except Exception as exc:
                logger.warning("Fallo SMTP (%s); se usa outbox local", exc)
        self._escribir_outbox(destinatario or incidencia.usuario_nombre or "usuario", asunto, cuerpo)

    def _enviar_smtp(
        self,
        cfg: dict[str, Any],
        to_addr: str,
        subject: str,
        body: str,
    ) -> None:
        msg = EmailMessage()
        msg["From"] = cfg["from"]
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        host = str(cfg["host"])
        port = int(cfg.get("port") or 587)
        use_tls = bool(cfg.get("use_tls", True))
        user = cfg.get("user") or ""
        password = cfg.get("password") or ""

        if use_tls:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls()
                if user:
                    smtp.login(str(user), str(password))
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                if user:
                    smtp.login(str(user), str(password))
                smtp.send_message(msg)

    def _escribir_outbox(self, destinatario: str, subject: str, body: str) -> None:
        linea = f"TO: {destinatario} | SUBJECT: {subject} | BODY: {body.replace(chr(10), ' ')}\n"
        with self._bandeja.open("a", encoding="utf-8") as f:
            f.write(linea)
        logger.info("Email simulado (outbox): %s", linea.strip()[:200])


class NotificadorCompuesto(Notificador):
    """Delega la misma notificación a varios notificadores en cadena."""

    def __init__(self, *notificadores: Notificador) -> None:
        self._notificadores = list(notificadores)

    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        for n in self._notificadores:
            n.notificar(incidencia, mensaje)
