"""Esquemas Pydantic de la API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str
    es_demo: bool


class EquipoIn(BaseModel):
    numero_serie: str
    marca: str
    modelo: str
    sistema_operativo: str = ""


class EquipoOut(BaseModel):
    id: int
    numero_serie: str
    marca: str
    modelo: str
    sistema_operativo: str
    nombre_completo: str


class IncidenciaIn(BaseModel):
    equipo_id: int
    titulo: str
    descripcion: str = ""
    prioridad: str = "Media"
    categoria: str = "Otro"


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1)


class ComentarioOut(BaseModel):
    id: Optional[int]
    texto: str
    fecha: Optional[str]
    usuario_nombre: Optional[str]


class IncidenciaOut(BaseModel):
    id: int
    codigo: str
    titulo: str
    descripcion: str
    categoria: str
    estado: str
    estado_usuario: str
    prioridad: str
    equipo_nombre: Optional[str]
    tecnico_nombre: Optional[str]
    fecha_creacion: Optional[str]
    vencida: bool
    fecha_limite: Optional[str]
    comentarios: list[ComentarioOut] = []
