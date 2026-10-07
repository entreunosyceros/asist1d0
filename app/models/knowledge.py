"""
Artículos de la base de conocimiento (help desk).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KnowledgeArticle:
    """Artículo de ayuda relacionado con una categoría del catálogo."""

    _titulo: str
    _contenido: str
    _resumen: str = ""
    _categoria_codigo: str = ""
    _tags: str = ""
    _activo: bool = True
    _es_demo: bool = False
    _id: Optional[int] = None
    _fecha_creacion: Optional[str] = None
    _fecha_actualizacion: Optional[str] = None

    def __post_init__(self) -> None:
        if not self._titulo.strip():
            raise ValueError("El título del artículo es obligatorio")
        if not self._contenido.strip():
            raise ValueError("El contenido del artículo es obligatorio")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def titulo(self) -> str:
        return self._titulo

    @titulo.setter
    def titulo(self, value: str) -> None:
        self._titulo = value.strip()

    @property
    def resumen(self) -> str:
        return self._resumen or self._titulo

    @resumen.setter
    def resumen(self, value: str) -> None:
        self._resumen = value or ""

    @property
    def contenido(self) -> str:
        return self._contenido

    @contenido.setter
    def contenido(self, value: str) -> None:
        self._contenido = value

    @property
    def categoria_codigo(self) -> str:
        return self._categoria_codigo

    @categoria_codigo.setter
    def categoria_codigo(self, value: str) -> None:
        self._categoria_codigo = value or ""

    @property
    def tags(self) -> str:
        return self._tags

    @property
    def lista_tags(self) -> list[str]:
        return [t.strip() for t in self._tags.split(",") if t.strip()]

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def es_demo(self) -> bool:
        return self._es_demo

    @property
    def fecha_creacion(self) -> Optional[str]:
        return self._fecha_creacion

    @property
    def fecha_actualizacion(self) -> Optional[str]:
        return self._fecha_actualizacion

    def __str__(self) -> str:
        return self._titulo


def article_desde_fila(row) -> KnowledgeArticle:
    data = dict(row)
    return KnowledgeArticle(
        _id=data["id"],
        _titulo=data["titulo"],
        _resumen=data.get("resumen") or "",
        _contenido=data["contenido"],
        _categoria_codigo=data.get("categoria_codigo") or "",
        _tags=data.get("tags") or "",
        _activo=bool(data.get("activo", 1)),
        _es_demo=bool(data.get("es_demo", 0)),
        _fecha_creacion=data.get("fecha_creacion"),
        _fecha_actualizacion=data.get("fecha_actualizacion"),
    )
