# Asist{1d0}

<p align="center">
<img width="786" height="852" alt="logo" src="https://github.com/user-attachments/assets/8b89866c-f93d-4013-976f-f81b4c7586b4" />
</p>

Sistema de gestión de incidencias y equipos (mini Help Desk) en Python.

Practica **POO** (encapsulación, herencia, polimorfismo, composición), **SQLite** y una interfaz de escritorio con **PySide6**.

## Requisitos

- Python 3.10+
- PySide6 (se instala automáticamente con el lanzador)

## Instalación y ejecución

Requisitos: **Python 3.10+** (en Windows, Linux o macOS). PySide6 se instala solo.

Clonar e iniciar:

```bash
git clone https://github.com/entreunosyceros/asist1d0.git
cd asist1d0
python3 run_app.py
```

En Windows (PowerShell o CMD), si `python3` no existe:

```bash
python run_app.py
```

El script [`run_app.py`](run_app.py):

1. Crea el entorno virtual (`.venv`) si no existe
2. Instala las dependencias de `requirements.txt` (solo si cambian)
3. Inicia Asist{1d0}

También puedes lanzar la app ya configurada con:

```bash
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m app
```

Al **primer arranque** en cada equipo se crea `data/asist1d0.db` y se cargan automáticamente los datos de demostración (usuarios, equipos, incidencias e inventario). La base y los logs son locales y no van en el repositorio.

## Logo del programa

Coloca el archivo del logo en la carpeta:

```text
assets/
```

con uno de estos nombres (el primero que exista se usa):

- `logo.png` (recomendado)
- `logo.svg`
- `logo.ico`
- `logo.jpg` / `logo.jpeg`

Ejemplo: `assets/logo.png`

Se usa en:

- Pantalla de login (tarjeta del formulario)
- Icono de las ventanas
- Icono de la **bandeja del sistema** tras iniciar sesión
- Diálogo **Acerca de**

Si no hay logo, la app funciona igual con el texto del nombre.

## Acceso (login)

- Ventana **sin bordes** del sistema: solo se ve la tarjeta del formulario
- Puedes **arrastrar** la ventana y cerrarla con ✕ o Escape (sale de la aplicación)
- Opción **Recordar usuario**: guarda el último email en `data/prefs.json` (nunca la contraseña)

## Usuarios demo

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | admin@asist1d0.local | admin123 |
| Técnico | tecnico@asist1d0.local | tecnico123 |
| Usuario | juan@asist1d0.local | juan123 |
| Usuario | maria@asist1d0.local | maria123 |

Las cuentas demo están en un ámbito aislado: **no pueden ver equipos, incidencias ni informes de usuarios reales** creados después. El administrador demo puede dar de alta usuarios reales con rol Usuario, Técnico o Administrador desde **Usuarios → + Nuevo usuario**.

## Roles

| Rol | Capacidades principales |
|-----|-------------------------|
| **Usuario** | Sus equipos (alta/edición), incidencias (crear, comentar, adjuntos, editar descripción), dashboard |
| **Técnico** | Incidencias (estado, asignación, intervenciones, repuestos), inventario, informes y panel técnico |
| **Administrador** | Todo lo del técnico + gestión de usuarios |

Todos los roles pueden **cambiar su propia contraseña** (menú Sesión o bandeja).

## Interfaz principal

### Menú superior

- **Sesión** — cambiar mi contraseña y cerrar sesión (`Ctrl+L`)
- **Ir** — secciones disponibles según el rol
- **Ayuda** — guía de uso por rol (`F1`) y **Acerca de** (logo, descripción y enlace a GitHub)

### Bandeja del sistema

Tras un login correcto aparece el icono del logo en la bandeja, con:

- Mostrar la ventana
- Ir a cada sección del rol
- Cambiar mi contraseña
- Cerrar sesión / Guía / Acerca de / Salir

Cerrar la ventana principal con la X **no cierra** la app: queda en bandeja. **Salir** (menú de bandeja) termina el proceso.

La bandeja muestra avisos breves cuando te asignan una incidencia, cambia su estado o hay un comentario nuevo en un ticket que te afecta (si la sesión sigue activa en segundo plano).

### Módulos

- **Dashboard** — KPIs y accesos rápidos; CTAs si no hay equipo/incidencias
- **Incidencias** — categorías/plantillas, SLA + badge Vencida, confirmar/reabrir (Usuario), filtros (incl. categoría), comentarios, adjuntos, editar descripción; técnicos: cola, intervenciones, repuestos
- **Equipos** — alta/edición (Usuario: solo los suyos); doble clic en un ticket del árbol abre Incidencias
- **Usuarios** — CRUD (admin); lectura para técnico; botón **Mi contraseña** (admin, mismo flujo que Sesión)
- **Inventario** — componentes/repuestos y control de stock
- **Informes** — estadísticas por estado/prioridad/técnico y exportación CSV
- **Panel técnico** — consultas predefinidas, historial global y logs

## Estructura

```text
Asist1d0/
├── run_app.py              # Escritorio (venv + dependencias + arranque)
├── run_api.py              # API REST + portal web
├── requirements.txt
├── portal/                 # Frontend ligero del portal
├── api/                    # FastAPI
├── assets/
├── data/                   # SQLite, prefs, smtp.json, adjuntos
├── logs/
└── app/                    # Dominio, SQLite, servicios, UI PySide6
```

## API REST y portal web

Misma base SQLite que el escritorio.

**Desde el escritorio:** menú **Ayuda → Abrir portal web…** (también en la bandeja). Si la API no está en marcha, la arranca sola y abre el navegador.

**Manual:**

```bash
source .venv/bin/activate
pip install -r requirements.txt   # si aún no tienes FastAPI
python run_api.py
```

Portal: http://127.0.0.1:8765/portal/ (login demo: `juan@asist1d0.local` / `juan123`).

Endpoints útiles bajo `/api/` (Bearer JWT tras `POST /api/auth/login`): incidencias, comentarios, confirmar, reabrir, equipos.

## Email SMTP

Copia [`data/smtp.json.example`](data/smtp.json.example) a `data/smtp.json` y rellena host/usuario/clave. Si no hay config válida, los avisos se escriben en `logs/email_outbox.log`.

## SLA

Plazo desde la creación: Baja 7 días, Media 3, Alta 1, Crítica 24 h. Los tickets abiertos fuera de plazo muestran **Vencida**.

## Empaquetado instalable

No incluido (pendiente).
