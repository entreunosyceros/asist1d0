"""
Preferencias locales de la aplicación.

Se guardan en ``data/prefs.json``. Solo datos no sensibles
(por ejemplo, el email recordado en el login). Nunca se almacenan
contraseñas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

PREFS_PATH = DATA_DIR / "prefs.json"


def load_prefs() -> dict[str, Any]:
    """Lee el fichero de preferencias o un diccionario vacío si no existe."""
    if not PREFS_PATH.exists():
        return {}
    try:
        return json.loads(PREFS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_prefs(data: dict[str, Any]) -> None:
    """Fusiona ``data`` con las preferencias actuales y las persiste."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_prefs()
    existing.update(data)
    PREFS_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_remembered_login() -> tuple[bool, str]:
    """Devuelve ``(recordar, email)``. Si no hay que recordar, el email va vacío."""
    prefs = load_prefs()
    recordar = bool(prefs.get("remember_user", False))
    email = str(prefs.get("last_email", "")).strip() if recordar else ""
    return recordar, email


def set_remembered_login(remember: bool, email: str) -> None:
    """Activa o desactiva el recordatorio del último email de acceso."""
    if remember:
        save_prefs(
            {
                "remember_user": True,
                "last_email": email.strip().lower(),
            }
        )
    else:
        save_prefs(
            {
                "remember_user": False,
                "last_email": "",
            }
        )
