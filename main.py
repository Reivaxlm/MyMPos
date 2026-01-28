import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, Menu
from tkinter import simpledialog
from database import Database
from bcv_tasa import obtener_tasa_bcv
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from datetime import datetime


class MyMPos(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        # Intentamos obtener la tasa; si falla, usar la tasa guardada o 1.0
        self.tasa = obtener_tasa_bcv() or self.db.obtener_tasa_guardada() or 1.0
        # carrito será un dict: {codigo: {'nombre', 'precio', 'cantidad', 'subtotal'}}
        self.carrito = {}

        self.title("MyMPos - Sistema de Control")
        self.geometry("1100x700")

        # --- 1. BARRA LATERAL (Menú Fijo) ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="MyMPos", font=("Roboto", 24, "bold"))
        self.lbl_logo.pack(pady=30)

        self.btn_pos = ctk.CTkButton(self.sidebar, text="VENTAS", command=self.mostrar_ventas)
        self.btn_pos.pack(pady=10, padx=20)

        self.btn_inv = ctk.CTkButton(self.sidebar, text="INVENTARIO", command=self.mostrar_inventario)
        self.btn_inv.pack(pady=10, padx=20)

        # --- 2. CONTENEDOR PRINCIPAL (Donde cambia el contenido) ---
        self.contenedor = ctk.CTkFrame(self, corner_radius=15)
        self.contenedor.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # usuario y cliente actuales
        self.current_user = None
        self.current_client = None

        # Pedir login antes de mostrar la interfaz
        self.after(100, self._prompt_login)
        # Mostrar Ventas por defecto
        self.mostrar_ventas()

    def _prompt_login(self):
        dlg = LoginDialog(self, self.db)
        self.wait_window(dlg)
        if getattr(dlg, 'result', None):
            self.current_user = dlg.result
            # Mostrar nombre en la sidebar
            name = self.current_user[2] if len(self.current_user) > 2 else self.current_user[1]
            self.lbl_logo.configure(text=f"MyMPos - {name}")
        else:
            # si no se logueó, cerramos la app
            self.destroy()

    def limpiar_pantalla(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def mostrar_ventas(self):
        self.limpiar_pantalla()
        
        # Cabecera Tasa
        ctk.CTkLabel(self.contenedor, text=f"Tasa BCV: {self.tasa:.2f} Bs.", text_color="yellow").pack(anchor="e", padx=20)

        # --- BUSCADOR VELOZ ---
        ctk.CTkLabel(self.contenedor, text="Buscar Producto:").pack(pady=(10,0))
        
        self.entry_buscar = ctk.CTkEntry(self.contenedor, width=500, height=40)
        self.entry_buscar.pack(pady=(5,0))
        
        # La lista ahora es FLOTANTE con .place()
        self.lista_sugerencias = tk.Listbox(
            self.contenedor, 
            width=70, 
            height=6,
            font=("Arial", 11),
            bg="#2b2b2b", 
            fg="white",
            borderwidth=1,
            relief="flat"
        )
        # IMPORTANTE: No usamos pack() aquí para que no ocupe espacio fijo.

        # Eventos para que funcione solo
        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)
        # En lugar de usar lambda e: ..., usa esto:
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.agregar_al_carrito)

        # Panel de pago visual (botones) — diseño centrado y unificado
        pago_frame = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        pago_frame.pack(fill='x', padx=20, pady=(0,8))

        # Contenedor centrado para métodos de pago
        pago_center = ctk.CTkFrame(pago_frame, fg_color="transparent")
        pago_center.pack(anchor='center', pady=4)

        payment_box = ctk.CTkFrame(pago_center, corner_radius=12, fg_color="#1f1f1f")
        payment_box.pack(padx=10, pady=6)
        payment_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(payment_box, text="Método de pago:", font=("Arial", 12, "bold")).pack(side='left', padx=(12,8))

        pagos_frame = ctk.CTkFrame(payment_box, fg_color="transparent")
        pagos_frame.pack(side='left', padx=6)

        # Botones de pago con estilo coherente
        self.payment_buttons = {}
        pagos = [("Efectivo","efectivo"), ("Tarjeta","tarjeta"), ("Biopago","biopago"), ("Transferencia","transferencia"), ("Pago Móvil","pago movil")]
        for text, key in pagos:
            btn = ctk.CTkButton(pagos_frame, text=text, width=110, height=36, fg_color="#2b2b2b", corner_radius=8, command=lambda k=key: self._set_metodo_pago(k))
            btn.pack(side='left', padx=6)
            self.payment_buttons[key] = btn

        # Área de referencia (creada pero oculta por defecto). Se mostrará centrada
        # debajo de los métodos de pago solo para transferencia/pago móvil.
        self.referencia_frame = ctk.CTkFrame(pago_center, fg_color="transparent")
        ctk.CTkLabel(self.referencia_frame, text="Referencia:", font=("Arial", 11)).pack(side='left', padx=(0,8))
        self.entry_referencia = ctk.CTkEntry(self.referencia_frame, width=420)
        self.entry_referencia.pack(side='left')
        # ocultar por defecto
        try:
            self.referencia_frame.pack_forget()
        except Exception:
            pass

        # Contenedor separado y centrado para Cliente (estilo similar)
        cliente_frame = ctk.CTkFrame(self.contenedor, corner_radius=12, fg_color="#1f1f1f")
        cliente_frame.pack(fill='x', padx=20, pady=(6,8))
        cliente_inner = ctk.CTkFrame(cliente_frame, fg_color="transparent")
        cliente_inner.pack(anchor='center', pady=8)
        ctk.CTkLabel(cliente_inner, text="Cliente:", font=("Arial", 12, "bold")).pack(side='left', padx=(0,8))
        self.btn_cliente = ctk.CTkButton(cliente_inner, text="Cliente: Consumidor Final", width=300, height=36, fg_color="#1976d2", command=self._seleccionar_cliente)
        self.btn_cliente.pack(side='left')

        # estado inicial de método
        self.metodo_seleccionado = 'efectivo'
        # marcar visualmente el seleccionado
        self._update_payment_buttons()

        # --- TABLA DEL CARRITO (Asegúrate de que las columnas coincidan) ---
        self.columnas_cart = ("cant", "producto", "precio", "subtotal")
        self.tabla_cart = ttk.Treeview(self.contenedor, columns=self.columnas_cart, show="headings", height=10)
        
        self.tabla_cart.heading("cant", text="CANT")
        self.tabla_cart.heading("producto", text="PRODUCTO")
        self.tabla_cart.heading("precio", text="PRECIO $")
        self.tabla_cart.heading("subtotal", text="SUBTOTAL $")
        
        # Ajustar anchos
        self.tabla_cart.column("cant", width=50, anchor="center")
        self.tabla_cart.column("producto", width=300)
        
        self.tabla_cart.pack(pady=10, fill="x", padx=20)

        # Menú eliminar (Clic derecho)
        self.menu_eliminar = Menu(self, tearoff=0)
        self.menu_eliminar.add_command(label="❌ Eliminar del carrito", command=self.eliminar_item_carrito)
        self.tabla_cart.bind("<Button-3>", self._mostrar_menu_contextual)

        # Total
        self.lbl_total = ctk.CTkLabel(self.contenedor, text="TOTAL: 0.00$", font=("Arial", 40, "bold"))
        self.lbl_total.pack(pady=10)

        self.btn_cobrar = ctk.CTkButton(self.contenedor, text="COBRAR VENTA", fg_color="green", height=45, command=self.finalizar_venta)
        self.btn_cobrar.pack(pady=10)

    def _filtrar_busqueda_combo(self, event):
        # Si presionas flecha abajo, vas a la lista
        if event.keysym == "Down":
            if self.lista_sugerencias.winfo_viewable():
                self.lista_sugerencias.focus_set()
                self.lista_sugerencias.selection_set(0)
            return

        texto = self.entry_buscar.get().strip().lower()
        
        if len(texto) >= 1:
            todos = self.db.obtener_todos_los_productos()
            relacionados = [
                f"{p[1]} | {p[2]}" 
                for p in todos 
                if texto in str(p[2]).lower() or texto in str(p[1]).lower()
            ]
            
            if relacionados:
                self.lista_sugerencias.delete(0, tk.END)
                for item in relacionados:
                    self.lista_sugerencias.insert(tk.END, item)
                
                # POSICIONAR LA LISTA JUSTO DEBAJO DEL ENTRY (Ajusta x e y si es necesario)
                # x=200 es un ejemplo, ponlo para que cuadre con tu entry_buscar
                self.lista_sugerencias.place(x=self.entry_buscar.winfo_x(), 
                                           y=self.entry_buscar.winfo_y() + 42)
                self.lista_sugerencias.lift() # La pone por encima de todo
            else:
                self.lista_sugerencias.place_forget()
        else:
            self.lista_sugerencias.place_forget()

    def agregar_desde_lista(self, event=None):
        # Si hay algo seleccionado en la lista, lo usamos. Si no, lo que esté escrito.
        try:
            seleccion = self.lista_sugerencias.get(self.lista_sugerencias.curselection())
        except:
            seleccion = self.entry_buscar.get()

        if seleccion:
            # Reutilizamos tu lógica de agregar al carrito (adaptada al nombre del widget)
            self._procesar_agregado(seleccion)
            
    def _procesar_agregado(self, texto):
        busqueda = texto.split(" | ")[0] if " | " in texto else texto
        resultado = self.db.buscar_producto(busqueda)
        if resultado:
            # Aquí va tu código de siempre de agregar_al_carrito...
            # (El de prod[0], prod[1], prod[2])
            # Al final, limpias todo:
            self.entry_buscar.delete(0, tk.END)
            self.lista_sugerencias.pack_forget()
            self._refrescar_vista_carrito()
    
    def eliminar_item_carrito(self):
        seleccion = self.tabla_cart.selection()
        if seleccion:
            valores = self.tabla_cart.item(seleccion, "values")
            nombre_prod = valores[1]
            
            # Borramos del diccionario buscando por el nombre
            codigo_a_eliminar = None
            for cod, info in self.carrito.items():
                if info['nombre'] == nombre_prod:
                    codigo_a_eliminar = cod
                    break
            
            if codigo_a_eliminar:
                del self.carrito[codigo_a_eliminar]
                self._refrescar_vista_carrito()

    def _mostrar_menu_contextual(self, event):
        # Selecciona la fila donde se hizo clic derecho
        item = self.tabla_cart.identify_row(event.y)
        if item:
            self.tabla_cart.selection_set(item)
            self.menu_eliminar.post(event.x_root, event.y_root)

    def mostrar_inventario(self):
        self.limpiar_pantalla()
        ctk.CTkLabel(self.contenedor, text="GESTIÓN INTEGRAL DE INVENTARIO", font=("Roboto", 22, "bold")).pack(pady=10)

        # Formulario Extendido (2 Filas)
        frame_form = ctk.CTkFrame(self.contenedor)
        frame_form.pack(fill="x", padx=20, pady=10)

        # Fila 1
        self.in_cod = ctk.CTkEntry(frame_form, placeholder_text="Código Barras", width=150)
        self.in_cod.grid(row=0, column=0, padx=5, pady=5)
        
        self.in_nom = ctk.CTkEntry(frame_form, placeholder_text="Nombre Producto", width=250)
        self.in_nom.grid(row=0, column=1, padx=5, pady=5)

        self.in_cat = ctk.CTkEntry(frame_form, placeholder_text="Categoría", width=120)
        self.in_cat.grid(row=0, column=2, padx=5, pady=5)

        # Fila 2
        self.in_pre_c = ctk.CTkEntry(frame_form, placeholder_text="Costo $", width=100)
        self.in_pre_c.grid(row=1, column=0, padx=5, pady=5)

        self.in_pre_v = ctk.CTkEntry(frame_form, placeholder_text="Venta $", width=100)
        self.in_pre_v.grid(row=1, column=1, padx=5, pady=5)

        self.in_sto = ctk.CTkEntry(frame_form, placeholder_text="Stock", width=80)
        self.in_sto.grid(row=1, column=2, padx=5, pady=5)

        self.in_min = ctk.CTkEntry(frame_form, placeholder_text="Mínimo", width=80)
        self.in_min.grid(row=1, column=3, padx=5, pady=5)

        # Botones de Acción
        frame_btns = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        frame_btns.pack(fill="x", padx=20)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="green", command=self.nuevo_producto).pack(side="left", padx=5)
        ctk.CTkButton(frame_btns, text="ACTUALIZAR", fg_color="orange", text_color="black", command=self.modificar_producto).pack(side="left", padx=5)
        ctk.CTkButton(frame_btns, text="ELIMINAR", fg_color="red", command=self.borrar_producto).pack(side="left", padx=5)

        # Agregué la coma que faltaba después de "categoria"
        self.tabla = ttk.Treeview(self.contenedor, 
                                  columns=("codigo_barras", "nombre", "categoria", "precio_compra", "precio_venta", "stock", "stock_minimo"), 
                                  show="headings")
        
        self.tabla.heading("codigo_barras", text="CÓDIGO")
        self.tabla.heading("nombre", text="NOMBRE")
        self.tabla.heading("categoria", text="CAT")
        self.tabla.heading("precio_compra", text="COSTO $")
        self.tabla.heading("precio_venta", text="VENTA $")
        self.tabla.heading("stock", text="STOCK")
        self.tabla.heading("stock_minimo", text="MÍN")
        
        # Ajustar ancho de columnas pequeñas
        self.tabla.column("precio_compra", width=80)
        self.tabla.column("precio_venta", width=80)
        self.tabla.column("stock", width=60)
        self.tabla.column("stock_minimo", width=60)

        self.tabla.pack(fill="both", expand=True, padx=20, pady=10)
        self.tabla.bind("<<TreeviewSelect>>", self.cargar_datos_en_campos)
        self.actualizar_tabla_inv()

    def cargar_datos_en_campos(self, event):
        seleccion = self.tabla.focus()
        if not seleccion: return
        v = self.tabla.item(seleccion, 'values')
        
        # Limpiar y llenar los 7 campos
        self.in_cod.delete(0, 'end'); self.in_cod.insert(0, v[0])
        self.in_nom.delete(0, 'end'); self.in_nom.insert(0, v[1])
        self.in_cat.delete(0, 'end'); self.in_cat.insert(0, v[2])
        self.in_pre_c.delete(0, 'end'); self.in_pre_c.insert(0, v[3])
        self.in_pre_v.delete(0, 'end'); self.in_pre_v.insert(0, v[4])
        self.in_sto.delete(0, 'end'); self.in_sto.insert(0, v[5])
        self.in_min.delete(0, 'end'); self.in_min.insert(0, v[6])

    def modificar_producto(self):
        try:
            # El orden debe coincidir con el UPDATE de database.py
            # nombre, precio_compra, precio_venta, stock, stock_minimo, categoria, codigo
            datos = (
                self.in_nom.get(),
                float(self.in_pre_c.get()),
                float(self.in_pre_v.get()),
                int(self.in_sto.get()),
                int(self.in_min.get()),
                self.in_cat.get(),
                self.in_cod.get() # El código es el filtro (WHERE)
            )
            
            if self.db.actualizar_producto(datos):
                messagebox.showinfo("Actualizado", "Cambios guardados con éxito.")
                self.actualizar_tabla_inv()
            else:
                messagebox.showerror("Error", "No se pudo actualizar.")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al actualizar: {e}")

    def borrar_producto(self):
        codigo = self.in_cod.get()
        if messagebox.askyesno("Confirmar", f"¿Seguro que quieres eliminar el código {codigo}?"):
            if self.db.eliminar_producto(codigo):
                self.actualizar_tabla_inv()
                messagebox.showinfo("Eliminado", "Producto borrado del sistema")

    def actualizar_tabla_inv(self):
        # 1. Limpiar la tabla antes de cargar
        for i in self.tabla.get_children(): 
            self.tabla.delete(i)
        
        # 2. Traer productos de la DB
        productos = self.db.obtener_todos_los_productos()
        
        for p in productos:
            # Los índices p[0], p[1], etc., dependen de cómo creaste la tabla en SQL.
            # Basado en tu configuración, el orden debería ser:
            # p[1] = codigo, p[2] = nombre, p[7] = categoria, 
            # p[3] = costo, p[4] = venta, p[5] = stock, p[6] = minimo
            
            self.tabla.insert("", "end", values=(
                p[1], # codigo_barras
                p[2], # nombre
                p[7], # categoria (ajusta el número si sale otra cosa)
                p[3], # precio_compra
                p[4], # precio_venta
                p[5], # stock
                p[6]  # stock_minimo
            ))

    def nuevo_producto(self):
        try:
            # Capturamos todos los campos del formulario
            datos = (
                self.in_cod.get(),     # codigo_barras
                self.in_nom.get(),     # nombre
                float(self.in_pre_c.get()), # precio_compra (Costo)
                float(self.in_pre_v.get()), # precio_venta (Venta)
                int(self.in_sto.get()),     # stock
                int(self.in_min.get()),     # stock_minimo
                self.in_cat.get()      # categoria
            )
            
            if self.db.registrar_producto(datos):
                messagebox.showinfo("Éxito", f"Producto '{self.in_nom.get()}' registrado.")
                self.limpiar_formulario_inv()
                self.actualizar_tabla_inv()
            else:
                messagebox.showerror("Error", "No se pudo registrar. ¿El código ya existe?")
        except ValueError:
            messagebox.showwarning("Dato Inválido", "Asegúrate de poner números en Costo, Venta y Stock.")

    def agregar_al_carrito(self, event=None): # Añade event=None para que acepte el clic
        try:
            # Obtener el índice de lo que clickeaste
            indices = self.lista_sugerencias.curselection()
            if indices:
                texto = self.lista_sugerencias.get(indices[0])
            else:
                # Si no hay clic, probar con lo que hay escrito en el cuadro
                texto = self.entry_buscar.get().strip()
        except Exception as e:
            print(f"Error al obtener selección: {e}")
            return

        if not texto or texto == "Sin resultados":
            return

        # --- Tu lógica de siempre de buscar en DB ---
        busqueda = texto.split(" | ")[0] if " | " in texto else texto
        resultado = self.db.buscar_producto(busqueda)
        
        if resultado:
            prod = resultado[0] if isinstance(resultado, list) else resultado
            codigo, nombre, precio = str(prod[0]), str(prod[1]), float(prod[2])
            
            if codigo in self.carrito:
                self.carrito[codigo]['cantidad'] += 1
                self.carrito[codigo]['subtotal'] = self.carrito[codigo]['cantidad'] * precio
            else:
                self.carrito[codigo] = {
                    'nombre': nombre, 
                    'precio': precio, 
                    'cantidad': 1, 
                    'subtotal': precio
                }
            
            # --- LIMPIEZA TOTAL ---
            self.entry_buscar.delete(0, tk.END)
            self.lista_sugerencias.delete(0, tk.END)
            self.lista_sugerencias.place_forget() # Ocultar la lista flotante
            self._refrescar_vista_carrito()
            self.entry_buscar.focus() # El cursor vuelve arriba para el siguiente producto

    def _refrescar_vista_carrito(self):
        # 1. Limpiar la tabla usando TU variable self.tabla_cart
        for item in self.tabla_cart.get_children():
            self.tabla_cart.delete(item)
        
        # 2. Llenar con los datos del diccionario carrito
        total_acumulado = 0
        for codigo, datos in self.carrito.items():
            # Calculamos el subtotal (puedes usar el que ya guardas o calcularlo aquí)
            subtotal = datos['precio'] * datos['cantidad']
            total_acumulado += subtotal
            
            # INSERTAR con tus columnas exactas: ("cant", "producto", "precio", "subtotal")
            self.tabla_cart.insert("", "end", values=(
                datos['cantidad'],
                datos['nombre'],
                f"{datos['precio']:.2f}",
                f"{subtotal:.2f}"
            ))
        
        self.label_total.configure(text=f"TOTAL: ${total_acumulado:.2f}")

    def _seleccionar_cliente(self):
        dlg = ClienteDialog(self, self.db)
        self.wait_window(dlg)
        if getattr(dlg, 'result', None):
            self.current_client = dlg.result
            # mostrar nombre en el botón
            self.btn_cliente.configure(text=f"Cliente: {self.current_client[1]}")
        else:
            # por defecto consumidor final
            self.current_client = None
            self.btn_cliente.configure(text="Cliente: Consumidor Final")

    def _on_metodo_pago_change(self, value):
        # antiguo handler (ya no usado) — mantener compatibilidad
        self._set_metodo_pago(value)

    def _set_metodo_pago(self, metodo):
        self.metodo_seleccionado = metodo
        # Mostrar u ocultar referencia
        if metodo in ("transferencia", "pago movil"):
            # mostrar el marco de referencia centrado y habilitar entrada
            try:
                self.referencia_frame.pack(pady=(8,6))
                self.entry_referencia.configure(state='normal')
                self.entry_referencia.delete(0, 'end')
                self.entry_referencia.focus()
            except Exception:
                pass
        else:
            # ocultar el marco de referencia
            try:
                self.referencia_frame.pack_forget()
                self.entry_referencia.delete(0, 'end')
            except Exception:
                pass
        self._update_payment_buttons()

    def _update_payment_buttons(self):
        for key, btn in self.payment_buttons.items():
            if key == getattr(self, 'metodo_seleccionado', 'efectivo'):
                btn.configure(fg_color="#16a085", text_color="white")
            else:
                btn.configure(fg_color="#2b2b2b", text_color="#d1d1d1")

    def finalizar_venta(self):
        # 1. VALIDACIÓN OBLIGATORIA DEL CLIENTE (Lo que pediste)
        if self.current_client is None:
            messagebox.showerror("Cliente Requerido", "No se puede finalizar la venta sin un cliente registrado o seleccionado.")
            self._seleccionar_cliente() # Abrir ventana de una vez
            return

        if not self.carrito:
            messagebox.showwarning("Carrito vacío", "No hay productos para cobrar.")
            return

        if messagebox.askyesno("Confirmar", f"¿Desea cerrar la venta por un total de {self.lbl_total.cget('text')}?"):
            try:
                metodo = getattr(self, 'metodo_seleccionado', 'efectivo')
                referencia = self.entry_referencia.get().strip() if metodo in ("transferencia", "pago movil") else None
                
                if metodo in ("transferencia", "pago movil") and not referencia:
                    messagebox.showwarning("Referencia", "Ingrese el número de referencia.")
                    return

                # Registrar en DB
                venta_id = self.db.crear_venta(self.carrito, metodo_pago=metodo, referencia=referencia)
                if venta_id:
                    messagebox.showinfo("Éxito", f"Venta {venta_id} procesada.")
                    self.generar_recibo_pdf(venta_id)
                    self.carrito = {}
                    self.current_client = None # Resetear cliente para la próxima
                    self.btn_cliente.configure(text="Cliente: Consumidor Final")
                    self.mostrar_ventas()
            except Exception as e:
                messagebox.showerror("Error", f"Fallo al cobrar: {e}")

    def limpiar_formulario_inv(self):
        self.in_cod.delete(0, 'end')
        self.in_nom.delete(0, 'end')
        self.in_cat.delete(0, 'end')
        self.in_pre_c.delete(0, 'end')
        self.in_pre_v.delete(0, 'end')
        self.in_sto.delete(0, 'end')
        self.in_min.delete(0, 'end')

    def generar_recibo_pdf(self, venta_id):
        # Recuperar venta e items
        venta = self.db.obtener_venta(venta_id)
        items = self.db.obtener_items_venta(venta_id)

        if not venta:
            return None

        # crear carpeta receipts
        receipts_dir = os.path.join(os.path.dirname(__file__), 'receipts')
        os.makedirs(receipts_dir, exist_ok=True)
        filename = f"recibo_{venta_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path = os.path.join(receipts_dir, filename)

        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4

        x = 40
        y = height - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y, "RECIBO DE PAGO - MyMPos")
        c.setFont("Helvetica", 10)
        y -= 20
        c.drawString(x, y, f"Venta ID: {venta_id}")
        y -= 14
        c.drawString(x, y, f"Fecha: {venta[1]}")
        y -= 14
        # metodo_pago and referencia might be in different columns; try to find them
        try:
            metodo = venta[3]
        except Exception:
            metodo = ''
        try:
            referencia = venta[7] if len(venta) > 7 else ''
        except Exception:
            referencia = ''

        y -= 10
        c.drawString(x, y, f"Método: {metodo}")
        y -= 14
        if referencia:
            c.drawString(x, y, f"Referencia: {referencia}")
            y -= 14

        y -= 6
        c.drawString(x, y, "Cant  Producto                         P.Unit    Subtotal")
        y -= 12
        c.line(x, y, width-40, y)
        y -= 12

        total = 0.0
        for it in items:
            producto_id, cantidad, precio_unit, subtotal = it[0], it[1], float(it[2]), float(it[3])
            # buscar nombre del producto
            prod = self.db.get_producto_por_id(producto_id)
            nombre = prod[2] if prod else f"ID {producto_id}"
            line = f"{cantidad:>3}   {nombre[:30]:30}   {precio_unit:7.2f}   {subtotal:8.2f}"
            c.drawString(x, y, line)
            y -= 14
            total += subtotal
            if y < 80:
                c.showPage()
                y = height - 40

        y -= 8
        c.line(x, y, width-40, y)
        y -= 18
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, f"TOTAL: {total:.2f} $")

        c.save()
        return path


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.title("Login - Cajero")
        self.db = db
        self.result = None
        self.geometry("360x200")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Usuario:").pack(pady=(12,4))
        self.e_user = ctk.CTkEntry(self, width=300)
        self.e_user.pack()

        ctk.CTkLabel(self, text="Contraseña:").pack(pady=(8,4))
        self.e_pass = ctk.CTkEntry(self, width=300, show='*')
        self.e_pass.pack()

        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Entrar", command=self._on_ok).pack(side='left', padx=8)
        ctk.CTkButton(btn_frame, text="Salir", fg_color='#e74c3c', command=self.destroy).pack(side='left', padx=8)

    def _on_ok(self):
        user = self.e_user.get().strip()
        pw = self.e_pass.get()
        if not user or not pw:
            messagebox.showwarning("Atención", "Usuario y contraseña obligatorios")
            return
        # hashear con sha256 (debe coincidir con lo guardado en DB)
        h = hashlib.sha256(pw.encode('utf-8')).hexdigest()
        row = self.db.authenticate_user(user, h)
        if row:
            self.result = row
            self.destroy()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")


