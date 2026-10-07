"""
Catálogo jerárquico de categorías de incidencia.

Usa **composición** (perfil = SLA + plantilla + grupo + campos) y
**polimorfismo** (hojas Hardware/Software/Red formatean campos distintos).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional

from app.models.enums import Prioridad


# ---------------------------------------------------------------------------
# Piezas compuestas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlaPolicy:
    """Política de plazo en horas desde la creación del ticket."""

    horas: int

    def __post_init__(self) -> None:
        if self.horas <= 0:
            raise ValueError("El SLA debe ser mayor que 0 horas")

    def plazo_desde(self, inicio: datetime) -> datetime:
        return inicio + timedelta(hours=self.horas)

    @property
    def etiqueta(self) -> str:
        """Siempre en horas (coherente con la definición del catálogo)."""
        return f"{self.horas} h"


@dataclass(frozen=True)
class PlantillaIncidencia:
    titulo: str
    descripcion: str


@dataclass(frozen=True)
class CampoEspecifico:
    """Campo adicional pedido al crear según la categoría hoja."""

    clave: str
    etiqueta: str
    hint: str = ""
    obligatorio: bool = False


@dataclass(frozen=True)
class GrupoCatalogo:
    """Referencia al grupo de soporte (código alineado con ``grupos_soporte``)."""

    codigo: str
    nombre: str


@dataclass(frozen=True)
class PerfilCategoria:
    """Composición de metadatos de una categoría hoja."""

    prioridad: Prioridad
    sla: SlaPolicy
    plantilla: PlantillaIncidencia
    grupo: GrupoCatalogo
    campos: tuple[CampoEspecifico, ...] = ()


# ---------------------------------------------------------------------------
# Árbol: grupo / hoja (polimorfismo)
# ---------------------------------------------------------------------------


class CategoriaNodo(ABC):
    """Nodo del catálogo (grupo o hoja seleccionable)."""

    @property
    @abstractmethod
    def codigo(self) -> str:
        ...

    @property
    @abstractmethod
    def nombre(self) -> str:
        ...

    @abstractmethod
    def es_hoja(self) -> bool:
        ...

    @abstractmethod
    def hojas(self) -> list[CategoriaHoja]:
        ...

    def etiqueta_ruta(self) -> str:
        return self.nombre


@dataclass
class CategoriaGrupo(CategoriaNodo):
    """Familia (Hardware, Software, Red…) con hijas."""

    _codigo: str
    _nombre: str
    _hijos: list[CategoriaNodo] = field(default_factory=list)

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def hijos(self) -> list[CategoriaNodo]:
        return self._hijos

    def es_hoja(self) -> bool:
        return False

    def hojas(self) -> list[CategoriaHoja]:
        out: list[CategoriaHoja] = []
        for h in self._hijos:
            out.extend(h.hojas())
        return out


@dataclass
class CategoriaHoja(CategoriaNodo):
    """Categoría seleccionable con perfil compuesto."""

    _codigo: str
    _nombre: str
    _perfil: PerfilCategoria
    _padre: Optional[str] = None

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def perfil(self) -> PerfilCategoria:
        return self._perfil

    @property
    def padre(self) -> Optional[str]:
        return self._padre

    def es_hoja(self) -> bool:
        return True

    def hojas(self) -> list[CategoriaHoja]:
        return [self]

    def etiqueta_ruta(self) -> str:
        if self._padre:
            return f"{self._padre} › {self._nombre}"
        return self._nombre

    def enriquecer_descripcion(
        self, base: str, valores: dict[str, str]
    ) -> str:
        """Añade el bloque de campos específicos (polimórfico)."""
        bloque = self.formatear_campos(valores)
        base = (base or "").rstrip()
        if not bloque:
            return base
        if base:
            return f"{base}\n\n{bloque}"
        return bloque

    def formatear_campos(self, valores: dict[str, str]) -> str:
        """Por defecto: lista etiqueta: valor. Las subclases especializan."""
        lineas: list[str] = []
        for campo in self._perfil.campos:
            val = (valores.get(campo.clave) or "").strip()
            if not val:
                continue
            lineas.append(f"• {campo.etiqueta}: {val}")
        if not lineas:
            return ""
        return "Datos específicos:\n" + "\n".join(lineas)

    def a_api(self) -> dict:
        p = self._perfil
        return {
            "value": self.codigo,
            "nombre": self.nombre,
            "ruta": self.etiqueta_ruta(),
            "padre": self._padre,
            "titulo": p.plantilla.titulo,
            "descripcion": p.plantilla.descripcion,
            "prioridad": p.prioridad.value,
            "sla_horas": p.sla.horas,
            "sla_etiqueta": p.sla.etiqueta,
            "grupo": {"codigo": p.grupo.codigo, "nombre": p.grupo.nombre},
            "campos": [
                {
                    "clave": c.clave,
                    "etiqueta": c.etiqueta,
                    "hint": c.hint,
                    "obligatorio": c.obligatorio,
                }
                for c in p.campos
            ],
        }


class CategoriaHardware(CategoriaHoja):
    """Hoja de la familia Hardware: resalta modelo/ubicación."""

    def formatear_campos(self, valores: dict[str, str]) -> str:
        lineas: list[str] = []
        for campo in self._perfil.campos:
            val = (valores.get(campo.clave) or "").strip()
            if not val:
                continue
            lineas.append(f"• {campo.etiqueta}: {val}")
        if not lineas:
            return ""
        return "— Hardware —\n" + "\n".join(lineas)


class CategoriaSoftware(CategoriaHoja):
    """Hoja Software: versión / aplicación."""

    def formatear_campos(self, valores: dict[str, str]) -> str:
        lineas: list[str] = []
        for campo in self._perfil.campos:
            val = (valores.get(campo.clave) or "").strip()
            if not val:
                continue
            lineas.append(f"• {campo.etiqueta}: {val}")
        if not lineas:
            return ""
        return "— Software —\n" + "\n".join(lineas)


class CategoriaRed(CategoriaHoja):
    """Hoja Red: ubicación de red / síntoma."""

    def formatear_campos(self, valores: dict[str, str]) -> str:
        lineas: list[str] = []
        for campo in self._perfil.campos:
            val = (valores.get(campo.clave) or "").strip()
            if not val:
                continue
            lineas.append(f"• {campo.etiqueta}: {val}")
        if not lineas:
            return ""
        return "— Red —\n" + "\n".join(lineas)


class CategoriaGenerica(CategoriaHoja):
    """Hojas sueltas (Cuenta, Otro) sin familia tipada."""


# ---------------------------------------------------------------------------
# Construcción del catálogo
# ---------------------------------------------------------------------------

_GRUPOS = {
    "soporte_hardware": GrupoCatalogo("soporte_hardware", "Soporte Hardware"),
    "soporte_software": GrupoCatalogo("soporte_software", "Soporte Software"),
    "redes": GrupoCatalogo("redes", "Redes"),
    "sistemas": GrupoCatalogo("sistemas", "Sistemas"),
}


def _perfil(
    *,
    prioridad: Prioridad,
    horas: int,
    titulo: str,
    descripcion: str,
    grupo: str,
    campos: tuple[CampoEspecifico, ...] = (),
) -> PerfilCategoria:
    return PerfilCategoria(
        prioridad=prioridad,
        sla=SlaPolicy(horas),
        plantilla=PlantillaIncidencia(titulo, descripcion),
        grupo=_GRUPOS[grupo],
        campos=campos,
    )


def _hw(codigo: str, nombre: str, perfil: PerfilCategoria) -> CategoriaHardware:
    return CategoriaHardware(
        _codigo=f"Hardware/{codigo}",
        _nombre=nombre,
        _perfil=perfil,
        _padre="Hardware",
    )


def _sw(codigo: str, nombre: str, perfil: PerfilCategoria) -> CategoriaSoftware:
    return CategoriaSoftware(
        _codigo=f"Software/{codigo}",
        _nombre=nombre,
        _perfil=perfil,
        _padre="Software",
    )


def _rd(codigo: str, nombre: str, perfil: PerfilCategoria) -> CategoriaRed:
    return CategoriaRed(
        _codigo=f"Red/{codigo}",
        _nombre=nombre,
        _perfil=perfil,
        _padre="Red",
    )


def construir_catalogo() -> list[CategoriaNodo]:
    """Árbol canónico del catálogo."""
    hardware = CategoriaGrupo(
        "Hardware",
        "Hardware",
        [
            _hw(
                "PC",
                "PC",
                _perfil(
                    prioridad=Prioridad.ALTA,
                    horas=24,
                    titulo="Fallo en el PC",
                    descripcion="Describe el síntoma (no enciende, pantallazo, ruido…) y desde cuándo ocurre.",
                    grupo="soporte_hardware",
                    campos=(
                        CampoEspecifico("modelo", "Modelo / marca", "Ej. Dell Latitude 5420"),
                        CampoEspecifico(
                            "sintoma",
                            "Síntoma principal",
                            "No enciende, pantallazo azul, lento…",
                            obligatorio=True,
                        ),
                    ),
                ),
            ),
            _hw(
                "Monitor",
                "Monitor",
                _perfil(
                    prioridad=Prioridad.MEDIA,
                    horas=48,
                    titulo="Problema con el monitor",
                    descripcion="Indica si no hay imagen, parpadea, o hay daño físico.",
                    grupo="soporte_hardware",
                    campos=(
                        CampoEspecifico("conexion", "Tipo de conexión", "HDMI, DP, VGA…"),
                        CampoEspecifico("sintoma", "Síntoma", obligatorio=True),
                    ),
                ),
            ),
            _hw(
                "Impresora",
                "Impresora",
                _perfil(
                    prioridad=Prioridad.MEDIA,
                    horas=48,
                    titulo="Problema con impresora",
                    descripcion="Modelo, si es local o de red, y qué ocurre al imprimir.",
                    grupo="soporte_hardware",
                    campos=(
                        CampoEspecifico("modelo", "Modelo", obligatorio=True),
                        CampoEspecifico("ubicacion", "Ubicación / cola", "Planta, sala, nombre de cola"),
                        CampoEspecifico(
                            "tipo",
                            "Local o red",
                            "USB / red compartida",
                        ),
                    ),
                ),
            ),
            _hw(
                "Perifericos",
                "Periféricos",
                _perfil(
                    prioridad=Prioridad.BAJA,
                    horas=72,
                    titulo="Problema con periférico",
                    descripcion="Teclado, ratón, webcam, auriculares… Indica el dispositivo y el fallo.",
                    grupo="soporte_hardware",
                    campos=(
                        CampoEspecifico(
                            "dispositivo",
                            "Dispositivo",
                            "Teclado, ratón, webcam…",
                            obligatorio=True,
                        ),
                    ),
                ),
            ),
        ],
    )

    software = CategoriaGrupo(
        "Software",
        "Software",
        [
            _sw(
                "Sistema operativo",
                "Sistema operativo",
                _perfil(
                    prioridad=Prioridad.ALTA,
                    horas=24,
                    titulo="Problema de sistema operativo",
                    descripcion="Indica el SO, si hay actualizaciones pendientes y el error exacto.",
                    grupo="soporte_software",
                    campos=(
                        CampoEspecifico("so", "Sistema operativo", "Windows 11, Ubuntu…"),
                        CampoEspecifico("error", "Mensaje de error", obligatorio=True),
                    ),
                ),
            ),
            _sw(
                "Aplicaciones",
                "Aplicaciones",
                _perfil(
                    prioridad=Prioridad.MEDIA,
                    horas=48,
                    titulo="Problema de aplicación",
                    descripcion="Nombre de la aplicación, versión si la conoces y pasos para reproducir.",
                    grupo="soporte_software",
                    campos=(
                        CampoEspecifico(
                            "aplicacion",
                            "Aplicación",
                            "Nombre y versión",
                            obligatorio=True,
                        ),
                        CampoEspecifico("pasos", "Pasos para reproducir"),
                    ),
                ),
            ),
            _sw(
                "Licencias",
                "Licencias",
                _perfil(
                    prioridad=Prioridad.MEDIA,
                    horas=72,
                    titulo="Licencia / activación de software",
                    descripcion="Producto afectado y si es alta, renovación o error de activación.",
                    grupo="soporte_software",
                    campos=(
                        CampoEspecifico(
                            "producto",
                            "Producto",
                            "Office, Adobe…",
                            obligatorio=True,
                        ),
                        CampoEspecifico("tipo", "Tipo de solicitud", "Alta / renovación / error"),
                    ),
                ),
            ),
        ],
    )

    red = CategoriaGrupo(
        "Red",
        "Red",
        [
            _rd(
                "WiFi",
                "WiFi",
                _perfil(
                    prioridad=Prioridad.ALTA,
                    horas=24,
                    titulo="Problema de Wi‑Fi",
                    descripcion="SSID, si afecta a un equipo o a varios, y desde cuándo.",
                    grupo="redes",
                    campos=(
                        CampoEspecifico("ssid", "SSID / red"),
                        CampoEspecifico(
                            "alcance",
                            "Alcance",
                            "Solo mi equipo / zona / todo el edificio",
                            obligatorio=True,
                        ),
                    ),
                ),
            ),
            _rd(
                "Ethernet",
                "Ethernet",
                _perfil(
                    prioridad=Prioridad.ALTA,
                    horas=24,
                    titulo="Problema de red cableada",
                    descripcion="Puerto, sala y si el LED del puerto está activo.",
                    grupo="redes",
                    campos=(
                        CampoEspecifico("ubicacion", "Sala / puesto", obligatorio=True),
                        CampoEspecifico("puerto", "Puerto / toma"),
                    ),
                ),
            ),
            _rd(
                "Internet",
                "Internet",
                _perfil(
                    prioridad=Prioridad.CRITICA,
                    horas=8,
                    titulo="Sin acceso a Internet",
                    descripcion="¿Afecta a toda la sede o solo a algunos servicios? Prueba DNS y proxy.",
                    grupo="redes",
                    campos=(
                        CampoEspecifico(
                            "alcance",
                            "Alcance",
                            "Un equipo / planta / sede",
                            obligatorio=True,
                        ),
                        CampoEspecifico("servicios", "Servicios afectados"),
                    ),
                ),
            ),
            _rd(
                "VPN",
                "VPN",
                _perfil(
                    prioridad=Prioridad.ALTA,
                    horas=24,
                    titulo="Problema de VPN",
                    descripcion="Cliente VPN, mensaje de error y si ocurre en casa o en sede.",
                    grupo="redes",
                    campos=(
                        CampoEspecifico("cliente", "Cliente VPN", "GlobalProtect, OpenVPN…"),
                        CampoEspecifico("error", "Mensaje de error", obligatorio=True),
                    ),
                ),
            ),
        ],
    )

    cuenta = CategoriaGenerica(
        _codigo="Cuenta",
        _nombre="Cuenta",
        _perfil=_perfil(
            prioridad=Prioridad.ALTA,
            horas=24,
            titulo="Acceso / cuenta de usuario",
            descripcion="Indica el sistema (correo, VPN, dominio…) y el tipo de acceso que necesitas.",
            grupo="sistemas",
            campos=(
                CampoEspecifico(
                    "sistema",
                    "Sistema",
                    "Correo, AD, portal…",
                    obligatorio=True,
                ),
                CampoEspecifico("tipo", "Tipo", "Alta / reset / bloqueo"),
            ),
        ),
        _padre=None,
    )

    otro = CategoriaGenerica(
        _codigo="Otro",
        _nombre="Otro",
        _perfil=_perfil(
            prioridad=Prioridad.MEDIA,
            horas=72,
            titulo="Otra incidencia",
            descripcion="Describe el problema con el máximo detalle posible.",
            grupo="sistemas",
        ),
        _padre=None,
    )

    return [hardware, software, red, cuenta, otro]


CATALOGO: list[CategoriaNodo] = construir_catalogo()

# Alias de categorías antiguas (enum plano) → códigos actuales.
_ALIAS_LEGACY: dict[str, str] = {
    "Red": "Red/WiFi",
    "Hardware": "Hardware/PC",
    "Software": "Software/Aplicaciones",
    "Impresora": "Hardware/Impresora",
    "Cuenta": "Cuenta",
    "Otro": "Otro",
}


def _indice_hojas() -> dict[str, CategoriaHoja]:
    idx: dict[str, CategoriaHoja] = {}
    for nodo in CATALOGO:
        for hoja in nodo.hojas():
            idx[hoja.codigo] = hoja
            idx[hoja.nombre] = hoja  # acceso corto por nombre de hoja
    return idx


_HOJAS = _indice_hojas()


def normalizar_codigo(valor: str | None) -> str:
    """Devuelve el código canónico (soporta legacy y nombres cortos)."""
    if not valor:
        return "Otro"
    v = valor.strip()
    if v in _HOJAS and _HOJAS[v].codigo == v:
        return v
    if v in _ALIAS_LEGACY:
        return _ALIAS_LEGACY[v]
    # Nombre de hoja sin padre: Impresora, WiFi…
    if v in _HOJAS:
        return _HOJAS[v].codigo
    return v


def resolver_categoria(valor: str | None) -> Optional[CategoriaHoja]:
    """Resuelve una hoja del catálogo a partir del valor almacenado."""
    codigo = normalizar_codigo(valor)
    hoja = _HOJAS.get(codigo)
    if hoja is not None:
        return hoja
    # Prefijo de grupo sin hoja (datos antiguos "Hardware")
    return _HOJAS.get(_ALIAS_LEGACY.get(valor or "", ""))


def listar_hojas() -> list[CategoriaHoja]:
    out: list[CategoriaHoja] = []
    for nodo in CATALOGO:
        out.extend(nodo.hojas())
    return out


def listar_para_filtro() -> list[tuple[str, str]]:
    """Pares (etiqueta, valor) para combos de filtro (grupos + hojas)."""
    items: list[tuple[str, str]] = []
    for nodo in CATALOGO:
        if isinstance(nodo, CategoriaGrupo):
            items.append((f"{nodo.nombre} (todas)", nodo.codigo))
            for hoja in nodo.hojas():
                items.append((f"  {hoja.etiqueta_ruta()}", hoja.codigo))
        else:
            items.append((nodo.etiqueta_ruta(), nodo.codigo))
    return items


def etiqueta_categoria(valor: str | None) -> str:
    hoja = resolver_categoria(valor)
    if hoja:
        return hoja.etiqueta_ruta()
    return valor or "Otro"


def coincide_filtro(categoria_guardada: str, filtro: str) -> bool:
    """True si la categoría almacenada encaja con el filtro (hoja o grupo)."""
    if not filtro:
        return True
    guardada = normalizar_codigo(categoria_guardada)
    if guardada == filtro or categoria_guardada == filtro:
        return True
    # Filtro de grupo: Hardware → Hardware/*
    if "/" not in filtro and (
        guardada.startswith(filtro + "/") or categoria_guardada == filtro
    ):
        return True
    return False


def catalogo_api() -> list[dict]:
    """Lista plana de hojas para API/portal."""
    return [h.a_api() for h in listar_hojas()]


def grupos_catalogo() -> Iterable[GrupoCatalogo]:
    return _GRUPOS.values()
