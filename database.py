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
                cur.execute("""
                    SELECT 
                        v.id,           -- [0]
                        v.fecha,        -- [1]
                        v.total,        -- [2]
                        v.metodo_pago,  -- [3]
                        v.vendedor_id,  -- [4] (Es un UUID)
                        v.referencia,   -- [5]
                        c.nombre,       -- [6] (Viene de la tabla clientes)
                        c.cedula        -- [7] (Viene de la tabla clientes)
                    FROM public.ventas v
                    LEFT JOIN public.clientes c ON v.cliente_id = c.id
                    WHERE v.id = %s
                """, (venta_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error en consulta de venta: {e}")
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
                # Usamos RETURNING id para obtener el ID generado inmediatamente
                cur.execute("INSERT INTO clientes (nombre, cedula, telefono) VALUES (%s, %s, %s) RETURNING id", datos)
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error crear_cliente: {e}")
            return None

    def buscar_cliente(self, criterio):
        """Busca por ID exacto, Nombre parcial o Cédula parcial."""
        try:
            with self.get_cursor() as cur:
                # Si el buscador está vacío, traemos los últimos 50 clientes registrados
                if not criterio:
                    cur.execute("SELECT id, nombre, cedula, telefono FROM clientes ORDER BY id DESC LIMIT 50")
                    return cur.fetchall()

                # Definimos el patrón de búsqueda para ILIKE
                patron = f"%{criterio}%"
                
                # Intentamos ver si el criterio es un ID numérico exacto
                id_busqueda = None
                if criterio.isdigit():
                    id_busqueda = int(criterio)

                # Ejecutamos una sola consulta que busque en todos los campos importantes
                cur.execute("""
                    SELECT id, nombre, cedula, telefono 
                    FROM clientes 
                    WHERE id = %s OR nombre ILIKE %s OR cedula ILIKE %s 
                    ORDER BY nombre ASC 
                    LIMIT 20
                """, (id_busqueda, patron, patron))
                
                return cur.fetchall()
        except Exception as e:
            print(f"Error buscar_cliente: {e}")
            return []

    def get_cliente_por_id(self, cliente_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, nombre, cedula, telefono FROM clientes WHERE id = %s", (cliente_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error get_cliente_por_id: {e}")
            return None
        
    def obtener_detalle_ventas_por_fecha(self, fecha):
        """Retorna todas las ventas de un día específico con sus detalles."""
        try:
            with self.get_cursor() as cur:
                # Traemos: ID, Hora, Total, Método, Referencia y Vendedor
                cur.execute("""
                    SELECT v.id, v.fecha::time, v.total, v.metodo_pago, v.referencia, u.username
                    FROM ventas v
                    LEFT JOIN usuarios u ON v.vendedor_id = u.id
                    WHERE v.fecha::date = %s
                    ORDER BY v.id DESC
                """, (fecha,))
                return cur.fetchall()
        except Exception as e:
            print(f"Error en reporte detallado: {e}")
            return []
    
    def obtener_resumen_diario(self):
        try:
            with self.get_cursor() as cur:
                # Cambia "ventas" por "venta" si ese es el nombre de tu tabla
                cur.execute("""
                    SELECT metodo_pago, SUM(total) as total_ventas, COUNT(id) as num_operaciones
                    FROM ventas
                    WHERE fecha::date = CURRENT_DATE
                    GROUP BY metodo_pago
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Error resumen: {e}")
            return []

    def obtener_auditoria_diaria(self, fecha):
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT 
                        v.id,
                        v.fecha::time,
                        v.total,
                        v.metodo_pago,
                        u.nombre as cajero,
                        c.nombre as cliente
                    FROM public.ventas v
                    LEFT JOIN public.clientes c ON v.cliente_id = c.id
                    -- AGREGAMOS ::text en ambos lados para que la comparación sea válida
                    LEFT JOIN public.usuarios u ON v.vendedor_id::text = u.id::text
                    WHERE v.fecha::date = %s 
                    ORDER BY v.id DESC
                """, (fecha,))
                return cur.fetchall()
        except Exception as e:
            print(f"Error auditoria con cajero: {e}")
            return []
        
    def obtener_resumen_por_fecha(self, fecha):
        """Calcula el resumen de ventas para una fecha específica."""
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT metodo_pago, SUM(total) as total_ventas, COUNT(id) as num_operaciones
                    FROM ventas
                    WHERE fecha::date = %s
                    GROUP BY metodo_pago
                """, (fecha,))
                return cur.fetchall()
        except Exception as e:
            print(f"Error resumen por fecha: {e}")
            return []
    
    def obtener_cierre_cajero(self, usuario_id, fecha=None):
        if not fecha:
            from datetime import date
            fecha = date.today()
            
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT 
                        metodo_pago, 
                        SUM(total) as monto, 
                        COUNT(id) as cantidad
                    FROM public.ventas
                    WHERE vendedor_id::text = %s AND fecha::date = %s
                    GROUP BY metodo_pago
                """, (str(usuario_id), fecha))
                return cur.fetchall()
        except Exception as e:
            print(f"Error calculando cierre: {e}")
            return []
    
# .\.venv\Scripts\activate.bat