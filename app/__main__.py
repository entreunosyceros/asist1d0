"""
Punto de entrada del paquete: ``python -m app``.

Delega en ``app.main.main`` el arranque de la aplicación de escritorio.
"""

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