class ClienteDialog(ctk.CTkToplevel):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.title("Seleccionar Cliente")
        self.db = db
        self.result = None
        self.geometry("520x400")
        self.transient(parent)
        self.grab_set()

        top = ctk.CTkFrame(self)
        top.pack(fill='x', pady=8, padx=8)
        self.entry_buscar = ctk.CTkEntry(top, placeholder_text='Buscar por nombre o id', width=360)
        self.entry_buscar.pack(side='left', padx=(0,8))
        ctk.CTkButton(top, text='Buscar', command=self._buscar).pack(side='left')

        mid = ctk.CTkFrame(self)
        mid.pack(fill='both', expand=True, pady=6, padx=8)
        self.tree = ttk.Treeview(mid, columns=('id','nombre','telefono'), show='headings')
        self.tree.heading('id', text='ID')
        self.tree.heading('nombre', text='NOMBRE')
        self.tree.heading('telefono', text='TEL')
        self.tree.pack(fill='both', expand=True)

        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='x', pady=8, padx=8)
        ctk.CTkButton(bottom, text='Seleccionar', command=self._select).pack(side='left')
        ctk.CTkButton(bottom, text='Agregar Nuevo', command=self._add_new).pack(side='left', padx=8)
        ctk.CTkButton(bottom, text='Cerrar', fg_color='#e74c3c', command=self.destroy).pack(side='right')

    def _buscar(self):
        q = self.entry_buscar.get().strip()
        if not q:
            return
        res = self.db.buscar_cliente(q)
        # limpiar
        for r in self.tree.get_children():
            self.tree.delete(r)
        if not res:
            return
        if isinstance(res[0], tuple) and len(res[0])>1 and isinstance(res[0][0], int):
            # varios resultados
            for row in res:
                self.tree.insert('', 'end', values=(row[0], row[1], row[3]))
        else:
            # un solo resultado
            self.tree.insert('', 'end', values=(res[0], res[1], res[3]))

    def _select(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning('Atención','Selecciona un cliente')
            return
        vals = self.tree.item(sel,'values')
        # obtener cliente completo
        cid = vals[0]
        row = self.db.get_cliente_por_id(cid)
        if row:
            self.result = row
            self.destroy()

    def _add_new(self):
        name = simpledialog.askstring('Nuevo cliente','Nombre del cliente', parent=self)
        if not name:
            return
        cedula = simpledialog.askstring('Cédula','Cédula / RIF (opcional)', parent=self) or ''
        tel = simpledialog.askstring('Teléfono','Teléfono (opcional)', parent=self) or ''
        cid = self.db.crear_cliente((name, cedula, tel))
        if cid:
            messagebox.showinfo('Creado', f'Cliente creado ID {cid}')
            row = self.db.get_cliente_por_id(cid)
            self.result = row
            self.destroy()


if __name__ == "__main__":
    app = MyMPos()
    app.mainloop()