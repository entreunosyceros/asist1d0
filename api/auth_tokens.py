"""Emisión y validación de tokens JWT para la API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import JWT_HOURS, JWT_SECRET


def crear_token(usuario_id: int, email: str, rol: str, es_demo: bool) -> str:
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "rol": rol,
        "es_demo": es_demo,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decodificar_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
