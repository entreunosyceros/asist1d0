"""
Hashing de contraseñas con PBKDF2 (solo librería estándar).

Formato almacenado: ``pbkdf2_sha256$iteraciones$sal$digest``.
La verificación usa comparación en tiempo constante (``hmac.compare_digest``).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# Parámetros del algoritmo (suficientes para un escritorio local).
_ITERATIONS = 120_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2 con sal aleatoria a partir de la contraseña en claro."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba si ``password`` coincide con el hash almacenado."""
    try:
        algo, iterations, salt, digest = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(check, digest)
    except (ValueError, TypeError):
        return False
