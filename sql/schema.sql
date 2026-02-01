-- Schema básico para MyMPos (PostgreSQL)

-- Usuarios (opcional)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200),
    password_hash VARCHAR(200),
    rol VARCHAR(50) DEFAULT 'cajero',
    creado_en TIMESTAMP DEFAULT NOW()
);

-- Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    rif VARCHAR(50),
    telefono VARCHAR(50),
    email VARCHAR(120),
    direccion TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);

-- Configuración (clave/valor)
CREATE TABLE IF NOT EXISTS configuracion (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insertar tasa inicial si no existe
INSERT INTO configuracion (clave, valor) VALUES ('tasa_bcv', '1.00')
ON CONFLICT (clave) DO NOTHING;

-- Productos (ajustado a tu esquema existente)
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo_barras VARCHAR(120) UNIQUE NOT NULL,
    nombre VARCHAR(300) NOT NULL,
    precio_compra NUMERIC(12,2) DEFAULT 0.00,
    precio_venta NUMERIC(12,2) DEFAULT 0.00,
    stock INTEGER DEFAULT 0,
    stock_minimo INTEGER DEFAULT 0,
    categoria VARCHAR(150),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cajas (apertura / cierre)
CREATE TABLE IF NOT EXISTS cajas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    apertura TIMESTAMP DEFAULT NOW(),
    cierre TIMESTAMP,
    monto_apertura NUMERIC(12,2) DEFAULT 0.00,
    monto_cierre NUMERIC(12,2),
    estado VARCHAR(20) DEFAULT 'abierta'
);

-- Ventas (ajustado a tu modelo: campo "total" y "metodo_pago" y vendedor_id)
CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total NUMERIC(12,2) DEFAULT 0.00,
    metodo_pago VARCHAR(50) DEFAULT 'efectivo',
    vendedor_id UUID,
    cliente_id INTEGER REFERENCES clientes(id),
    caja_id INTEGER REFERENCES cajas(id),
    estado VARCHAR(20) DEFAULT 'pagada'
);

-- Detalle de ventas (tu tabla `detalle_ventas`)
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos(id),
    cantidad INTEGER DEFAULT 1,
    precio_unitario NUMERIC(12,2) DEFAULT 0.00,
    subtotal NUMERIC(12,2) DEFAULT 0.00
);

-- Índices de ayuda
CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo_barras);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);

-- Fin del schema
