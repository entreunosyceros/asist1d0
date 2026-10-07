"""
Arranque del portal web desde la aplicación de escritorio.

Si el puerto de la API no responde, lanza ``python -m api`` en segundo
plano y abre el navegador en ``/portal/``.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import sys
import time
import webbrowser
from typing import Optional

from app.config import API_HOST, API_PORT, BASE_DIR

logger = logging.getLogger("asist1d0.portal")

_process: Optional[subprocess.Popen] = None


def portal_url() -> str:
    return f"http://{API_HOST}:{API_PORT}/portal/"


def is_portal_up(timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((API_HOST, API_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_portal_running(wait_seconds: float = 12.0) -> None:
    """Arranca la API si no está escuchando; espera hasta ``wait_seconds``."""
    global _process
    if is_portal_up():
        return

    if _process is not None and _process.poll() is None:
        # Ya lo lanzamos; seguir esperando.
        pass
    else:
        logger.info("Arrancando portal en %s:%s…", API_HOST, API_PORT)
        _process = subprocess.Popen(
            [sys.executable, "-m", "api"],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_portal_up():
            return
        if _process is not None and _process.poll() is not None:
            raise RuntimeError(
                "El portal no pudo iniciarse. Comprueba las dependencias "
                "(fastapi, uvicorn) con: pip install -r requirements.txt"
            )
        time.sleep(0.25)

    raise RuntimeError(
        f"Tiempo de espera agotado al arrancar el portal en {portal_url()}"
    )


def open_portal() -> str:
    """Asegura el servidor y abre el navegador. Devuelve la URL."""
    ensure_portal_running()
    url = portal_url()
    webbrowser.open(url)
    return url


def stop_portal_if_owned() -> None:
    """Detiene el proceso hijo si lo arrancamos nosotros."""
    global _process
    if _process is None:
        return
    if _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _process.kill()
    _process = None
