import hashlib
from database import Database

db = Database()

username = 'Admin'       # cámbialo si ya existe
password = 'Postgres'    # pon la contraseña que quieras
nombre = 'Cajero Prueba'
rol = 'cajero'

pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

with db.get_cursor() as cur:
    cur.execute(
        "INSERT INTO usuarios (username, nombre, password_hash, rol) VALUES (%s, %s, %s, %s) RETURNING id",
        (username, nombre, pw_hash, rol)
    )
    new_id = cur.fetchone()[0]

print('Usuario creado id =', new_id)