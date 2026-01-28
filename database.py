import psycopg2
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.config = {
            "host": "aws-1-us-east-1.pooler.supabase.com",
            "port": "6543",
            "database": "postgres",
            "user": "postgres.zkjxmopqdbwuqdnjnnji",
            "password": "Megapostgrs"
        }

    @contextmanager
    def get_cursor(self):
        """Maneja la apertura y cierre automático de conexiones"""
        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def buscar_producto(self, criterio):
        try:
            with self.get_cursor() as cur:
                query = """SELECT codigo_barras, nombre, precio_venta, stock 
                           FROM productos 
                           WHERE codigo_barras = %s OR nombre ILIKE %s"""
                cur.execute(query, (criterio, f"%{criterio}%"))
                return cur.fetchone()
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return None

    # --- NUEVA FUNCIÓN PARA EL VALERY ---
    def obtener_tasa_guardada(self):
        """Recupera la última tasa guardada para evitar errores sin internet"""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv'")
                res = cur.fetchone()
                return float(res[0]) if res else 1.0
        except:
            return 1.0

    # Métodos CRUD básicos usados por la interfaz
    def registrar_producto(self, datos):
        """datos = (codigo_barras, nombre, precio_compra, precio_venta, stock, stock_minimo, categoria)"""
        try:
            with self.get_cursor() as cur:
                query = ("INSERT INTO productos (codigo_barras, nombre, precio_compra, precio_venta, stock, stock_minimo, categoria)"
                         " VALUES (%s, %s, %s, %s, %s, %s, %s)")
                cur.execute(query, datos)
                return True
        except Exception as e:
            print(f"Error registrar_producto: {e}")
            return False

    def actualizar_producto(self, datos):
        """datos = (nombre, precio_compra, precio_venta, stock, stock_minimo, categoria, codigo_barras)"""
        try:
            with self.get_cursor() as cur:
                query = ("UPDATE productos SET nombre=%s, precio_compra=%s, precio_venta=%s, stock=%s, stock_minimo=%s, categoria=%s"
                         " WHERE codigo_barras=%s")
                cur.execute(query, datos)
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error actualizar_producto: {e}")
            return False

    def eliminar_producto(self, codigo):
        try:
            with self.get_cursor() as cur:
                cur.execute("DELETE FROM productos WHERE codigo_barras = %s", (codigo,))
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error eliminar_producto: {e}")
            return False

    def obtener_todos_los_productos(self):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT * FROM productos ORDER BY nombre")
                return cur.fetchall()
        except Exception as e:
            print(f"Error obtener_todos_los_productos: {e}")
            return []

    def obtener_productos_bajo_stock(self):
        """Devuelve lista de productos cuyo stock es menor o igual a stock_minimo.
        Retorna filas completas de la tabla productos.
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, codigo_barras, nombre, stock, stock_minimo FROM productos WHERE stock <= stock_minimo ORDER BY nombre")
                return cur.fetchall()
        except Exception as e:
            print(f"Error obtener_productos_bajo_stock: {e}")
            return []

    def restar_stock(self, codigo, cantidad):
        try:
            with self.get_cursor() as cur:
                cur.execute("UPDATE productos SET stock = stock - %s WHERE codigo_barras = %s", (cantidad, codigo))
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error restar_stock: {e}")
            return False

    def get_producto_por_codigo(self, codigo):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT * FROM productos WHERE codigo_barras = %s", (codigo,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error get_producto_por_codigo: {e}")
            return None

    def crear_venta(self, carrito, usuario_id=None, cliente_id=None, metodo_pago='efectivo', caja_id=None, referencia=None):
        """
        carrito: lista de tuplas (codigo_barras, nombre, precio) o (codigo_barras, nombre, precio, cantidad)
        Agrupa por codigo, inserta venta y detalle_ventas, y actualiza stock.
        Retorna id de la venta si OK, o None si falla.
        """
        try:
            # 1) Agrupar items por codigo. Soportamos varias estructuras:
            # - lista de tuplas (codigo, nombre, precio) o (codigo, nombre, precio, cantidad)
            # - diccionario {codigo: {nombre, precio, cantidad, subtotal}}
            items = {}
            if isinstance(carrito, dict):
                for codigo, v in carrito.items():
                    items[codigo] = {
                        'nombre': v.get('nombre'),
                        'precio': float(v.get('precio')),
                        'cantidad': int(v.get('cantidad', 1)),
                        'subtotal': float(v.get('precio')) * int(v.get('cantidad', 1))
                    }
            else:
                for it in carrito:
                    if isinstance(it, dict):
                        codigo = it.get('codigo')
                        nombre = it.get('nombre')
                        precio = float(it.get('precio'))
                        cantidad = int(it.get('cantidad', 1))
                    else:
                        if len(it) == 4:
                            codigo, nombre, precio, cantidad = it
                        else:
                            codigo, nombre, precio = it
                            cantidad = 1
                        precio = float(precio)

                    if codigo in items:
                        items[codigo]['cantidad'] += cantidad
                        items[codigo]['subtotal'] += precio * cantidad
                    else:
                        items[codigo] = {
                            'nombre': nombre,
                            'precio': precio,
                            'cantidad': cantidad,
                            'subtotal': precio * cantidad
                        }

            total = sum(v['subtotal'] for v in items.values())

            # 2) Insertar venta (intentamos variantes según columnas disponibles)
            with self.get_cursor() as cur:
                try:
                    # intentamos insertar incluyendo referencia si fue provista
                    if referencia is not None:
                        cur.execute(
                            "INSERT INTO ventas (total, metodo_pago, vendedor_id, cliente_id, caja_id, referencia) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                            (total, metodo_pago, usuario_id, cliente_id, caja_id, referencia)
                        )
                    else:
                        cur.execute(
                            "INSERT INTO ventas (total, metodo_pago, vendedor_id, cliente_id, caja_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                            (total, metodo_pago, usuario_id, cliente_id, caja_id)
                        )
                except Exception:
                    # La transacción puede quedar abortada; hacemos rollback y probamos variantes
                    try:
                        cur.connection.rollback()
                    except Exception:
                        pass
                    # variante: sin cliente_id y/o caja_id
                    try:
                        if referencia is not None:
                            cur.execute(
                                "INSERT INTO ventas (total, metodo_pago, vendedor_id, referencia) VALUES (%s, %s, %s, %s) RETURNING id",
                                (total, metodo_pago, usuario_id, referencia)
                            )
                        else:
                            cur.execute(
                                "INSERT INTO ventas (total, metodo_pago, vendedor_id) VALUES (%s, %s, %s) RETURNING id",
                                (total, metodo_pago, usuario_id)
                            )
                    except Exception:
                        try:
                            cur.connection.rollback()
                        except Exception:
                            pass
                        # última variante: solo total
                        if referencia is not None:
                            # si la tabla no acepta referencia en columnas anteriores, intentamos crear solo total y referencia
                            try:
                                cur.execute(
                                    "INSERT INTO ventas (total, referencia) VALUES (%s, %s) RETURNING id",
                                    (total, referencia)
                                )
                            except Exception:
                                cur.execute(
                                    "INSERT INTO ventas (total) VALUES (%s) RETURNING id",
                                    (total,)
                                )
                        else:
                            cur.execute(
                                "INSERT INTO ventas (total) VALUES (%s) RETURNING id",
                                (total,)
                            )
                venta_id = cur.fetchone()[0]

                # 3) Insertar detalle_ventas y restar stock
                for codigo, v in items.items():
                    # obtener producto_id
                    cur.execute("SELECT id, stock FROM productos WHERE codigo_barras = %s", (codigo,))
                    prod = cur.fetchone()
                    producto_id = prod[0] if prod else None
                    current_stock = prod[1] if prod else None

                    cur.execute(
                        "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
                        (venta_id, producto_id, v['cantidad'], v['precio'], v['subtotal'])
                    )

                    if producto_id is not None:
                        # actualizar stock
                        cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (v['cantidad'], producto_id))

            return venta_id
        except Exception as e:
            print(f"Error crear_venta: {e}")
            return None

    def obtener_venta(self, venta_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error obtener_venta: {e}")
            return None

    def obtener_items_venta(self, venta_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT producto_id, cantidad, precio_unitario, subtotal FROM detalle_ventas WHERE venta_id = %s", (venta_id,))
                return cur.fetchall()
        except Exception as e:
            print(f"Error obtener_items_venta: {e}")
            return []

    def get_producto_por_id(self, producto_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error get_producto_por_id: {e}")
            return None

    # --- Usuarios y Clientes ---
    def authenticate_user(self, username, password_hash):
        """Retorna fila de usuario si las credenciales coinciden (password ya hasheado)."""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, username, nombre, rol FROM usuarios WHERE username = %s AND password_hash = %s", (username, password_hash))
                return cur.fetchone()
        except Exception as e:
            print(f"Error authenticate_user: {e}")
            return None

    def crear_cliente(self, datos):
        """datos = (nombre, cedula, telefono) -> retorna id o None"""
        try:
            with self.get_cursor() as cur:
                cur.execute("INSERT INTO clientes (nombre, cedula, telefono) VALUES (%s, %s, %s) RETURNING id", datos)
                return cur.fetchone()[0]
        except Exception as e:
            print(f"Error crear_cliente: {e}")
            return None

    def buscar_cliente(self, criterio):
        """Busca por id exacto o por nombre parcial."""
        try:
            with self.get_cursor() as cur:
                # si criterio es numérico, buscar por id primero
                try:
                    cid = int(criterio)
                    cur.execute("SELECT id, nombre, cedula, telefono FROM clientes WHERE id = %s", (cid,))
                    res = cur.fetchone()
                    if res:
                        return res
                except Exception:
                    pass

                cur.execute("SELECT id, nombre, cedula, telefono FROM clientes WHERE nombre ILIKE %s LIMIT 10", (f"%{criterio}%",))
                return cur.fetchall()
        except Exception as e:
            print(f"Error buscar_cliente: {e}")
            return None

    def get_cliente_por_id(self, cliente_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, nombre, cedula, telefono FROM clientes WHERE id = %s", (cliente_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error get_cliente_por_id: {e}")
            return None

# .\.venv\Scripts\activate.bat