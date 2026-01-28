-- Migration: añadir columna referencia a ventas si no existe
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS referencia VARCHAR(200);
