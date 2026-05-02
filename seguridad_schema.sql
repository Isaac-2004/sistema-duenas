-- ============================================================
--  MÓDULO DE SEGURIDAD - DISTRIBUIDORA DE PRODUCTOS ALIMENTICIOS
--  MySQL 8.0  |  Complemento del schema principal
--  Versión: 1.0
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- SEC-1. modulos
--   Agrupa las funcionalidades del sistema (ej: Ventas, Inventario…)
-- ============================================================
CREATE TABLE modulos (
    id_modulo     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    codigo        VARCHAR(50)  UNIQUE NOT NULL COMMENT 'Clave técnica: VENTAS, INVENTARIO…',
    nombre        VARCHAR(100) NOT NULL,
    descripcion   VARCHAR(255),
    icono         VARCHAR(50)  COMMENT 'Nombre del icono en el frontend',
    orden         TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Orden en el menú',
    estado        TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-2. permisos
--   Acciones disponibles dentro de cada módulo (CRUD + extras)
-- ============================================================
CREATE TABLE permisos (
    id_permiso    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_modulo     INT UNSIGNED NOT NULL,
    codigo        VARCHAR(100) UNIQUE NOT NULL COMMENT 'Ej: ventas.crear, inventario.ver',
    nombre        VARCHAR(150) NOT NULL,
    descripcion   VARCHAR(255),
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_perm_modulo FOREIGN KEY (id_modulo) REFERENCES modulos(id_modulo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-3. roles
--   Perfiles predefinidos: ADMINISTRADOR, VENDEDOR, CAJERO, etc.
-- ============================================================
CREATE TABLE roles (
    id_rol        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(80)  UNIQUE NOT NULL,
    descripcion   VARCHAR(255),
    es_admin      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1 = acceso total sin verificar permisos',
    estado        TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-4. roles_permisos
--   Tabla pivote: qué permisos tiene cada rol
-- ============================================================
CREATE TABLE roles_permisos (
    id_rol        INT UNSIGNED NOT NULL,
    id_permiso    INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_rol, id_permiso),
    CONSTRAINT fk_rp_rol     FOREIGN KEY (id_rol)     REFERENCES roles(id_rol)    ON DELETE CASCADE,
    CONSTRAINT fk_rp_permiso FOREIGN KEY (id_permiso) REFERENCES permisos(id_permiso) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-5. usuarios
--   Personas que acceden al sistema con credenciales propias
-- ============================================================
CREATE TABLE usuarios (
    id_usuario          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_rol              INT UNSIGNED  NOT NULL,
    username            VARCHAR(60)   UNIQUE NOT NULL,
    email               VARCHAR(100)  UNIQUE NOT NULL,
    password_hash       VARCHAR(255)  NOT NULL        COMMENT 'bcrypt / argon2 hash — NUNCA texto plano',
    nombre_completo     VARCHAR(150)  NOT NULL,
    telefono            VARCHAR(20),

    -- Control de acceso
    estado              ENUM('ACTIVO','INACTIVO','BLOQUEADO','PENDIENTE') NOT NULL DEFAULT 'ACTIVO',
    intentos_fallidos   TINYINT UNSIGNED NOT NULL DEFAULT 0,
    bloqueado_hasta     DATETIME      NULL            COMMENT 'NULL = no bloqueado temporalmente',

    -- Seguridad adicional
    requiere_2fa        TINYINT(1)    NOT NULL DEFAULT 0,
    secreto_2fa         VARCHAR(64)   NULL             COMMENT 'Semilla TOTP (cifrada en la app)',
    debe_cambiar_pass   TINYINT(1)    NOT NULL DEFAULT 0 COMMENT 'Forzar cambio en próximo login',

    -- Auditoría de acceso
    ultimo_login        DATETIME      NULL,
    ultimo_login_ip     VARCHAR(45)   NULL             COMMENT 'IPv4 o IPv6',
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_usr_rol FOREIGN KEY (id_rol) REFERENCES roles(id_rol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-6. usuarios_permisos_extra
--   Permisos adicionales (o revocados) a nivel de usuario individual
--   Permite ajuste fino sin cambiar el rol
-- ============================================================
CREATE TABLE usuarios_permisos_extra (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT UNSIGNED NOT NULL,
    id_permiso      INT UNSIGNED NOT NULL,
    tipo            ENUM('GRANT','REVOKE') NOT NULL DEFAULT 'GRANT'
                    COMMENT 'GRANT = conceder, REVOKE = quitar aunque el rol lo tenga',
    motivo          VARCHAR(255) COMMENT 'Por qué se asignó/revocó',
    asignado_por    INT UNSIGNED NOT NULL COMMENT 'id_usuario del admin que hizo el cambio',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_usr_perm (id_usuario, id_permiso),
    CONSTRAINT fk_upe_usuario  FOREIGN KEY (id_usuario)   REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_upe_permiso  FOREIGN KEY (id_permiso)   REFERENCES permisos(id_permiso) ON DELETE CASCADE,
    CONSTRAINT fk_upe_asignado FOREIGN KEY (asignado_por) REFERENCES usuarios(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-7. sesiones
--   Token activo por sesión (JWT refresh token o session token)
-- ============================================================
CREATE TABLE sesiones (
    id_sesion       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT UNSIGNED  NOT NULL,
    token_hash      VARCHAR(255)  UNIQUE NOT NULL COMMENT 'SHA-256 del token real',
    ip_address      VARCHAR(45)   NOT NULL,
    user_agent      VARCHAR(500),
    dispositivo     VARCHAR(100)  COMMENT 'Ej: Chrome / Windows, iPhone / iOS',
    activa          TINYINT(1)    NOT NULL DEFAULT 1,
    expira_en       DATETIME      NOT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrada_en      DATETIME      NULL     COMMENT 'Cuándo se cerró la sesión',
    cerrada_motivo  ENUM('LOGOUT','EXPIRADA','ADMIN','SEGURIDAD') NULL,
    CONSTRAINT fk_ses_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-8. tokens_recuperacion
--   Tokens de un solo uso para recuperar contraseña
-- ============================================================
CREATE TABLE tokens_recuperacion (
    id_token        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT UNSIGNED  NOT NULL,
    token_hash      VARCHAR(255)  UNIQUE NOT NULL COMMENT 'SHA-256 del token enviado por email',
    tipo            ENUM('RESET_PASSWORD','ACTIVACION','CAMBIO_EMAIL') NOT NULL DEFAULT 'RESET_PASSWORD',
    usado           TINYINT(1)    NOT NULL DEFAULT 0,
    expira_en       DATETIME      NOT NULL,
    ip_solicitante  VARCHAR(45),
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usado_en        DATETIME      NULL,
    CONSTRAINT fk_tk_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-9. historial_passwords
--   Últimas N contraseñas de cada usuario para evitar reutilización
-- ============================================================
CREATE TABLE historial_passwords (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT UNSIGNED  NOT NULL,
    password_hash   VARCHAR(255)  NOT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hp_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-10. audit_logs
--   Registro inmutable de TODAS las acciones sensibles del sistema
--   (creaciones, ediciones, eliminaciones, accesos, errores)
-- ============================================================
CREATE TABLE audit_logs (
    id_log          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT UNSIGNED  NULL     COMMENT 'NULL si es acción del sistema/anónima',
    accion          VARCHAR(100)  NOT NULL COMMENT 'Ej: CREAR_VENTA, EDITAR_CLIENTE, LOGIN_FALLIDO',
    modulo          VARCHAR(50)   NOT NULL COMMENT 'Módulo afectado',
    tabla_afectada  VARCHAR(100)  NULL     COMMENT 'Tabla de BD modificada',
    id_registro     INT UNSIGNED  NULL     COMMENT 'PK del registro afectado',
    descripcion     TEXT          NOT NULL COMMENT 'Descripción legible del evento',
    datos_anteriores JSON         NULL     COMMENT 'Snapshot antes del cambio (UPDATE/DELETE)',
    datos_nuevos     JSON         NULL     COMMENT 'Snapshot después del cambio (INSERT/UPDATE)',
    ip_address      VARCHAR(45)   NULL,
    user_agent      VARCHAR(500)  NULL,
    resultado       ENUM('EXITO','FALLO','ERROR') NOT NULL DEFAULT 'EXITO',
    created_at      DATETIME(3)   NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Precisión de milisegundos',
    CONSTRAINT fk_log_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-11. login_intentos
--   Historial de intentos de acceso (para detectar ataques de fuerza bruta)
-- ============================================================
CREATE TABLE login_intentos (
    id_intento      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username_input  VARCHAR(100) NOT NULL COMMENT 'Lo que el atacante ingresó como usuario',
    ip_address      VARCHAR(45)  NOT NULL,
    user_agent      VARCHAR(500),
    exitoso         TINYINT(1)   NOT NULL DEFAULT 0,
    motivo_fallo    VARCHAR(100) NULL COMMENT 'USUARIO_NO_EXISTE, CLAVE_INCORRECTA, BLOQUEADO…',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SEC-12. configuracion_seguridad
--   Parámetros de política de seguridad modificables por el admin
-- ============================================================
CREATE TABLE configuracion_seguridad (
    id_config       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    clave           VARCHAR(100) UNIQUE NOT NULL,
    valor           VARCHAR(255) NOT NULL,
    descripcion     VARCHAR(255),
    updated_by      INT UNSIGNED NULL,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cfg_usuario FOREIGN KEY (updated_by) REFERENCES usuarios(id_usuario) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- ÍNDICES DE RENDIMIENTO
-- ============================================================
CREATE INDEX idx_audit_usuario   ON audit_logs(id_usuario);
CREATE INDEX idx_audit_fecha     ON audit_logs(created_at);
CREATE INDEX idx_audit_accion    ON audit_logs(accion);
CREATE INDEX idx_audit_tabla     ON audit_logs(tabla_afectada, id_registro);
CREATE INDEX idx_sesiones_token  ON sesiones(token_hash);
CREATE INDEX idx_sesiones_usr    ON sesiones(id_usuario, activa);
CREATE INDEX idx_sesiones_exp    ON sesiones(expira_en);
CREATE INDEX idx_login_ip        ON login_intentos(ip_address, created_at);
CREATE INDEX idx_login_usr       ON login_intentos(username_input, created_at);
CREATE INDEX idx_tokens_hash     ON tokens_recuperacion(token_hash);
CREATE INDEX idx_histpass_usr    ON historial_passwords(id_usuario, created_at);

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================
-- DATOS INICIALES DEL MÓDULO DE SEGURIDAD
-- ============================================================

-- Módulos del sistema
INSERT INTO modulos (codigo, nombre, descripcion, orden) VALUES
('DASHBOARD',   'Panel Principal',      'Resumen y estadísticas generales', 1),
('CLIENTES',    'Clientes',             'Gestión de clientes',              2),
('PROVEEDORES', 'Proveedores',          'Gestión de proveedores',           3),
('PRODUCTOS',   'Productos',            'Catálogo y precios',               4),
('INVENTARIO',  'Inventario',           'Control de stock',                 5),
('COMPRAS',     'Compras',              'Registro de compras',              6),
('PEDIDOS',     'Pedidos',              'Gestión de pedidos',               7),
('VENTAS',      'Ventas',               'Registro de ventas',               8),
('FACTURAS',    'Facturación',          'Emisión de facturas',              9),
('CXC',         'Cuentas por Cobrar',   'Créditos y abonos',               10),
('REPORTES',    'Reportes',             'Reportes y estadísticas',         11),
('SEGURIDAD',   'Seguridad',            'Usuarios, roles y permisos',      12),
('CONFIG',      'Configuración',        'Parámetros del sistema',          13);

-- Permisos estándar por módulo (ver, crear, editar, eliminar, exportar)
INSERT INTO permisos (id_modulo, codigo, nombre) VALUES
-- DASHBOARD
(1, 'dashboard.ver',            'Ver panel principal'),
-- CLIENTES
(2, 'clientes.ver',             'Ver clientes'),
(2, 'clientes.crear',           'Crear clientes'),
(2, 'clientes.editar',          'Editar clientes'),
(2, 'clientes.eliminar',        'Eliminar / inactivar clientes'),
(2, 'clientes.exportar',        'Exportar clientes'),
-- PROVEEDORES
(3, 'proveedores.ver',          'Ver proveedores'),
(3, 'proveedores.crear',        'Crear proveedores'),
(3, 'proveedores.editar',       'Editar proveedores'),
(3, 'proveedores.eliminar',     'Eliminar / inactivar proveedores'),
-- PRODUCTOS
(4, 'productos.ver',            'Ver productos'),
(4, 'productos.crear',          'Crear productos'),
(4, 'productos.editar',         'Editar productos'),
(4, 'productos.eliminar',       'Eliminar / inactivar productos'),
(4, 'productos.cambiar_precio', 'Cambiar precios'),
-- INVENTARIO
(5, 'inventario.ver',           'Ver inventario y movimientos'),
(5, 'inventario.ajustar',       'Realizar ajustes manuales de stock'),
-- COMPRAS
(6, 'compras.ver',              'Ver compras'),
(6, 'compras.crear',            'Registrar compras'),
(6, 'compras.anular',           'Anular compras'),
-- PEDIDOS
(7, 'pedidos.ver',              'Ver pedidos'),
(7, 'pedidos.crear',            'Crear pedidos'),
(7, 'pedidos.editar',           'Editar pedidos'),
(7, 'pedidos.cancelar',         'Cancelar pedidos'),
-- VENTAS
(8, 'ventas.ver',               'Ver ventas'),
(8, 'ventas.crear',             'Registrar ventas'),
(8, 'ventas.anular',            'Anular ventas'),
(8, 'ventas.descuento',         'Aplicar descuentos'),
-- FACTURAS
(9, 'facturas.ver',             'Ver facturas'),
(9, 'facturas.emitir',          'Emitir facturas'),
(9, 'facturas.anular',          'Anular facturas'),
-- CXC
(10,'cxc.ver',                  'Ver cuentas por cobrar'),
(10,'cxc.registrar_abono',      'Registrar abonos'),
(10,'cxc.exportar',             'Exportar reporte de cartera'),
-- REPORTES
(11,'reportes.ventas',          'Ver reportes de ventas'),
(11,'reportes.inventario',      'Ver reportes de inventario'),
(11,'reportes.cxc',             'Ver reporte de cartera'),
(11,'reportes.compras',         'Ver reportes de compras'),
-- SEGURIDAD
(12,'seguridad.ver_usuarios',   'Ver usuarios'),
(12,'seguridad.gestionar_usuarios', 'Crear/editar/inactivar usuarios'),
(12,'seguridad.gestionar_roles','Gestionar roles y permisos'),
(12,'seguridad.ver_logs',       'Ver audit logs'),
-- CONFIG
(13,'config.ver',               'Ver configuración del sistema'),
(13,'config.editar',            'Editar configuración del sistema');

-- Roles predefinidos
INSERT INTO roles (nombre, descripcion, es_admin) VALUES
('ADMINISTRADOR', 'Acceso total al sistema',                              1),
('VENDEDOR',      'Puede crear pedidos, ventas y registrar abonos',       0),
('CAJERO',        'Gestiona cobros, facturas y abonos',                   0),
('BODEGUERO',     'Gestiona compras e inventario',                        0),
('SUPERVISOR',    'Acceso de lectura a todo + reportes',                  0);

-- Permisos del rol VENDEDOR
INSERT INTO roles_permisos (id_rol, id_permiso)
SELECT 2, id_permiso FROM permisos WHERE codigo IN (
    'dashboard.ver',
    'clientes.ver','clientes.crear','clientes.editar',
    'productos.ver',
    'inventario.ver',
    'pedidos.ver','pedidos.crear','pedidos.editar','pedidos.cancelar',
    'ventas.ver','ventas.crear','ventas.descuento',
    'facturas.ver','facturas.emitir',
    'cxc.ver','cxc.registrar_abono'
);

-- Permisos del rol CAJERO
INSERT INTO roles_permisos (id_rol, id_permiso)
SELECT 3, id_permiso FROM permisos WHERE codigo IN (
    'dashboard.ver',
    'clientes.ver',
    'ventas.ver',
    'facturas.ver','facturas.emitir','facturas.anular',
    'cxc.ver','cxc.registrar_abono','cxc.exportar',
    'reportes.ventas','reportes.cxc'
);

-- Permisos del rol BODEGUERO
INSERT INTO roles_permisos (id_rol, id_permiso)
SELECT 4, id_permiso FROM permisos WHERE codigo IN (
    'dashboard.ver',
    'productos.ver','productos.crear','productos.editar',
    'proveedores.ver','proveedores.crear','proveedores.editar',
    'inventario.ver','inventario.ajustar',
    'compras.ver','compras.crear','compras.anular',
    'reportes.inventario','reportes.compras'
);

-- Permisos del rol SUPERVISOR (solo lectura + reportes)
INSERT INTO roles_permisos (id_rol, id_permiso)
SELECT 5, id_permiso FROM permisos WHERE codigo IN (
    'dashboard.ver',
    'clientes.ver','clientes.exportar',
    'proveedores.ver',
    'productos.ver',
    'inventario.ver',
    'compras.ver',
    'pedidos.ver',
    'ventas.ver',
    'facturas.ver',
    'cxc.ver','cxc.exportar',
    'reportes.ventas','reportes.inventario','reportes.cxc','reportes.compras',
    'seguridad.ver_usuarios','seguridad.ver_logs'
);

-- Configuración de política de seguridad por defecto
INSERT INTO configuracion_seguridad (clave, valor, descripcion) VALUES
('pass_min_length',        '8',     'Longitud mínima de contraseña'),
('pass_requiere_mayuscula','1',     '1=Obligatorio tener al menos una mayúscula'),
('pass_requiere_numero',   '1',     '1=Obligatorio tener al menos un número'),
('pass_requiere_especial', '1',     '1=Obligatorio tener al menos un carácter especial'),
('pass_historial_n',       '5',     'No permitir reutilizar las últimas N contraseñas'),
('pass_expira_dias',       '90',    'Días antes de que la contraseña expire (0=nunca)'),
('login_max_intentos',     '5',     'Intentos fallidos antes de bloquear la cuenta'),
('login_bloqueo_minutos',  '30',    'Minutos de bloqueo temporal tras superar intentos'),
('sesion_expira_minutos',  '480',   'Duración máxima de sesión activa en minutos'),
('sesion_max_por_usuario', '3',     'Sesiones simultáneas máximas por usuario'),
('2fa_obligatorio',        '0',     '1=Requerir 2FA para todos los usuarios'),
('ip_whitelist_activa',    '0',     '1=Solo permitir IPs de la lista blanca'),
('log_retension_dias',     '365',   'Días a retener los audit_logs');


-- ============================================================
-- TRIGGER: Bloqueo automático por intentos fallidos
-- ============================================================
DELIMITER $$

CREATE TRIGGER trg_after_login_fallido
AFTER INSERT ON login_intentos
FOR EACH ROW
BEGIN
    DECLARE v_max_intentos INT;
    DECLARE v_minutos_bloqueo INT;
    DECLARE v_intentos_recientes INT;

    IF NEW.exitoso = 0 THEN
        SELECT CAST(valor AS UNSIGNED) INTO v_max_intentos
        FROM configuracion_seguridad WHERE clave = 'login_max_intentos';

        SELECT CAST(valor AS UNSIGNED) INTO v_minutos_bloqueo
        FROM configuracion_seguridad WHERE clave = 'login_bloqueo_minutos';

        -- Contar intentos fallidos en los últimos N minutos
        SELECT COUNT(*) INTO v_intentos_recientes
        FROM login_intentos
        WHERE username_input = NEW.username_input
          AND exitoso = 0
          AND created_at >= DATE_SUB(NOW(), INTERVAL v_minutos_bloqueo MINUTE);

        IF v_intentos_recientes >= v_max_intentos THEN
            UPDATE usuarios
            SET estado           = 'BLOQUEADO',
                intentos_fallidos = v_intentos_recientes,
                bloqueado_hasta   = DATE_ADD(NOW(), INTERVAL v_minutos_bloqueo MINUTE)
            WHERE username = NEW.username_input
              AND estado = 'ACTIVO';
        END IF;
    END IF;
END$$


-- ============================================================
-- TRIGGER: Desbloqueo automático cuando expira el bloqueo temporal
-- (Llamar con evento programado o verificar en la app al hacer login)
-- ============================================================
CREATE TRIGGER trg_after_login_exitoso
AFTER INSERT ON login_intentos
FOR EACH ROW
BEGIN
    IF NEW.exitoso = 1 THEN
        UPDATE usuarios
        SET intentos_fallidos = 0,
            bloqueado_hasta   = NULL,
            ultimo_login      = NOW(),
            ultimo_login_ip   = NEW.ip_address
        WHERE username = NEW.username_input;
    END IF;
END$$

DELIMITER ;


-- ============================================================
-- VISTA: Resumen de permisos efectivos por usuario
-- ============================================================
CREATE VIEW v_permisos_efectivos AS
SELECT
    u.id_usuario,
    u.username,
    u.nombre_completo,
    r.nombre                AS rol,
    p.codigo                AS permiso,
    m.nombre                AS modulo,
    'ROL'                   AS origen
FROM usuarios u
JOIN roles          r  ON u.id_rol      = r.id_rol
JOIN roles_permisos rp ON r.id_rol      = rp.id_rol
JOIN permisos       p  ON rp.id_permiso = p.id_permiso
JOIN modulos        m  ON p.id_modulo   = m.id_modulo
WHERE r.es_admin = 0

UNION ALL

-- Permisos extra GRANT (adicionales al rol)
SELECT
    u.id_usuario,
    u.username,
    u.nombre_completo,
    r.nombre                AS rol,
    p.codigo                AS permiso,
    m.nombre                AS modulo,
    'EXTRA_GRANT'           AS origen
FROM usuarios               u
JOIN roles                  r   ON u.id_rol      = r.id_rol
JOIN usuarios_permisos_extra upe ON u.id_usuario = upe.id_usuario AND upe.tipo = 'GRANT'
JOIN permisos               p   ON upe.id_permiso = p.id_permiso
JOIN modulos                m   ON p.id_modulo    = m.id_modulo;


-- ============================================================
-- VISTA: Sesiones activas actuales
-- ============================================================
CREATE VIEW v_sesiones_activas AS
SELECT
    s.id_sesion,
    u.username,
    u.nombre_completo,
    r.nombre    AS rol,
    s.ip_address,
    s.dispositivo,
    s.created_at AS inicio_sesion,
    s.expira_en
FROM sesiones s
JOIN usuarios u ON s.id_usuario = u.id_usuario
JOIN roles    r ON u.id_rol     = r.id_rol
WHERE s.activa = 1
  AND s.expira_en > NOW();


-- ============================================================
-- VISTA: Últimos 100 eventos del audit log (para dashboard)
-- ============================================================
CREATE VIEW v_audit_reciente AS
SELECT
    al.id_log,
    IFNULL(u.username, 'SISTEMA')   AS usuario,
    al.accion,
    al.modulo,
    al.tabla_afectada,
    al.id_registro,
    al.descripcion,
    al.resultado,
    al.ip_address,
    al.created_at
FROM audit_logs al
LEFT JOIN usuarios u ON al.id_usuario = u.id_usuario
ORDER BY al.created_at DESC
LIMIT 100;
