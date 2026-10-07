"""
Aplicación FastAPI: API REST + portal estático.

Reutiliza ``bootstrap()`` y los servicios de dominio.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from api.auth_tokens import crear_token, decodificar_token
from api.schemas import (
    AuditOut,
    ComentarioIn,
    ComentarioOut,
    EquipoIn,
    EquipoOut,
    IncidenciaIn,
    IncidenciaOut,
    LoginIn,
    TokenOut,
    UsuarioOut,
)
from app.auth.password import verify_password
from app.auth.service import SessionContext
from app.bootstrap import AppContext, bootstrap
from app.config import API_HOST, API_PORT, BASE_DIR
from app.models.audit import AuditAction, AuditEntity
from app.models.catalogo_categorias import catalogo_api, normalizar_codigo
from app.models.enums import Prioridad, Rol
from app.models.incidencia import Incidencia

security = HTTPBearer(auto_error=False)
_ctx: AppContext | None = None
PORTAL_DIR = BASE_DIR / "portal"

app = FastAPI(title="Asist{1d0} API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_ctx() -> AppContext:
    global _ctx
    if _ctx is None:
        _ctx = bootstrap()
    return _ctx


def current_session(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ctx: AppContext = Depends(get_ctx),
) -> SessionContext:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    try:
        payload = decodificar_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from exc
    usuario = ctx.usuarios.obtener(int(payload["sub"]))
    if not usuario or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")
    return SessionContext(usuario=usuario)


def _inc_out(inc: Incidencia, *, con_comentarios: bool = False) -> IncidenciaOut:
    limite = inc.fecha_limite
    comentarios: list[ComentarioOut] = []
    if con_comentarios:
        for c in inc.comentarios:
            comentarios.append(
                ComentarioOut(
                    id=c.id,
                    texto=c.texto,
                    fecha=c.fecha,
                    usuario_nombre=c.usuario_nombre,
                )
            )
    return IncidenciaOut(
        id=inc.id or 0,
        codigo=inc.codigo,
        titulo=inc.titulo,
        descripcion=inc.descripcion,
        categoria=inc.categoria_etiqueta,
        estado=inc.estado.value,
        estado_usuario=inc.estado.etiqueta_usuario,
        prioridad=inc.prioridad.value,
        equipo_nombre=inc.equipo_nombre,
        tecnico_nombre=inc.tecnico_nombre,
        fecha_creacion=inc.fecha_creacion,
        vencida=inc.vencida,
        fecha_limite=limite.strftime("%Y-%m-%d %H:%M") if limite else None,
        comentarios=comentarios,
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "api"


@app.post("/api/auth/login", response_model=TokenOut)
def login(
    body: LoginIn,
    request: Request,
    ctx: AppContext = Depends(get_ctx),
) -> TokenOut:
    # No usar AuthService.login: la sesión en memoria es del escritorio (una sola).
    usuario = ctx.usuario_repo.obtener_por_email(body.email.strip().lower())
    if not usuario or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    if not verify_password(body.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales incorrectas")
    ctx.audit.registrar(
        usuario.id,
        AuditAction.LOGIN,
        AuditEntity.USUARIO,
        usuario.id,
        f"Login API de {usuario.email} ({usuario.rol.value})",
        ip_address=_client_ip(request),
    )
    token = crear_token(
        usuario.id or 0,
        usuario.email,
        usuario.rol.value,
        usuario.es_demo,
    )
    return TokenOut(access_token=token)


@app.get("/api/me", response_model=UsuarioOut)
def me(session: SessionContext = Depends(current_session)) -> UsuarioOut:
    u = session.usuario
    return UsuarioOut(
        id=u.id or 0,
        nombre=u.nombre,
        email=u.email,
        rol=u.rol.value,
        es_demo=u.es_demo,
    )


@app.get("/api/equipos", response_model=list[EquipoOut])
def listar_equipos(
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> list[EquipoOut]:
    uid = session.usuario_id if session.rol == Rol.USUARIO else None
    eqs = ctx.equipos.listar(usuario_id=uid, es_demo=session.es_demo)
    return [
        EquipoOut(
            id=e.id or 0,
            numero_serie=e.numero_serie,
            marca=e.marca,
            modelo=e.modelo,
            sistema_operativo=e.sistema_operativo or "",
            nombre_completo=e.nombre_completo,
        )
        for e in eqs
    ]


@app.post("/api/equipos", response_model=EquipoOut)
def crear_equipo(
    body: EquipoIn,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> EquipoOut:
    if session.rol != Rol.USUARIO and not session.es_tecnico():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permiso")
    eq = ctx.equipos.crear(
        usuario_id=session.usuario_id,
        numero_serie=body.numero_serie,
        marca=body.marca,
        modelo=body.modelo,
        sistema_operativo=body.sistema_operativo,
    )
    return EquipoOut(
        id=eq.id or 0,
        numero_serie=eq.numero_serie,
        marca=eq.marca,
        modelo=eq.modelo,
        sistema_operativo=eq.sistema_operativo or "",
        nombre_completo=eq.nombre_completo,
    )


@app.get("/api/incidencias", response_model=list[IncidenciaOut])
def listar_incidencias(
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> list[IncidenciaOut]:
    kwargs: dict = {"es_demo": session.es_demo}
    if session.rol == Rol.USUARIO:
        kwargs["usuario_id"] = session.usuario_id
    return [_inc_out(i) for i in ctx.incidencias.listar(**kwargs)]


@app.get("/api/incidencias/{incidencia_id}", response_model=IncidenciaOut)
def obtener_incidencia(
    incidencia_id: int,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> IncidenciaOut:
    inc = ctx.incidencias.obtener(incidencia_id, es_demo=session.es_demo)
    if not inc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrada")
    if session.rol == Rol.USUARIO and inc.usuario_id != session.usuario_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso")
    return _inc_out(inc, con_comentarios=True)


@app.post("/api/incidencias", response_model=IncidenciaOut)
def crear_incidencia(
    body: IncidenciaIn,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> IncidenciaOut:
    try:
        prioridad = Prioridad(body.prioridad)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    categoria = normalizar_codigo(body.categoria)
    if session.rol == Rol.USUARIO:
        eq = ctx.equipos.obtener(body.equipo_id)
        if not eq or eq.usuario_id != session.usuario_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Equipo no válido")
    creada = ctx.incidencias.crear(
        equipo_id=body.equipo_id,
        titulo=body.titulo,
        descripcion=body.descripcion,
        prioridad=prioridad,
        categoria=categoria,
        actor_id=session.usuario_id,
    )
    full = ctx.incidencias.obtener(creada.id or 0, es_demo=session.es_demo)
    return _inc_out(full or creada, con_comentarios=True)


@app.post("/api/incidencias/{incidencia_id}/comentarios", response_model=ComentarioOut)
def comentar(
    incidencia_id: int,
    body: ComentarioIn,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> ComentarioOut:
    try:
        c = ctx.incidencias.agregar_comentario(
            incidencia_id,
            session.usuario_id,
            body.texto,
            rol=session.rol,
            es_demo=session.es_demo,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return ComentarioOut(
        id=c.id, texto=c.texto, fecha=c.fecha, usuario_nombre=c.usuario_nombre
    )


@app.post("/api/incidencias/{incidencia_id}/confirmar", response_model=IncidenciaOut)
def confirmar(
    incidencia_id: int,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> IncidenciaOut:
    try:
        inc = ctx.incidencias.confirmar_resolucion(
            incidencia_id,
            actor_id=session.usuario_id,
            rol=session.rol,
            es_demo=session.es_demo,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    full = ctx.incidencias.obtener(incidencia_id, es_demo=session.es_demo)
    return _inc_out(full or inc, con_comentarios=True)


@app.post("/api/incidencias/{incidencia_id}/reabrir", response_model=IncidenciaOut)
def reabrir(
    incidencia_id: int,
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
) -> IncidenciaOut:
    try:
        inc = ctx.incidencias.reabrir(
            incidencia_id,
            actor_id=session.usuario_id,
            rol=session.rol,
            es_demo=session.es_demo,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    full = ctx.incidencias.obtener(incidencia_id, es_demo=session.es_demo)
    return _inc_out(full or inc, con_comentarios=True)


@app.get("/api/categorias")
def categorias() -> list[dict]:
    """Catálogo jerárquico (hojas) con SLA, prioridad, grupo y campos."""
    return catalogo_api()


@app.get("/api/audit", response_model=list[AuditOut])
def listar_audit(
    session: SessionContext = Depends(current_session),
    ctx: AppContext = Depends(get_ctx),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    texto: Optional[str] = None,
    limite: int = Query(default=200, ge=1, le=2000),
) -> list[AuditOut]:
    if not session.puede_ver_informes_globales():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo admin/técnico")
    entradas = ctx.audit.listar(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        desde=desde,
        hasta=hasta,
        texto=texto,
        limite=limite,
    )
    return [
        AuditOut(
            id=e.id or 0,
            timestamp=e.timestamp,
            user_id=e.user_id,
            usuario_nombre=e.usuario_nombre,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            details=e.details or "",
            ip_address=e.ip_address,
        )
        for e in entradas
    ]


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/portal/")


if PORTAL_DIR.is_dir():
    app.mount(
        "/portal",
        StaticFiles(directory=str(PORTAL_DIR), html=True),
        name="portal",
    )


def create_app() -> FastAPI:
    """Compatibilidad con tests / lanzadores."""
    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
