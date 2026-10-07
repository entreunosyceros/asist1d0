#!/usr/bin/env python3
"""Lanzador de Asist{1d0}: crea el venv, instala dependencias e inicia la app."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import venv
from pathlib import Path

# Configuración principal del lanzador.
DIRECTORIO_ENTORNO_VIRTUAL = ".venv"
ARCHIVO_REQUISITOS = "requirements.txt"
MODULO_PRINCIPAL = "app"


def existe_entorno_virtual() -> bool:
    """Comprueba si el entorno virtual existe y es válido."""
    if not os.path.exists(DIRECTORIO_ENTORNO_VIRTUAL) or not os.path.isdir(
        DIRECTORIO_ENTORNO_VIRTUAL
    ):
        return False
    return os.path.exists(obtener_ejecutable_python())


def crear_entorno_virtual() -> None:
    """Crea el entorno virtual y actualiza herramientas base."""
    if os.path.exists(DIRECTORIO_ENTORNO_VIRTUAL):
        print("Eliminando entorno virtual corrupto...")
        import shutil

        shutil.rmtree(DIRECTORIO_ENTORNO_VIRTUAL)

    print("Creando el entorno virtual...")
    venv.create(DIRECTORIO_ENTORNO_VIRTUAL, with_pip=True)

    print("Actualizando herramientas base del entorno...")
    try:
        ejecutar_comando_pip(
            "install", "--upgrade", "pip", "setuptools", "wheel", capture_output=True
        )
    except subprocess.CalledProcessError as error_subproceso:
        print("[!] No se pudieron actualizar pip/setuptools/wheel.")
        print("    Se continuará con las versiones incluidas en el entorno virtual.")
        detalles = formatear_error_subproceso(error_subproceso)
        if detalles:
            print(detalles)
    print(f" [OK] Entorno virtual creado en: {DIRECTORIO_ENTORNO_VIRTUAL}")


def obtener_ejecutable_python() -> str:
    """Obtiene la ruta al ejecutable Python del entorno virtual."""
    if platform.system().lower() == "windows":
        return os.path.join(DIRECTORIO_ENTORNO_VIRTUAL, "Scripts", "python.exe")
    return os.path.join(DIRECTORIO_ENTORNO_VIRTUAL, "bin", "python")


def ejecutar_comando_pip(*argumentos, capture_output: bool = False):
    """Ejecuta pip usando `python -m pip` para evitar problemas con pip.exe."""
    ejecutable_python = obtener_ejecutable_python()
    return subprocess.run(
        [ejecutable_python, "-m", "pip", *argumentos],
        check=True,
        capture_output=capture_output,
        text=capture_output,
    )


def formatear_error_subproceso(error_subproceso) -> str:
    """Devuelve una versión legible del stderr/stdout de un subproceso fallido."""
    partes = []
    salida_estandar = getattr(error_subproceso, "stdout", None)
    salida_error = getattr(error_subproceso, "stderr", None)
    if salida_estandar:
        partes.append(salida_estandar.strip())
    if salida_error:
        partes.append(salida_error.strip())
    return "\n".join(parte for parte in partes if parte)


def instalar_requisitos() -> None:
    """Instala las dependencias desde requirements.txt si han cambiado."""
    if not os.path.exists(ARCHIVO_REQUISITOS):
        print(f"[!] {ARCHIVO_REQUISITOS} no encontrado, continuando sin dependencias extras...")
        return

    ruta_requisitos = Path(ARCHIVO_REQUISITOS)
    ruta_marca = Path(DIRECTORIO_ENTORNO_VIRTUAL) / ".requirements.sha256"
    hash_requisitos = hashlib.sha256(ruta_requisitos.read_bytes()).hexdigest()

    if ruta_marca.exists() and ruta_marca.read_text(encoding="utf-8").strip() == hash_requisitos:
        print("[OK] Dependencias verificadas (sin cambios)")
        return

    print("Instalando dependencias...")
    ejecutar_comando_pip("install", "-r", ARCHIVO_REQUISITOS)
    ruta_marca.write_text(hash_requisitos, encoding="utf-8")
    print("   [OK] Dependencias instaladas")


def asegurar_entorno() -> None:
    """Verifica el entorno virtual y las dependencias necesarias antes del arranque."""
    if existe_entorno_virtual():
        print(f"[OK] Entorno virtual encontrado: {DIRECTORIO_ENTORNO_VIRTUAL}")
    else:
        print("[OK] Entorno virtual no encontrado")
        crear_entorno_virtual()

    instalar_requisitos()


def ejecutar_aplicacion_principal(argumentos=None) -> None:
    """Ejecuta Asist{1d0} con el Python del entorno virtual."""
    argumentos = list(argumentos or [])
    ejecutable_python = obtener_ejecutable_python()

    print("[OK] Iniciando Asist{1d0}...\n")
    print("─" * 70)
    subprocess.run(
        [ejecutable_python, "-m", MODULO_PRINCIPAL, *argumentos],
        check=True,
    )


def mostrar_banner() -> None:
    """Muestra el banner del lanzador."""
    print(
        """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                               Asist{1d0}                                      ║
║              Help Desk · Gestión de incidencias y equipos                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
    )


def principal(argumentos=None) -> None:
    """Función principal del lanzador."""
    os.chdir(Path(__file__).parent)
    mostrar_banner()

    try:
        asegurar_entorno()
        ejecutar_aplicacion_principal(
            argumentos if argumentos is not None else sys.argv[1:]
        )
    except KeyboardInterrupt:
        print("\n[OK] Asist{1d0} finalizado por el usuario")
        sys.exit(0)
    except subprocess.CalledProcessError as error_subproceso:
        if error_subproceso.returncode in (130, -2):
            print("\n[OK] Asist{1d0} finalizado correctamente")
            sys.exit(0)
        print(f"[!] Error ocurrido: {error_subproceso}")
        detalles = formatear_error_subproceso(error_subproceso)
        if detalles:
            print(detalles)
        sys.exit(1)
    except Exception as error_inesperado:
        print(f"[!] Error inesperado: {error_inesperado}")
        sys.exit(1)


if __name__ == "__main__":
    principal()
