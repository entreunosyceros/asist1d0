-- Esquema SQLite de Asist1d0
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    telefono TEXT,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('usuario', 'tecnico', 'administrador')),
    activo INTEGER NOT NULL DEFAULT 1,
    es_demo INTEGER NOT NULL DEFAULT 0,
    fecha_alta TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    numero_serie TEXT NOT NULL UNIQUE,
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    sistema_operativo TEXT,
    fecha_registro TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS incidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL,
    tecnico_id INTEGER,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT NOT NULL DEFAULT 'Otro'
        CHECK (categoria IN ('Red', 'Hardware', 'Software', 'Impresora', 'Cuenta', 'Otro')),
    estado TEXT NOT NULL DEFAULT 'Abierta'
        CHECK (estado IN ('Abierta', 'En reparación', 'Pendiente', 'Cerrada')),
    prioridad TEXT NOT NULL DEFAULT 'Media'
        CHECK (prioridad IN ('Baja', 'Media', 'Alta', 'Crítica')),
    fecha_creacion TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_cierre TEXT,
    FOREIGN KEY (equipo_id) REFERENCES equipos(id) ON DELETE CASCADE,
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS intervenciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id INTEGER NOT NULL,
    tecnico_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
    FOREIGN KEY (tecnico_id) REFERENCES usuarios(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS componentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    precio REAL NOT NULL DEFAULT 0 CHECK (precio >= 0),
    descripcion TEXT,
    es_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS incidencia_componentes (
    incidencia_id INTEGER NOT NULL,
    componente_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (incidencia_id, componente_id),
    FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
    FOREIGN KEY (componente_id) REFERENCES componentes(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id INTEGER NOT NULL,
    accion TEXT NOT NULL,
    usuario_id INTEGER,
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    texto TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS adjuntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incidencia_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    nombre_original TEXT NOT NULL,
    nombre_archivo TEXT NOT NULL,
    tamano INTEGER NOT NULL DEFAULT 0 CHECK (tamano >= 0),
    fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (incidencia_id) REFERENCES incidencias(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios(rol);
CREATE INDEX IF NOT EXISTS idx_equipos_usuario ON equipos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_equipos_serie ON equipos(numero_serie);
CREATE INDEX IF NOT EXISTS idx_incidencias_estado ON incidencias(estado);
CREATE INDEX IF NOT EXISTS idx_incidencias_prioridad ON incidencias(prioridad);
CREATE INDEX IF NOT EXISTS idx_incidencias_equipo ON incidencias(equipo_id);
CREATE INDEX IF NOT EXISTS idx_incidencias_tecnico ON incidencias(tecnico_id);
CREATE INDEX IF NOT EXISTS idx_intervenciones_incidencia ON intervenciones(incidencia_id);
CREATE INDEX IF NOT EXISTS idx_historial_incidencia ON historial(incidencia_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_incidencia ON comentarios(incidencia_id);
CREATE INDEX IF NOT EXISTS idx_adjuntos_incidencia ON adjuntos(incidencia_id);
