"""
Modelo de componente / repuesto de inventario.

Controla stock, precio y el flag ``es_demo`` para aislar el inventario
de demostración del real.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Componente:
    """Pieza o material consumible asociado a reparaciones."""

    _nombre: str
    _stock: int = 0
    _precio: float = 0.0
    _descripcion: str = ""
    _es_demo: bool = False
    _id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self._nombre.strip():
            raise ValueError("El nombre del componente es obligatorio")
        if self._stock < 0:
            raise ValueError("El stock no puede ser negativo")
        if self._precio < 0:
            raise ValueError("El precio no puede ser negativo")

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, value: Optional[int]) -> None:
        self._id = value

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, value: str) -> None:
        if not value.strip():
            raise ValueError("El nombre del componente es obligatorio")
        self._nombre = value.strip()

    @property
    def stock(self) -> int:
        return self._stock

    @stock.setter
    def stock(self, value: int) -> None:
        if value < 0:
            raise ValueError("El stock no puede ser negativo")
        self._stock = value

    @property
    def precio(self) -> float:
        return self._precio

    @precio.setter
    def precio(self, value: float) -> None:
        if value < 0:
            raise ValueError("El precio no puede ser negativo")
        self._precio = float(value)

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @descripcion.setter
    def descripcion(self, value: str) -> None:
        self._descripcion = value or ""

    @property
    def es_demo(self) -> bool:
        return self._es_demo

    @es_demo.setter
    def es_demo(self, value: bool) -> None:
        self._es_demo = bool(value)

    def stock_bajo(self, umbral: int = 5) -> bool:
        return self._stock <= umbral

    def __str__(self) -> str:
        return f"{self._nombre} (stock: {self._stock})"


def componente_desde_fila(row) -> Componente:
    data = dict(row)
    return Componente(
        _id=data["id"],
        _nombre=data["nombre"],
        _stock=data["stock"],
        _precio=data["precio"],
        _descripcion=data.get("descripcion") or "",
        _es_demo=bool(data.get("es_demo", 0)),
    )
