import os
import re
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        # Leer configuración desde variables de entorno
        self.config = {
            "host": os.getenv("DB_HOST", "aws-1-us-east-1.pooler.supabase.com"),
            "port": os.getenv("DB_PORT", "6543"),
            "database": os.getenv("DB_NAME", "postgres"),
            "user": os.getenv("DB_USER", "postgres.zkjxmopqdbwuqdnjnnji"),
            "password": os.getenv("DB_PASSWORD", "Megapostgrs")
        }

    @contextmanager
    def get_cursor(self):
        """Maneja la apertura y cierre automático de conexiones"""
        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

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

    def obtener_tasa_guardada(self):
        """Recupera la última tasa guardada para evitar errores sin internet"""
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv'")
                res = cur.fetchone()
                return float(res[0]) if res else 1.0
        except Exception as e:
            print(f"Error obtener_tasa_guardada: {e}")
            return 1.0

    def registrar_producto(self, datos):
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

    def buscar_productos_por_texto(self, texto, limit=12):
        try:
            with self.get_cursor() as cur:
                patron = f"%{texto}%"
                cur.execute(
                    "SELECT codigo_barras, nombre, precio_venta, stock FROM productos WHERE nombre ILIKE %s OR codigo_barras ILIKE %s ORDER BY nombre LIMIT %s",
                    (patron, patron, limit)
                )
                return cur.fetchall()
        except Exception as e:
            print(f"Error buscar_productos_por_texto: {e}")
            return []
        
    def buscar_producto_precios(self, criterio):
        query = "SELECT id, codigo_barras, nombre, precio_compra, precio_venta, stock FROM productos WHERE codigo_barras = %s OR nombre ILIKE %s LIMIT 1"
        try:
            with self.get_cursor() as cur:
                cur.execute(query, (criterio, f"%{criterio}%"))
                return cur.fetchall() # Retorna lista para mantener compatibilidad
        except Exception as e:
            print(f"Error: {e}")
            return []

    def obtener_productos_bajo_stock(self):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, codigo_barras, nombre, stock, stock_minimo FROM productos WHERE stock <= stock_minimo ORDER BY nombre")
                return cur.fetchall()
        except Exception as e:
            print(f"Error obtener_productos_bajo_stock: {e}")
            return []

    def descontar_stock(self, nombre_producto, cantidad):
        try:
            # Usamos el gestor de contexto que ya creaste
            with self.get_cursor() as cur:
                query = "UPDATE productos SET stock = stock - %s WHERE nombre = %s"
                cur.execute(query, (cantidad, nombre_producto))
                # No necesitas hacer commit aquí, tu get_cursor ya lo hace al salir del 'with'
                return True
        except Exception as e:
            print(f"Error al descontar stock: {e}")
            return False

    def get_producto_por_codigo(self, codigo):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT * FROM productos WHERE codigo_barras = %s", (codigo,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error get_producto_por_codigo: {e}")
            return None

    def crear_venta(self, datos_pago, vendedor_id, cliente_id, tasa):
        def _to_float(val):
            if val is None: return 0.0
            if isinstance(val, (int, float)): return float(val)
            s = str(val).strip()
            if s == "": return 0.0
            s = s.replace(' ', '').replace('$', '').replace('US$', '').replace('Bs.', '').replace('Bs', '')
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
            elif ',' in s:
                s = s.replace('.', '').replace(',', '.')
            s = re.sub(r'[^0-9\.\-]', '', s)
            try: return float(s)
            except: return 0.0

        try:
            with self.get_cursor() as cur:
                total = _to_float(datos_pago.get('total_usd', datos_pago.get('total', 0)))
                metodo = datos_pago.get('metodo') or 'mixto'
                query_venta = """
                    INSERT INTO ventas (vendedor_id, cliente_id, total, metodo_pago, fecha) 
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id
                """
                cur.execute(query_venta, (vendedor_id, cliente_id, total, metodo))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error crítico al registrar venta: {e}")
            return None

    def obtener_venta(self, venta_id):
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT v.id, v.fecha, v.total, v.metodo_pago, v.vendedor_id, v.referencia,
                           c.nombre as cliente_nombre, c.cedula as cliente_cedula,
                           u.nombre as vendedor_nombre
                    FROM public.ventas v
                    LEFT JOIN public.clientes c ON v.cliente_id = c.id
                    LEFT JOIN public.usuarios u ON v.vendedor_id::text = u.id::text
                    WHERE v.id = %s
                """, (venta_id,))
                return cur.fetchone()
        except Exception as e:
            print(f"Error al obtener venta: {e}")
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

    def insertar_detalle_venta(self, venta_id, producto_id, cantidad, precio_unitario, subtotal):
        try:
            with self.get_cursor() as cur:
                cur.execute(
                    "INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)",
                    (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                )
                return True
        except Exception as e:
            print(f"Error insertar_detalle_venta: {e}")
            return False
        
    # Agrega este método a tu clase Database en database.py
    def obtener_totales_cierre_hoy(self):
        """Consulta los totales de venta agrupados por método de pago para hoy"""
        query = """
            SELECT metodo_pago, SUM(total) as total_ventas
            FROM ventas 
            WHERE fecha::date = CURRENT_DATE 
            GROUP BY metodo_pago
        """
        try:
            with self.get_cursor() as cur:
                cur.execute(query)
                return cur.fetchall() # Esto devuelve una lista de tuplas [(metodo, total), ...]
        except Exception as e:
            print(f"Error en cierre: {e}")
            return []

    def authenticate_user(self, username, password_hash):
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT id, username, nombre, rol FROM usuarios WHERE username = %s AND password_hash = %s", (username, password_hash))
                return cur.fetchone()
        except Exception as e:
            print(f"Error authenticate_user: {e}")
            return None

    def crear_cliente(self, datos):
        try:
            with self.get_cursor() as cur:
                cur.execute("INSERT INTO clientes (nombre, cedula, telefono) VALUES (%s, %s, %s) RETURNING id", datos)
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error crear_cliente: {e}")
            return None

    def buscar_cliente(self, criterio):
        try:
            with self.get_cursor() as cur:
                if not criterio:
                    cur.execute("SELECT id, nombre, cedula, telefono FROM clientes ORDER BY id DESC LIMIT 50")
                    return cur.fetchall()
                patron = f"%{criterio}%"
                id_busqueda = int(criterio) if criterio.isdigit() else None
                cur.execute("""
                    SELECT id, nombre, cedula, telefono FROM clientes 
                    WHERE id = %s OR nombre ILIKE %s OR cedula ILIKE %s 
                    ORDER BY nombre ASC LIMIT 20
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
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT v.id, v.fecha::time, v.total, v.metodo_pago, v.referencia, u.username
                    FROM ventas v
                    LEFT JOIN usuarios u ON v.vendedor_id = u.id
                    WHERE v.fecha::date = %s ORDER BY v.id DESC
                """, (fecha,))
                return cur.fetchall()
        except Exception as e:
            print(f"Error en reporte detallado: {e}")
            return []

        
    def obtener_resumen_kpi(self, inicio, fin):
        """Devuelve el total vendido y la cantidad de operaciones para las tarjetas"""
        query = "SELECT SUM(total), COUNT(id) FROM public.ventas WHERE fecha::date BETWEEN %s AND %s"
        with self.get_cursor() as cur:
            cur.execute(query, (inicio, fin))
            return cur.fetchone() # Retorna (total, cantidad)

    def obtener_top_productos(self, inicio, fin):
        """Datos para la gráfica"""
        query = """
            SELECT p.nombre, SUM(dv.cantidad) as total 
            FROM public.detalle_ventas dv
            JOIN public.productos p ON dv.producto_id = p.id
            JOIN public.ventas v ON dv.venta_id = v.id
            WHERE v.fecha::date BETWEEN %s AND %s
            GROUP BY p.nombre ORDER BY total DESC LIMIT 5
        """
        with self.get_cursor() as cur:
            cur.execute(query, (inicio, fin))
            return cur.fetchall()

    def obtener_cierre_cajero(self, usuario_id, fecha=None):
        if not fecha:
            from datetime import date
            fecha = date.today()
        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT metodo_pago, SUM(total) as monto, COUNT(id) as cantidad
                    FROM public.ventas WHERE vendedor_id::text = %s AND fecha::date = %s
                    GROUP BY metodo_pago
                """, (str(usuario_id), fecha))
                return cur.fetchall()
        except Exception as e:
            print(f"Error calculando cierre: {e}")
            return []

    def registrar_nuevo_usuario(self, username, nombre, password_hash, rol):
        try:
            with self.get_cursor() as cur:
                query = "INSERT INTO usuarios (username, nombre, password_hash, rol) VALUES (%s, %s, %s, %s)"
                cur.execute(query, (username, nombre, password_hash, rol))
                return True
        except Exception as e:
            print(f"Error al registrar usuario: {e}")
            return False

    def consultar_producto_rapido(self, busqueda):
        # 1. Agregamos LIMIT 10 para no saturar la interfaz con 100 resultados
        # 2. Priorizamos que empiece por el texto (más rápido con índices)
        query = """
            SELECT nombre, precio_venta, stock 
            FROM productos 
            WHERE nombre ILIKE %s 
            OR codigo_barras = %s 
            ORDER BY nombre ASC 
            LIMIT 10
        """
        try:
            with self.get_cursor() as cur:
                # Usamos busqueda% (sin el primer %) para que sea ultra rápido
                cur.execute(query, (f"{busqueda}%", busqueda))
                return cur.fetchall()
        except Exception as e:
            print(f"Error en consulta rápida: {e}")
            return []

    def registrar_item_venta(self, venta_id, producto_nombre, cantidad, precio_unitario, subtotal):
        query_item = """
            INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, (SELECT id FROM productos WHERE nombre = %s LIMIT 1), %s, %s, %s)
        """
        query_stock = "UPDATE productos SET stock = stock - %s WHERE nombre = %s"
        try:
            with self.get_cursor() as cur:
                cur.execute(query_item, (venta_id, producto_nombre, cantidad, precio_unitario, subtotal))
                cur.execute(query_stock, (cantidad, producto_nombre))
                return True
        except Exception as e:
            print(f"Error al registrar detalle: {e}")
            return False
# .\.venv\Scripts\activate.bat