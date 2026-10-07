"""
Paquete de autenticación.

Expone el servicio de login/sesión y las utilidades de hashing PBKDF2.
"""

from app.auth.password import hash_password, verify_password
from app.auth.service import AuthService, SessionContext

__all__ = ["AuthService", "SessionContext", "hash_password", "verify_password"]
