from database import Database
from psycopg2 import sql

def reset_sequences(db: Database, skip_tables=('usuarios','productos')):
    with db.get_cursor() as cur:
        cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type='BASE TABLE'
        """)
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            if t in skip_tables:
                print(f"Skipping {t}")
                continue
            cur.execute(sql.SQL('SELECT max(id) FROM {}').format(sql.Identifier(t)))
            v = cur.fetchone()[0]
            cur.execute("SELECT pg_get_serial_sequence(%s,%s)", (t,'id'))
            seq = cur.fetchone()[0]
            if not seq:
                print(f"No sequence for {t}, skipping")
                continue
            if v is None or v == 0:
                cur.execute(sql.SQL('SELECT setval(%s, %s, false)'), (seq, 1))
                print(f"Set {seq} -> 1 (empty table)")
            else:
                cur.execute(sql.SQL('SELECT setval(%s, %s, true)'), (seq, v))
                print(f"Set {seq} -> {v}")

if __name__ == '__main__':
    db = Database()
    reset_sequences(db)
    print('Secuencias reseteadas (excepto usuarios y productos).')
