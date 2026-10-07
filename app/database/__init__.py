"""
Capa de base de datos SQLite.

Incluye conexión, schema, migraciones, seed demo y repositorios.
"""

from app.database.connection import DatabaseConnection, get_db

__all__ = ["DatabaseConnection", "get_db"]
