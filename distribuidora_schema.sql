-- ============================================================
--  SISTEMA DE GESTIÓN - DISTRIBUIDORA DE PRODUCTOS ALIMENTICIOS
--  Modelo de Base de Datos - MySQL 8.0
--  Versión: 1.0
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- ============================================================
-- 1. TABLA: categorias
--    Clasifica los productos (Lácteos, Granos, Bebidas, etc.)
-- ============================================================
CREATE TABLE categorias (
    id_categoria     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(100)  NOT NULL,
    descripcion      VARCHAR(255),
    estado           TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1=Activo, 0=Inactivo',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 2. TABLA: unidades_medida
--    Unidades para medir productos (kg, litro, unidad, caja, etc.)
-- ============================================================
CREATE TABLE unidades_medida (
    id_unidad        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre           VARCHAR(50)   NOT NULL,
    abreviatura      VARCHAR(10)   NOT NULL,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 3. TABLA: proveedores
--    Empresas o personas que suministran los productos
-- ============================================================
CREATE TABLE proveedores (
    id_proveedor     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    razon_social     VARCHAR(150)  NOT NULL,
    ruc_cedula       VARCHAR(20)   UNIQUE,
    nombre_contacto  VARCHAR(100),
    telefono         VARCHAR(20),
    celular          VARCHAR(20),
    email            VARCHAR(100),
    direccion        VARCHAR(255),
    ciudad           VARCHAR(80),
    estado           TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1=Activo, 0=Inactivo',
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 4. TABLA: clientes
--    Personas o empresas que compran los productos
-- ============================================================
CREATE TABLE clientes (
    id_cliente       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tipo_cliente     ENUM('NATURAL','JURIDICA') NOT NULL DEFAULT 'NATURAL',
    nombres          VARCHAR(100)  NOT NULL,
    apellidos        VARCHAR(100),
    razon_social     VARCHAR(150)  COMMENT 'Para personas jurídicas',
    cedula_ruc       VARCHAR(20)   UNIQUE,
    telefono         VARCHAR(20),
    celular          VARCHAR(20),
    email            VARCHAR(100),
    direccion        VARCHAR(255),
    ciudad           VARCHAR(80),
    limite_credito   DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Monto máximo de crédito autorizado',
    estado           TINYINT(1)    NOT NULL DEFAULT 1,
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 5. TABLA: productos
--    Catálogo maestro de productos disponibles
-- ============================================================
CREATE TABLE productos (
    id_producto      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_categoria     INT UNSIGNED  NOT NULL,
    id_unidad        INT UNSIGNED  NOT NULL,
    codigo           VARCHAR(50)   UNIQUE NOT NULL COMMENT 'Código interno o código de barras',
    nombre           VARCHAR(150)  NOT NULL,
    descripcion      TEXT,
    precio_compra    DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Costo de adquisición más reciente',
    precio_venta     DECIMAL(10,2) NOT NULL COMMENT 'Precio de venta al público',
    stock_actual     DECIMAL(10,3) NOT NULL DEFAULT 0.000 COMMENT 'Cantidad actual en inventario',
    stock_minimo     DECIMAL(10,3) NOT NULL DEFAULT 0.000 COMMENT 'Punto de reorden',
    aplica_iva       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1=Grava IVA, 0=Exento',
    porcentaje_iva   DECIMAL(5,2)  NOT NULL DEFAULT 15.00,
    estado           TINYINT(1)    NOT NULL DEFAULT 1,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_prod_categoria FOREIGN KEY (id_categoria) REFERENCES categorias(id_categoria),
    CONSTRAINT fk_prod_unidad    FOREIGN KEY (id_unidad)    REFERENCES unidades_medida(id_unidad)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 6. TABLA: compras
--    Cabecera de cada compra realizada a un proveedor
-- ============================================================
CREATE TABLE compras (
    id_compra        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_proveedor     INT UNSIGNED  NOT NULL,
    numero_factura   VARCHAR(50)   COMMENT 'Número de factura del proveedor',
    fecha_compra     DATE          NOT NULL,
    subtotal         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_iva        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total            DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado           ENUM('PENDIENTE','RECIBIDA','ANULADA') NOT NULL DEFAULT 'RECIBIDA',
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_compra_proveedor FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 7. TABLA: compras_detalle
--    Detalle de productos en cada compra (genera entrada en inventario)
-- ============================================================
CREATE TABLE compras_detalle (
    id_detalle_compra INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_compra         INT UNSIGNED  NOT NULL,
    id_producto       INT UNSIGNED  NOT NULL,
    cantidad          DECIMAL(10,3) NOT NULL,
    precio_unitario   DECIMAL(10,2) NOT NULL,
    subtotal          DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detcompra_compra   FOREIGN KEY (id_compra)   REFERENCES compras(id_compra),
    CONSTRAINT fk_detcompra_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 8. TABLA: pedidos
--    Solicitudes de clientes antes de convertirse en venta
-- ============================================================
CREATE TABLE pedidos (
    id_pedido        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_cliente       INT UNSIGNED  NOT NULL,
    fecha_pedido     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega    DATE          COMMENT 'Fecha acordada de entrega',
    estado           ENUM('PENDIENTE','CONFIRMADO','EN_PROCESO','ENTREGADO','CANCELADO') NOT NULL DEFAULT 'PENDIENTE',
    canal_origen     ENUM('WHATSAPP','PRESENCIAL','TELEFONO','OTRO') DEFAULT 'WHATSAPP',
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pedido_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 9. TABLA: pedidos_detalle
--    Líneas de productos dentro de un pedido
-- ============================================================
CREATE TABLE pedidos_detalle (
    id_detalle_pedido INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_pedido         INT UNSIGNED  NOT NULL,
    id_producto       INT UNSIGNED  NOT NULL,
    cantidad          DECIMAL(10,3) NOT NULL,
    precio_unitario   DECIMAL(10,2) NOT NULL COMMENT 'Precio acordado al momento del pedido',
    subtotal          DECIMAL(10,2) NOT NULL,
    CONSTRAINT fk_detpedido_pedido   FOREIGN KEY (id_pedido)   REFERENCES pedidos(id_pedido),
    CONSTRAINT fk_detpedido_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 10. TABLA: ventas
--     Cabecera de cada venta (al contado o a crédito)
--     Puede originarse de un pedido o ser directa
-- ============================================================
CREATE TABLE ventas (
    id_venta         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_cliente       INT UNSIGNED  NOT NULL,
    id_pedido        INT UNSIGNED  NULL COMMENT 'Pedido que origina la venta (opcional)',
    numero_venta     VARCHAR(20)   UNIQUE NOT NULL COMMENT 'Número correlativo de venta',
    fecha_venta      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipo_venta       ENUM('CONTADO','CREDITO') NOT NULL DEFAULT 'CONTADO',
    subtotal         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    descuento        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_iva        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total            DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado           ENUM('ACTIVA','ANULADA') NOT NULL DEFAULT 'ACTIVA',
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_venta_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    CONSTRAINT fk_venta_pedido  FOREIGN KEY (id_pedido)  REFERENCES pedidos(id_pedido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 11. TABLA: ventas_detalle
--     Líneas de productos vendidos en cada venta
--     (genera movimiento de salida en inventario)
-- ============================================================
CREATE TABLE ventas_detalle (
    id_detalle_venta INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_venta         INT UNSIGNED  NOT NULL,
    id_producto      INT UNSIGNED  NOT NULL,
    cantidad         DECIMAL(10,3) NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL,
    descuento_linea  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    subtotal         DECIMAL(10,2) NOT NULL,
    aplica_iva       TINYINT(1)    NOT NULL DEFAULT 0,
    valor_iva        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_detventa_venta    FOREIGN KEY (id_venta)    REFERENCES ventas(id_venta),
    CONSTRAINT fk_detventa_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 12. TABLA: facturas
--     Documento fiscal asociado a una venta
-- ============================================================
CREATE TABLE facturas (
    id_factura       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_venta         INT UNSIGNED  NOT NULL UNIQUE,
    numero_factura   VARCHAR(20)   UNIQUE NOT NULL,
    fecha_emision    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento DATE         COMMENT 'Para crédito: fecha máxima de pago',
    subtotal         DECIMAL(10,2) NOT NULL,
    descuento        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_iva        DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total            DECIMAL(10,2) NOT NULL,
    estado           ENUM('EMITIDA','PAGADA','VENCIDA','ANULADA') NOT NULL DEFAULT 'EMITIDA',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_factura_venta FOREIGN KEY (id_venta) REFERENCES ventas(id_venta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 13. TABLA: cuentas_por_cobrar
--     Control del saldo pendiente por cada venta a crédito
-- ============================================================
CREATE TABLE cuentas_por_cobrar (
    id_cuenta        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_venta         INT UNSIGNED  NOT NULL UNIQUE,
    id_cliente       INT UNSIGNED  NOT NULL,
    monto_total      DECIMAL(10,2) NOT NULL COMMENT 'Deuda original',
    monto_pagado     DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    saldo_pendiente  DECIMAL(10,2) NOT NULL COMMENT 'monto_total - monto_pagado',
    fecha_vencimiento DATE         NOT NULL,
    estado           ENUM('PENDIENTE','PAGADA_PARCIAL','PAGADA','VENCIDA') NOT NULL DEFAULT 'PENDIENTE',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cxc_venta   FOREIGN KEY (id_venta)   REFERENCES ventas(id_venta),
    CONSTRAINT fk_cxc_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 14. TABLA: abonos
--     Registra cada pago parcial o total de una cuenta por cobrar
-- ============================================================
CREATE TABLE abonos (
    id_abono         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_cuenta        INT UNSIGNED  NOT NULL,
    id_cliente       INT UNSIGNED  NOT NULL,
    monto_abono      DECIMAL(10,2) NOT NULL,
    fecha_abono      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    forma_pago       ENUM('EFECTIVO','TRANSFERENCIA','CHEQUE','OTRO') NOT NULL DEFAULT 'EFECTIVO',
    referencia       VARCHAR(100)  COMMENT 'Número de transferencia, cheque, etc.',
    notas            TEXT,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_abono_cuenta  FOREIGN KEY (id_cuenta)  REFERENCES cuentas_por_cobrar(id_cuenta),
    CONSTRAINT fk_abono_cliente FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 15. TABLA: movimientos_inventario
--     Trazabilidad completa de cada entrada y salida de stock
-- ============================================================
CREATE TABLE movimientos_inventario (
    id_movimiento    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_producto      INT UNSIGNED  NOT NULL,
    tipo_movimiento  ENUM('ENTRADA','SALIDA','AJUSTE_POSITIVO','AJUSTE_NEGATIVO') NOT NULL,
    origen           ENUM('COMPRA','VENTA','AJUSTE_MANUAL','DEVOLUCION') NOT NULL,
    id_referencia    INT UNSIGNED  COMMENT 'ID del comprobante origen (compra, venta, etc.)',
    cantidad         DECIMAL(10,3) NOT NULL,
    stock_anterior   DECIMAL(10,3) NOT NULL,
    stock_posterior  DECIMAL(10,3) NOT NULL,
    costo_unitario   DECIMAL(10,2) COMMENT 'Costo para movimientos de entrada',
    fecha_movimiento DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notas            TEXT,
    CONSTRAINT fk_movinv_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- ÍNDICES ADICIONALES PARA RENDIMIENTO
-- ============================================================
CREATE INDEX idx_clientes_cedula      ON clientes(cedula_ruc);
CREATE INDEX idx_clientes_estado      ON clientes(estado);
CREATE INDEX idx_productos_codigo     ON productos(codigo);
CREATE INDEX idx_productos_categoria  ON productos(id_categoria);
CREATE INDEX idx_ventas_fecha         ON ventas(fecha_venta);
CREATE INDEX idx_ventas_cliente       ON ventas(id_cliente);
CREATE INDEX idx_ventas_tipo          ON ventas(tipo_venta);
CREATE INDEX idx_cxc_cliente          ON cuentas_por_cobrar(id_cliente);
CREATE INDEX idx_cxc_estado           ON cuentas_por_cobrar(estado);
CREATE INDEX idx_abonos_cuenta        ON abonos(id_cuenta);
CREATE INDEX idx_abonos_fecha         ON abonos(fecha_abono);
CREATE INDEX idx_movinv_producto      ON movimientos_inventario(id_producto);
CREATE INDEX idx_movinv_fecha         ON movimientos_inventario(fecha_movimiento);
CREATE INDEX idx_pedidos_cliente      ON pedidos(id_cliente);
CREATE INDEX idx_pedidos_estado       ON pedidos(estado);

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================
-- TRIGGERS: Automatización de lógica de negocio
-- ============================================================

-- Trigger: Actualizar inventario y cuentas por cobrar tras confirmar una venta
DELIMITER $$

-- Actualiza stock al insertar detalle de venta
CREATE TRIGGER trg_after_insert_ventas_detalle
AFTER INSERT ON ventas_detalle
FOR EACH ROW
BEGIN
    DECLARE v_stock_anterior DECIMAL(10,3);
    SELECT stock_actual INTO v_stock_anterior FROM productos WHERE id_producto = NEW.id_producto;

    -- Reducir stock
    UPDATE productos
    SET stock_actual = stock_actual - NEW.cantidad
    WHERE id_producto = NEW.id_producto;

    -- Registrar movimiento
    INSERT INTO movimientos_inventario
        (id_producto, tipo_movimiento, origen, id_referencia, cantidad, stock_anterior, stock_posterior)
    VALUES
        (NEW.id_producto, 'SALIDA', 'VENTA', NEW.id_venta, NEW.cantidad,
         v_stock_anterior, v_stock_anterior - NEW.cantidad);
END$$

-- Actualiza stock al insertar detalle de compra
CREATE TRIGGER trg_after_insert_compras_detalle
AFTER INSERT ON compras_detalle
FOR EACH ROW
BEGIN
    DECLARE v_stock_anterior DECIMAL(10,3);
    SELECT stock_actual INTO v_stock_anterior FROM productos WHERE id_producto = NEW.id_producto;

    -- Aumentar stock
    UPDATE productos
    SET stock_actual    = stock_actual + NEW.cantidad,
        precio_compra   = NEW.precio_unitario
    WHERE id_producto = NEW.id_producto;

    -- Registrar movimiento
    INSERT INTO movimientos_inventario
        (id_producto, tipo_movimiento, origen, id_referencia, cantidad, stock_anterior, stock_posterior, costo_unitario)
    VALUES
        (NEW.id_producto, 'ENTRADA', 'COMPRA', NEW.id_compra, NEW.cantidad,
         v_stock_anterior, v_stock_anterior + NEW.cantidad, NEW.precio_unitario);
END$$

-- Actualiza saldo de cuenta por cobrar al registrar abono
CREATE TRIGGER trg_after_insert_abono
AFTER INSERT ON abonos
FOR EACH ROW
BEGIN
    DECLARE v_saldo_nuevo DECIMAL(10,2);

    UPDATE cuentas_por_cobrar
    SET monto_pagado    = monto_pagado + NEW.monto_abono,
        saldo_pendiente = saldo_pendiente - NEW.monto_abono,
        estado = CASE
            WHEN (saldo_pendiente - NEW.monto_abono) <= 0 THEN 'PAGADA'
            ELSE 'PAGADA_PARCIAL'
        END
    WHERE id_cuenta = NEW.id_cuenta;
END$$

DELIMITER ;


-- ============================================================
-- VISTAS ÚTILES
-- ============================================================

-- Vista: Resumen de deudas por cliente
CREATE VIEW v_deudas_clientes AS
SELECT
    c.id_cliente,
    CONCAT(c.nombres, ' ', IFNULL(c.apellidos,'')) AS cliente,
    c.celular,
    COUNT(cxc.id_cuenta)                           AS num_facturas_pendientes,
    SUM(cxc.monto_total)                           AS total_deuda_original,
    SUM(cxc.monto_pagado)                          AS total_abonado,
    SUM(cxc.saldo_pendiente)                       AS saldo_total_pendiente
FROM clientes c
JOIN cuentas_por_cobrar cxc ON c.id_cliente = cxc.id_cliente
WHERE cxc.estado IN ('PENDIENTE','PAGADA_PARCIAL','VENCIDA')
GROUP BY c.id_cliente, cliente, c.celular;

-- Vista: Productos con bajo stock
CREATE VIEW v_productos_bajo_stock AS
SELECT
    p.id_producto,
    p.codigo,
    p.nombre,
    c.nombre     AS categoria,
    p.stock_actual,
    p.stock_minimo,
    (p.stock_minimo - p.stock_actual) AS unidades_faltantes
FROM productos p
JOIN categorias c ON p.id_categoria = c.id_categoria
WHERE p.stock_actual <= p.stock_minimo
  AND p.estado = 1;

-- Vista: Historial de abonos por cliente
CREATE VIEW v_historial_abonos AS
SELECT
    a.id_abono,
    CONCAT(c.nombres,' ',IFNULL(c.apellidos,'')) AS cliente,
    v.numero_venta,
    f.numero_factura,
    a.fecha_abono,
    a.monto_abono,
    a.forma_pago,
    cxc.saldo_pendiente AS saldo_tras_abono
FROM abonos a
JOIN cuentas_por_cobrar cxc ON a.id_cuenta   = cxc.id_cuenta
JOIN clientes           c   ON a.id_cliente  = c.id_cliente
JOIN ventas             v   ON cxc.id_venta  = v.id_venta
LEFT JOIN facturas      f   ON f.id_venta    = v.id_venta
ORDER BY a.fecha_abono DESC;
