"""
Notificadores polimórficos de eventos de incidencias.

La interfaz ``Notificador`` permite combinar implementaciones
(consola, email simulado, compuesto) sin acoplar la lógica de negocio.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import LOGS_DIR
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


class NotificadorEmail(Notificador):
    """Simula envío de email escribiendo a un archivo de bandeja saliente."""

    def __init__(self, bandeja: Path | None = None) -> None:
        self._bandeja = bandeja or (LOGS_DIR / "email_outbox.log")
        self._bandeja.parent.mkdir(parents=True, exist_ok=True)

    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        destinatario = incidencia.usuario_nombre or "usuario"
        linea = (
            f"TO: {destinatario} | SUBJECT: {incidencia.codigo} - {incidencia.titulo} "
            f"| BODY: {mensaje}\n"
        )
        with self._bandeja.open("a", encoding="utf-8") as f:
            f.write(linea)
        logger.info("Email simulado: %s", linea.strip())


class NotificadorCompuesto(Notificador):
    """Delega la misma notificación a varios notificadores en cadena."""

    def __init__(self, *notificadores: Notificador) -> None:
        self._notificadores = list(notificadores)

    def notificar(self, incidencia: Incidencia, mensaje: str) -> None:
        for n in self._notificadores:
            n.notificar(incidencia, mensaje)
