-- reset_sequences_safe.sql
-- Ajusta las sequences para que queden coherentes con max(id) de cada tabla.
-- No tocar las tablas 'usuarios' ni 'productos'.
DO $$
DECLARE
  t RECORD;
  v_max bigint;
  seq_name text;
BEGIN
  FOR t IN
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type='BASE TABLE'
  LOOP
    IF t.table_name NOT IN ('usuarios','productos') THEN
      EXECUTE format('SELECT max(id) FROM %I', t.table_name) INTO v_max;
      seq_name := pg_get_serial_sequence(t.table_name, 'id');
      IF seq_name IS NULL THEN
        -- no hay sequence para esta tabla (no serial/identity), saltar
        CONTINUE;
      END IF;
      IF v_max IS NULL OR v_max = 0 THEN
        -- si no hay filas, inicializamos la sequence en 1 y marcamos is_called = false
        EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
      ELSE
        -- si hay filas, fijamos la sequence al máximo actual (nextval dará max+1)
        EXECUTE format('SELECT setval(%L, %s, true)', seq_name, v_max);
      END IF;
    END IF;
  END LOOP;
END;
$$;
