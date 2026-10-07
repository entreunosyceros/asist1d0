"""
Timeline unificada de una incidencia.

Combina historial, comentarios e intervenciones en una secuencia
cronológica para la ficha del ticket (sin sustituir el historial SQL).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.models.incidencia import Incidencia


class TimelineKind(str, Enum):
    CREAR = "crear"
    ASIGNAR = "asignar"
    ESTADO = "estado"
    PRIORIDAD = "prioridad"
    COMENTARIO = "comentario"
    INTERVENCION = "intervencion"
    ADJUNTO = "adjunto"
    REPUESTO = "repuesto"
    OTRO = "otro"


@dataclass(frozen=True)
class TimelineEvent:
    """Un punto de la línea de tiempo del ticket."""

    fecha: str
    kind: TimelineKind
    titulo: str
    cuerpo: str = ""
    actor: str = ""

    @property
    def hora(self) -> str:
        """HH:MM si hay timestamp reconocible (``YYYY-MM-DD HH:MM:SS``)."""
        f = (self.fecha or "").strip()
        if len(f) >= 16 and f[10] == " ":
            return f[11:16]
        if len(f) >= 5 and f[2] == ":":
            return f[:5]
        return f[-5:] if len(f) >= 5 else f

    @property
    def dia(self) -> str:
        f = (self.fecha or "").strip()
        if len(f) >= 10 and f[4] == "-":
            return f[:10]
        return ""


def _kind_from_historial(accion: str) -> TimelineKind:
    a = (accion or "").lower()
    if a.startswith("incidencia creada") or a.startswith("creada"):
        return TimelineKind.CREAR
    if "asignad" in a or "desasignad" in a:
        return TimelineKind.ASIGNAR
    if a.startswith("estado:"):
        return TimelineKind.ESTADO
    if a.startswith("prioridad:"):
        return TimelineKind.PRIORIDAD
    if a.startswith("adjunto"):
        return TimelineKind.ADJUNTO
    if a.startswith("repuesto"):
        return TimelineKind.REPUESTO
    if "reabiert" in a:
        return TimelineKind.ESTADO
    return TimelineKind.OTRO


def _historial_duplicado(accion: str) -> bool:
    """Entradas de historial que ya se muestran vía comentario/intervención."""
    a = accion or ""
    return a.startswith("Comentario añadido") or a.startswith("Intervención:")


def _formatear_historial(accion: str, actor: str) -> tuple[str, str]:
    """Título y cuerpo legibles a partir de una acción de historial."""
    a = (accion or "").strip()
    if a.startswith("Incidencia creada:"):
        resto = a.split(":", 1)[1].strip()
        quien = actor or "Usuario"
        return f"{quien} creó la incidencia", resto
    if a.startswith("Estado:"):
        return a.replace("Estado:", "Estado →").strip(), ""
    if a.startswith("Prioridad:"):
        return a.replace("Prioridad:", "Prioridad →").strip(), ""
    if a.startswith("Asignada al grupo"):
        return a.replace("Asignada al grupo", "Grupo →").strip(), ""
    if a.startswith("Asignada a"):
        return f"Técnico asignado: {a.replace('Asignada a', '').strip()}", ""
    if a == "Técnico desasignado":
        return "Técnico desasignado", ""
    if a == "Grupo desasignado":
        return "Grupo desasignado", ""
    if "grupo" in a.lower() and a.startswith("Asignada"):
        return a, ""
    if a.startswith("Adjunto añadido:"):
        return "Adjunto añadido", a.split(":", 1)[1].strip()
    if a.startswith("Adjunto eliminado:"):
        return "Adjunto eliminado", a.split(":", 1)[1].strip()
    if a.startswith("Repuesto usado:"):
        return "Repuesto utilizado", a.split(":", 1)[1].strip()
    if a == "Descripción actualizada":
        quien = actor or "Usuario"
        return f"{quien} actualizó la descripción", ""
    if a.startswith("Reabierta"):
        return "Incidencia reabierta", ""
    if actor:
        return f"{actor}: {a}", ""
    return a, ""


def construir_timeline(inc: Incidencia) -> list[TimelineEvent]:
    """Fusiona comentarios, intervenciones e historial ordenados por fecha."""
    eventos: list[TimelineEvent] = []

    for c in inc.comentarios:
        actor = c.usuario_nombre or "Usuario"
        eventos.append(
            TimelineEvent(
                fecha=c.fecha or "",
                kind=TimelineKind.COMENTARIO,
                titulo=actor,
                cuerpo=c.texto.strip(),
                actor=actor,
            )
        )

    for iv in inc.intervenciones:
        actor = iv.tecnico_nombre or "Técnico"
        eventos.append(
            TimelineEvent(
                fecha=iv.fecha or "",
                kind=TimelineKind.INTERVENCION,
                titulo=f"Intervención · {actor}",
                cuerpo=iv.descripcion.strip(),
                actor=actor,
            )
        )

    for h in inc.historial:
        if _historial_duplicado(h.accion):
            continue
        actor = h.usuario_nombre or ""
        kind = _kind_from_historial(h.accion)
        titulo, cuerpo = _formatear_historial(h.accion, actor)
        eventos.append(
            TimelineEvent(
                fecha=h.fecha or "",
                kind=kind,
                titulo=titulo,
                cuerpo=cuerpo,
                actor=actor,
            )
        )

    eventos.sort(key=lambda e: (e.fecha or "", e.kind.value, e.titulo))
    return eventos
