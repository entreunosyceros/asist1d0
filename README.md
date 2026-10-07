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
<p align="center">
<img width="378" height="490" alt="login" src="https://github.com/user-attachments/assets/63e8c300-5cc7-441f-9bb7-4071ae81884b" />
</p>

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

<p align="center">
![Uploading about-asist1d0.png…]()
</p>

| Rol | Capacidades principales |
|-----|-------------------------|
| **Usuario** | Sus equipos (alta/edición), incidencias (crear, comentar, adjuntos, editar descripción), dashboard |
| **Técnico** | Incidencias (estado, asignación, intervenciones, repuestos), inventario, informes y panel técnico |
| **Administrador** | Todo lo del técnico + gestión de usuarios |

Todos los roles pueden **cambiar su propia contraseña** (menú Sesión o bandeja).

## Interfaz principal

<p align="center">
<img width="1920" height="1011" alt="asistido-admin" src="https://github.com/user-attachments/assets/d86cf079-ad73-4239-ab39-887eec90297e" />
</p>

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

- **Búsqueda global** — cuadro `🔎 Buscar…` (Ctrl+K): incidencias, equipos, usuarios, comentarios y artículos a la vez
- **Dashboard** — paneles INCIDENCIAS / SLA / TÉCNICOS, gráficas nativas (día, categoría, prioridad, resolución, técnico) y accesos rápidos
- **Incidencias** — catálogo jerárquico, asignación grupo→técnico, sugerencias KB al crear, badge Vencida, timeline, adjuntos
- **Equipos** — ficha con specs (CPU/RAM/SSD/GPU), árbol de componentes/software/reparaciones/incidencias/usuario; alta/edición
- **Usuarios** — CRUD (admin) con pertenencia a grupos de soporte; lectura para técnico; **Mi contraseña**
- **Inventario** — stock de repuestos; al usarlos en un ticket se asocian también al equipo
- **Base de conocimiento** — artículos de autoayuda ligados a categorías; edición técnico/admin
- **Informes** — estadísticas por estado/prioridad/técnico y exportación CSV
- **Auditoría** — trazabilidad global (`audit_log`: quién hizo qué); distinta del historial por ticket
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

<p align="center">
<img width="1913" height="922" alt="portalweb" src="https://github.com/user-attachments/assets/074df649-0733-4074-ad97-fb0f4c504941" />
</p>

Misma base SQLite que el escritorio.

**Desde el escritorio:** menú **Ir → Abrir portal web…** (también en la bandeja). Si la API no está en marcha, la arranca sola y abre el navegador.

**Manual:**

```bash
source .venv/bin/activate
pip install -r requirements.txt   # si aún no tienes FastAPI
python run_api.py
```

Portal: http://127.0.0.1:8765/portal/ (login demo: `juan@asist1d0.local` / `juan123`).

Endpoints útiles bajo `/api/` (Bearer JWT tras `POST /api/auth/login`): incidencias, comentarios, confirmar, reabrir, equipos, `GET /api/audit` (admin/técnico).

### Auditoría vs historial del ticket

<p align="center">
<img width="1917" height="1011" alt="auditoria" src="https://github.com/user-attachments/assets/ae0ce8d7-cc1a-4a08-a7e0-34c4ca96a12f" />
</p>

- **Historial / timeline** (en la ficha de la incidencia): actividad unificada del caso (estados, comentarios, intervenciones, repuestos).
- **Auditoría** (sección Escritorio + `GET /api/audit`): registro transversal de acciones sobre usuarios, equipos, inventario e incidencias, filtrable por actor/acción/fecha/entidad.

## Email SMTP

Copia [`data/smtp.json.example`](data/smtp.json.example) a `data/smtp.json` y rellena host/usuario/clave. Si no hay config válida, los avisos se escriben en `logs/email_outbox.log`.

## SLA

Cada categoría del catálogo define su propio SLA en horas (p. ej. Impresora 48 h, Internet 8 h). Si no hay categoría reconocida, se usa el fallback por prioridad: Baja 7 d, Media 3 d, Alta 1 d, Crítica 24 h. Los tickets abiertos fuera de plazo muestran **Vencida**.

### Catálogo de categorías

Árbol Hardware / Software / Red (más Cuenta y Otro). Cada hoja compone prioridad por defecto, SLA, plantilla, grupo de soporte y campos específicos (polimorfismo por familia).

### Grupos de técnicos

<p align="center">
<img width="1917" height="1047" alt="usuarios" src="https://github.com/user-attachments/assets/19bfa398-36f2-4ef6-8b51-4353c8349d3a" />
</p>

Colas reales en BBDD: **Soporte Hardware**, **Soporte Software**, **Redes**, **Sistemas**. Un técnico/admin puede pertenecer a varios. Al crear una incidencia se encola en el grupo de su categoría; luego se puede asignar a un técnico de ese grupo.

### Base de conocimiento
<p align="center">
<img width="1919" height="1009" alt="base-conocimiento" src="https://github.com/user-attachments/assets/d4cf2df4-87b7-4825-8263-84acf71329ff" />
</p>

Artículos de autoayuda ligados a categorías del catálogo. Al crear una incidencia aparecen **posibles soluciones** (doble clic para leer). Todos los roles pueden consultar; técnico y admin pueden crear/editar.

### Inventario de equipos (relaciones SQLite)

<p align="center">
<img width="1922" height="1010" alt="inventario" src="https://github.com/user-attachments/assets/82fd183f-d839-4c4e-b4a1-f3dc1eb54e4a" />
</p>

Cada equipo (`PC-023`) tiene especificaciones (CPU, RAM, almacenamiento, GPU, SO) y tablas hijas:

- `equipo_componentes` → piezas del inventario instaladas
- `equipo_software` → aplicaciones/licencias
- `equipo_reparaciones` → historial (opcionalmente ligado a una incidencia)
- incidencias y usuario asignado (ya existentes)

Usar un repuesto en un ticket actualiza stock, asocia la pieza al equipo y deja constancia en reparaciones.

## Empaquetado instalable

No incluido (pendiente).
