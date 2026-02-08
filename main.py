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
from decimal import Decimal
import re


def parse_monto(valor):
    """Convierte cadenas con separadores de miles/decimales variados a float.
    Acepta formatos como '4,974.21', '4.974,21', '$ 1.234,56', '1234.56' y devuelve float.
    """
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float, Decimal)):
        return float(valor)
    s = str(valor).strip()
    if s == "":
        return 0.0
    # eliminar símbolos de moneda y espacios
    s = s.replace(' ', '').replace('$', '').replace('US$', '').replace('Bs.', '').replace('Bs', '')
    # Si contiene ambos separadores, detectar cuál es el decimal (el que aparece más a la derecha)
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # coma es decimal, punto miles
            s = s.replace('.', '').replace(',', '.')
        else:
            # punto es decimal, coma miles
            s = s.replace(',', '')
    elif ',' in s:
        # Asumir coma como separador decimal
        s = s.replace('.', '').replace(',', '.')
    else:
        # solo punto o solo dígitos
        s = s
    # eliminar cualquier caracter no numérico salvo '.' y '-'
    s = re.sub(r'[^0-9\.\-]', '', s)
    try:
        return float(s)
    except Exception:
        return 0.0


class MyMPos(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        # Obtener la tasa y forzar a `float` para evitar operaciones entre float y Decimal
        tasa_val = obtener_tasa_bcv() or self.db.obtener_tasa_guardada() or 1.0
        try:
            self.tasa = float(Decimal(str(tasa_val)))
        except Exception:
            self.tasa = 1.0
        self.carrito = {}

        self.title("MyMPos - Sistema de Control")
        self.geometry("1100x700")

        # --- A. CONFIGURAR LA MALLA (GRID) DE LA VENTANA PRINCIPAL ---
        self.grid_columnconfigure(1, weight=1) # El contenedor de ventas se estira
        self.grid_rowconfigure(0, weight=1)    # El centro se estira hacia abajo
        self.grid_rowconfigure(1, weight=0)    # La barra de estado se queda fija abajo

        # --- B. CREAR LOS COMPONENTES (Sin posicionarlos aún) ---
        
        # Barra de Estado (Abajo)
        self.status_frame = ctk.CTkFrame(self, height=30, fg_color="#2b2b2b", corner_radius=0)
        
        self.btn_user_status = ctk.CTkButton(
            self.status_frame, text="👤 Sesión: No iniciada", 
            font=("Arial", 12), fg_color="transparent", 
            hover_color="#3d3d3d", command=self.cerrar_sesion
        )
        self.btn_user_status.pack(side="left", padx=20)
        
        import datetime
        fecha = datetime.datetime.now().strftime("%d/%m/%Y")
        self.lbl_fecha = ctk.CTkLabel(self.status_frame, text=f"📅 {fecha}", font=("Arial", 12))
        self.lbl_fecha.pack(side="right", padx=20)

        # Barra Lateral (Izquierda)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="MyMPos", font=("Roboto", 24, "bold"))
        self.lbl_logo.pack(pady=30)

        self.btn_pos = ctk.CTkButton(self.sidebar, text="🛒 VENTAS", command=self.mostrar_ventas)
        self.btn_pos.pack(pady=10, padx=20)

        self.btn_consulta = ctk.CTkButton(self.sidebar, text="🔍 CONSULTAR PRECIO", command=self.abrir_consulta_precios)
        self.btn_consulta.pack(pady=10, padx=20)

        self.btn_inv = ctk.CTkButton(self.sidebar, text="📦 INVENTARIO", command=self.mostrar_inventario)
        self.btn_inv.pack(pady=10, padx=20)

        self.btn_reportes = ctk.CTkButton(self.sidebar, text="📈 Reportes / Caja", command=self.mostrar_seccion_reportes)
        self.btn_reportes.pack(pady=10, padx=20)

        # Contenedor Principal (Derecha)
        self.contenedor = ctk.CTkFrame(self, corner_radius=15)

        # --- C. POSICIONAR TODO CON GRID (Regla de oro: No usar .pack aquí) ---
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.contenedor.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        # usuario y cliente actuales
        self.current_user = None
        self.current_client = None

        # Pedir login antes de mostrar la interfaz
        self.after(200, self._prompt_login)
        # Mostrar Ventas por defecto
        self.mostrar_ventas()

    def aplicar_estilo_oscuro(self):
        style = ttk.Style()
        style.theme_use("clam") # Forzamos el motor que sí acepta colores
        
        # Configuramos el estilo 'Treeview' de forma global
        style.configure("Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=35,
            borderwidth=0,
            font=("Arial", 11)
        )
        style.configure("Treeview.Heading",
            background="#333333",
            foreground="white",
            relief="flat",
            font=("Arial", 12, "bold")
        )
        style.map("Treeview", background=[('selected', '#1f538d')])

    def _prompt_login(self):
        # 1. Nos aseguramos de que la principal esté escondida
        self.withdraw() 
        
        # 2. Lanzamos el diálogo
        dlg = LoginDialog(self, self.db)
        
        # 3. Esperamos a que el usuario termine en esa ventana
        self.wait_window(dlg)
        
        if getattr(dlg, 'result', None):
            self.current_user = dlg.result 
            
            # --- LÍNEA CLAVE 1: Mostrar la ventana principal ---
            self.deiconify() 
            
            nombre_real = self.current_user[2] 
            rol_db = self.current_user[3].lower() if self.current_user[3] else "cajero"
            
            self.btn_user_status.configure(
                text=f"👤 USUARIO: {nombre_real} | ROL: {rol_db.upper()} (Cerrar Sesión)"
            )
            
            self.lbl_logo.configure(text=f"MyMPos\n{nombre_real}")

            # Bloque de seguridad según el rol
            if rol_db == "admin":
                # Verificamos si ya existe el botón para no crear 20 botones iguales
                if not hasattr(self, 'btn_usuarios') or self.btn_usuarios is None:
                    self.btn_usuarios = ctk.CTkButton(self.sidebar, text="+ NUEVO EMPLEADO", 
                                                     fg_color="#1e3799", 
                                                     command=self.abrir_ventana_nuevo_empleado)
                
                # Mostramos todo en orden
                self.btn_pos.pack(pady=10, padx=20)
                self.btn_inv.pack(pady=10, padx=20)
                self.btn_reportes.pack(pady=10, padx=20)
                self.btn_usuarios.pack(pady=10, padx=20)
            else:
                # Si es cajero, ocultamos lo prohibido
                self.btn_inv.pack_forget()
                self.btn_reportes.pack_forget()
                if hasattr(self, 'btn_usuarios'):
                    self.btn_usuarios.pack_forget()

            self.mostrar_ventas() 
        else:
            # Si cierran la ventanita de login sin entrar, se cierra el programa
            self.quit()

    def abrir_ventana_nuevo_empleado(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title("Registrar Nuevo Empleado")
        ventana.geometry("400x550")
        
        # Estas dos líneas evitan que la ventana se "pierda" o se minimice sola
        ventana.after(100, ventana.lift) 
        ventana.grab_set() 

        ctk.CTkLabel(ventana, text="REGISTRO DE PERSONAL", font=("Roboto", 20, "bold")).pack(pady=20)

        ent_nombre = ctk.CTkEntry(ventana, placeholder_text="Nombre Completo", width=300)
        ent_nombre.pack(pady=10)

        ent_user = ctk.CTkEntry(ventana, placeholder_text="Nombre de Usuario (Login)", width=300)
        ent_user.pack(pady=10)

        ent_pass = ctk.CTkEntry(ventana, placeholder_text="Contraseña Normal", width=300, show="*")
        ent_pass.pack(pady=10)

        combo_rol = ctk.CTkComboBox(ventana, values=["cajero", "admin"], width=300)
        combo_rol.set("cajero")
        combo_rol.pack(pady=10)

        def guardar():
            nombre = ent_nombre.get().strip()
            usuario = ent_user.get().strip()
            contra = ent_pass.get().strip()
            rol = combo_rol.get()

            if not (nombre and usuario and contra):
                from tkinter import messagebox
                messagebox.showwarning("Faltan datos", "Por favor llena todos los campos.")
                return

            import hashlib
            hash_v = hashlib.sha256(contra.encode('utf-8')).hexdigest()
            
            exito = self.db.registrar_nuevo_usuario(usuario, nombre, hash_v, rol)
            
            if exito:
                from tkinter import messagebox
                messagebox.showinfo("Listo", f"El usuario {usuario} ha sido creado.")
                ventana.destroy()
            else:
                from tkinter import messagebox
                messagebox.showerror("Error", "No se pudo crear. Revisa si el nombre ya existe.")

        # --- ESTO ES LO QUE FALTABA: EL BOTÓN ---
        btn_crear = ctk.CTkButton(ventana, text="CREAR EMPLEADO", fg_color="#27ae60", command=guardar)
        btn_crear.pack(pady=20)

    def cerrar_sesion(self):
        from tkinter import messagebox
        if messagebox.askyesno("Cerrar Sesión", "¿Estás seguro de que deseas salir?"):
            # 1. Limpiamos los datos del usuario actual
            self.current_user = None
            
            # 2. Reseteamos la interfaz
            self.btn_user_status.configure(text="👤 Sesión: No iniciada")
            self.lbl_logo.configure(text="MyMPos")
        
            # 5. Volvemos a lanzar el login
            self._prompt_login()

    def limpiar_pantalla(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def mostrar_ventas(self):
        self.limpiar_pantalla()
        self.carrito = {} 
        self.aplicar_estilo_oscuro()

        # Configurar el contenedor para que la tabla se estire
        self.contenedor.grid_columnconfigure(0, weight=1)
        self.contenedor.grid_rowconfigure(1, weight=1) # La tabla (fila 1) es la que crece

        # --- BLOQUE SUPERIOR (Buscador) ---
        self.frame_sup = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.frame_sup.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(self.frame_sup, text=f"📊 Tasa BCV: {self.tasa:.2f} Bs.", 
                     font=("Roboto", 12, "bold"), text_color="#3498db").pack(anchor="w")
        
        # --- BUSCADOR VELOZ ---
        ctk.CTkLabel(self.frame_sup, text="Buscar Producto:").pack(pady=(10,0))
        
        self.entry_buscar = ctk.CTkEntry(self.frame_sup, width=500, height=40)
        self.entry_buscar.pack(pady=(5,0))
        
        # La lista FLOTANTE (se queda en el contenedor principal para que no se mueva con el scroll)
        self.lista_sugerencias = tk.Listbox(
            self.contenedor, # Este se queda fuera del scroll para que flote encima
            width=70, height=6, font=("Arial", 11),
            bg="#2b2b2b", fg="white", borderwidth=1, relief="flat"
        )

        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.agregar_al_carrito)

        # --- BLOQUE CENTRAL (Scroll con Tabla y Pagos) ---
        self.scroll_container = ctk.CTkScrollableFrame(self.contenedor, fg_color="transparent")
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=5)

        # Panel de pago visual
        pago_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        pago_frame.pack(fill='x', padx=20, pady=(0,8))

        pago_center = ctk.CTkFrame(pago_frame, fg_color="transparent")
        pago_center.pack(anchor='center', pady=4)

        payment_box = ctk.CTkFrame(pago_center, corner_radius=15, fg_color="#1f1f1f")
        payment_box.pack(padx=10, pady=10, fill="x")

        ctk.CTkLabel(payment_box, text="Método de pago:", font=("Arial", 13, "bold")).pack(side='left', padx=(20,10), pady=15)

        pagos_frame = ctk.CTkFrame(payment_box, fg_color="transparent")
        pagos_frame.pack(side='left', padx=10, fill="x", expand=True)

        self.payment_buttons = {}
        # Lista de pagos sin el menú de efectivo
        pagos = [("Efectivo","efectivo"), ("Tarjeta","tarjeta"), ("Biopago","biopago"), ("Transferencia","transferencia"), ("Pago Móvil","pago movil")]
        
        for text, key in pagos:
            btn = ctk.CTkButton(
                pagos_frame, 
                text=text, 
                width=110, 
                height=40,
                fg_color="#2b2b2b", 
                corner_radius=10, 
                command=lambda k=key: self._set_metodo_pago(k) # Volvemos al comando simple
            )
            btn.pack(side='left', padx=5, pady=10)
            self.payment_buttons[key] = btn

        # --- SECTOR DE OPCIONES DINÁMICAS (Debajo de los botones) ---
        
        # 1. Selector de Moneda FIJO (Solo se muestra si eligen Efectivo)
        self.moneda_frame = ctk.CTkFrame(pago_center, fg_color="transparent")
        ctk.CTkLabel(self.moneda_frame, text="Moneda del Efectivo:", font=("Arial", 11, "bold")).pack(side='left', padx=(0,8))
        
        self.opcion_moneda = ctk.CTkSegmentedButton(
            self.moneda_frame, 
            values=["Dólares ($)", "Bolívares (Bs)"],
            command=self._cambiar_tipo_moneda_efectivo # Esta es la función que guarda la elección
        )
        self.opcion_moneda.set("Dólares ($)")
        self.opcion_moneda.pack(side='left')

        # 2. Área de referencia (Tu código original de referencia)
        self.referencia_frame = ctk.CTkFrame(pago_center, fg_color="transparent")
        ctk.CTkLabel(self.referencia_frame, text="Referencia:", font=("Arial", 11)).pack(side='left', padx=(0,8))
        self.entry_referencia = ctk.CTkEntry(self.referencia_frame, width=420)
        self.entry_referencia.pack(side='left')

        # Contenedor Cliente
        cliente_frame = ctk.CTkFrame(self.scroll_container, corner_radius=12, fg_color="#1f1f1f")
        cliente_frame.pack(fill='x', padx=20, pady=(6,8))
        cliente_inner = ctk.CTkFrame(cliente_frame, fg_color="transparent")
        cliente_inner.pack(anchor='center', pady=8)
        ctk.CTkLabel(cliente_inner, text="Cliente:", font=("Arial", 12, "bold")).pack(side='left', padx=(0,8))
        self.btn_cliente = ctk.CTkButton(cliente_inner, text="Cliente: Consumidor Final", width=300, height=36, fg_color="#1976d2", command=self._seleccionar_cliente)
        self.btn_cliente.pack(side='left')

       # 2. TABLA CON COLUMNA "ACCIÓN"
        self.columnas_cart = ("cant", "producto", "precio", "subtotal", "accion")
        self.tabla_cart = ttk.Treeview(self.scroll_container, columns=self.columnas_cart, 
                                      show="headings", style="Custom.Treeview")
        
        # Encabezados
        self.tabla_cart.heading("cant", text="CANT")
        self.tabla_cart.heading("producto", text="PRODUCTO")
        self.tabla_cart.heading("precio", text="PRECIO $")
        self.tabla_cart.heading("subtotal", text="SUBTOTAL $")
        self.tabla_cart.heading("accion", text="ELIMINAR")

        # Configurar columnas
        self.tabla_cart.column("cant", width=60, anchor="center")
        self.tabla_cart.column("producto", width=300)
        self.tabla_cart.column("accion", width=100, anchor="center")
        
        self.tabla_cart.pack(pady=10, fill="x", padx=20)

        # EVENTO: Doble clic para ejecutar la eliminación
        self.tabla_cart.bind("<Double-1>", lambda event: self.eliminar_item_carrito())

        # --- BLOQUE INFERIOR (Total y Cobrar fijo) ---
        self.frame_total = ctk.CTkFrame(self.contenedor, fg_color="#1a1a1a", height=100)
        self.frame_total.grid(row=2, column=0, sticky="ew")
        
        self.lbl_total = ctk.CTkLabel(self.frame_total, text="TOTAL: $0.00\n(0.00 Bs.)", 
                                     font=("Arial", 30, "bold"), text_color="#27ae60")
        self.lbl_total.pack(side="left", padx=30, pady=10)

        self.btn_cobrar = ctk.CTkButton(self.frame_total, text="COBRAR VENTA", command=self.presionar_boton_cobrar, fg_color="green",
                                       height=50, width=200, font=("Arial", 14, "bold"))
        self.btn_cobrar.pack(side="right", padx=30, pady=10)

        # --- BOTÓN DE CIERRE LIMPIO ---
        self.btn_cierre_esquina = ctk.CTkButton(
            master=self.contenedor, 
            text="🔒 CERRAR TURNO", 
            width=120,
            height=30,
            corner_radius=20, # Estilo píldora, se ve más moderno
            border_spacing=0,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            font=("Roboto", 10, "bold"),
            command=self.ventana_cierre_turno
        )
        
        # Lo bajamos un poquito más (y=10) para que no choque con el borde
        self.btn_cierre_esquina.place(relx=0.97, y=10, anchor="ne")
        self.btn_cierre_esquina.lift()

        # Estado inicial
        self.metodo_seleccionado = 'efectivo'
        self._update_payment_buttons()

        # Forzar a la ventana a dibujar los widgets internos inmediatamente
        self.update_idletasks()
        self.after(100, lambda: self.scroll_container._parent_canvas.event_generate("<Configure>"))

    def abrir_consulta_precios(self):
        # Crear ventana emergente
        ventana = ctk.CTkToplevel(self)
        ventana.title("🔍 Verificador de Precios")
        ventana.geometry("500x400")
        ventana.after(100, ventana.lift) # Traer al frente
        ventana.grab_set() # Bloquear la ventana de atrás mientras esta esté abierta

        ctk.CTkLabel(ventana, text="Consulta de Producto", font=("Arial", 20, "bold")).pack(pady=15)

        # Campo de entrada
        ent_busqueda = ctk.CTkEntry(ventana, placeholder_text="Escriba nombre o pase el escáner...", width=350)
        ent_busqueda.pack(pady=5)
        ent_busqueda.focus() # El cursor aparece aquí automáticamente

        # Contenedor de resultados
        scroll_res = ctk.CTkScrollableFrame(ventana, width=450, height=220)
        scroll_res.pack(pady=10, padx=10)

        def ejecutar_busqueda(event=None):
            # Limpiar búsqueda anterior
            for widget in scroll_res.winfo_children():
                widget.destroy()

            texto = ent_busqueda.get()
            if not texto: return

            resultados = self.db.consultar_producto_rapido(texto)

            if not resultados:
                ctk.CTkLabel(scroll_res, text="❌ No se encontró el producto").pack(pady=20)
                return

            # Mostrar cada producto encontrado
            for nombre, precio, stock in resultados:
                fila = ctk.CTkFrame(scroll_res)
                fila.pack(fill="x", pady=2)
                
                # Nombre
                ctk.CTkLabel(fila, text=nombre.upper(), font=("Arial", 12, "bold"), width=200, anchor="w").pack(side="left", padx=10)
                precio_usd = float(precio) # El valor que viene de la DB, forzamos float
                precio_bs = precio_usd * float(self.tasa) # Conversión

                # Mostramos ambos precios con formato profesional
                ctk.CTkLabel(
                    fila, 
                    text=f"${precio_usd:,.2f} USD\n{precio_bs:,.2f} Bs", 
                    font=("Arial", 13, "bold"), 
                    text_color="#3498db",
                    justify="left"
                ).pack(side="left", padx=15)
                # Stock (Cambia de color si hay poco)
                color_stock = "red" if stock <= 3 else "gray"
                ctk.CTkLabel(fila, text=f"Stock: {stock}", text_color=color_stock).pack(side="right", padx=10)

        # Hacer que busque al presionar ENTER
        ent_busqueda.bind("<Return>", ejecutar_busqueda)
        
        # Botón opcional de buscar
        ctk.CTkButton(ventana, text="BUSCAR", command=ejecutar_busqueda).pack(pady=5)
    
    def _forzar_refresco_visual(self):
        """Esta función despierta al ScrollableFrame para que no salga en blanco"""
        self.scroll_container.update()
        self.scroll_container._parent_canvas.configure(scrollregion=self.scroll_container._parent_canvas.bbox("all"))
        self.scroll_container._parent_canvas.yview_moveto(0)

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
        except Exception:
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
            # usamos place_forget porque la lista fue posicionada con .place()
            try:
                self.lista_sugerencias.place_forget()
            except Exception:
                pass
            self._refrescar_vista_carrito()
    
    def eliminar_item_carrito(self):
        # 1. Verificamos qué fila está seleccionada
        seleccion = self.tabla_cart.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Por favor, selecciona un producto en la tabla para eliminarlo.")
            return

        # 2. Sacamos el nombre del producto (está en la columna 1)
        valores = self.tabla_cart.item(seleccion, "values")
        nombre_prod = valores[1]
        
        # 3. Lo buscamos en nuestro diccionario 'self.carrito' para borrarlo del "cerebro"
        codigo_a_quitar = None
        for cod, info in self.carrito.items():
            if info['nombre'] == nombre_prod:
                codigo_a_quitar = cod
                break
        
        if codigo_a_quitar:
            del self.carrito[codigo_a_quitar]
            # IMPORTANTE: Actualizar la pantalla y el total
            self._refrescar_vista_carrito()
            self.actualizar_total_interfaz()

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

    def mostrar_modulo_reportes(self):
        # Limpiar panel central
        for widget in self.contenedor_principal.winfo_children():
            widget.destroy()

        # --- ENCABEZADO Y FILTRO ---
        header = ctk.CTkFrame(self.contenedor_principal, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(header, text="Auditoría de Ventas", font=("Helvetica", 24, "bold")).pack(side="left")
        
        # Aquí podrías poner un entry para cambiar la fecha, por ahora usaremos hoy
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        ctk.CTkLabel(header, text=f"Fecha: {fecha_hoy}", font=("Helvetica", 14)).pack(side="right", padx=20)

        # --- TARJETAS DE RESUMEN (Aquí ves cuánto hay por cada método) ---
        resumen_frame = ctk.CTkFrame(self.contenedor_principal, fg_color="transparent")
        resumen_frame.pack(fill="x", padx=20, pady=10)

        resumen_data = self.db.obtener_resumen_diario()
        colores = {"efectivo": "#2ecc71", "punto": "#3498db", "pago movil": "#f1c40f", "transferencia": "#9b59b6"}

        for metodo, monto, cant in resumen_data:
            card = ctk.CTkFrame(resumen_frame, width=150, height=80, border_width=2, border_color=colores.get(metodo.lower(), "gray"))
            card.pack(side="left", padx=10, expand=True, fill="both")
            card.pack_propagate(False)
            
            ctk.CTkLabel(card, text=metodo.upper(), font=("Helvetica", 12, "bold")).pack(pady=2)
            ctk.CTkLabel(card, text=f"$ {monto:,.2f}", font=("Helvetica", 16)).pack()
            ctk.CTkLabel(card, text=f"{cant} ops", font=("Helvetica", 10, "italic")).pack()

        # --- TABLA DETALLADA DE MOVIMIENTOS ---
        tabla_frame = ctk.CTkScrollableFrame(self.contenedor_principal)
        tabla_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Encabezados de tabla
        headers = ["N° Fact", "Hora", "Vendedor", "Método", "Referencia", "Monto"]
        h_frame = ctk.CTkFrame(tabla_frame, fg_color="gray30")
        h_frame.pack(fill="x", pady=5)
        for text in headers:
            ctk.CTkLabel(h_frame, text=text, font=("Helvetica", 12, "bold"), width=120).pack(side="left", padx=5)

        # Cargar datos
        ventas = self.db.obtener_detalle_ventas_por_fecha(fecha_hoy)
        for v in ventas:
            f = ctk.CTkFrame(tabla_frame)
            f.pack(fill="x", pady=2)
            
            ctk.CTkLabel(f, text=f"#{v[0]}", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=v[1].strftime('%H:%M'), width=120).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=v[5], width=120).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=v[3].upper(), width=120).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=v[4] if v[4] else "---", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(f, text=f"$ {v[2]:,.2f}", width=120, font=("Helvetica", 12, "bold")).pack(side="left", padx=5)

    def mostrar_seccion_reportes(self, fecha_consulta=None):
        self.limpiar_pantalla()
        
        # Si no pasamos fecha, usamos la de hoy
        from datetime import datetime
        if not fecha_consulta:
            fecha_consulta = datetime.now().strftime('%Y-%m-%d')

        modulo_frame = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        modulo_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- CABECERA CON BUSCADOR ---
        cabecera = ctk.CTkFrame(modulo_frame, height=70)
        cabecera.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(cabecera, text="AUDITORÍA DE CAJA", font=("Roboto", 20, "bold")).pack(side="left", padx=20)
        
        # Filtro de Fecha
        frame_filtro = ctk.CTkFrame(cabecera, fg_color="transparent")
        frame_filtro.pack(side="right", padx=20)
        
        self.ent_fecha = ctk.CTkEntry(frame_filtro, placeholder_text="AAAA-MM-DD", width=120)
        self.ent_fecha.insert(0, fecha_consulta) # Ponemos la fecha consultada
        self.ent_fecha.pack(side="left", padx=5)
        
        btn_buscar = ctk.CTkButton(frame_filtro, text="🔍", width=40, 
                                   command=lambda: self.mostrar_seccion_reportes(self.ent_fecha.get()))
        btn_buscar.pack(side="left", padx=5)

        # --- RESUMEN POR MÉTODOS (Cards) ---
        resumen_frame = ctk.CTkFrame(modulo_frame, fg_color="transparent")
        resumen_frame.pack(fill="x", pady=10)
        
        data_resumen = self.db.obtener_resumen_por_fecha(fecha_consulta)
        for metodo, monto, cant in data_resumen:
            nombre_metodo = str(metodo).upper() if metodo else "DESCONOCIDO"
            
            card = ctk.CTkFrame(resumen_frame, width=160, height=80, border_width=1)
            card.pack(side="left", padx=5)
            card.pack_propagate(False)
            
            ctk.CTkLabel(card, text=nombre_metodo, font=("Roboto", 11, "bold")).pack()
            ctk.CTkLabel(card, text=f"$ {float(monto):,.2f}", font=("Roboto", 15, "bold"), text_color="#2ecc71").pack()
            ctk.CTkLabel(card, text=f"{cant} vtas", font=("Roboto", 9, "italic")).pack()

        # --- TABLA DETALLADA ---
        h_table = ctk.CTkFrame(modulo_frame, fg_color="gray25")
        h_table.pack(fill="x", pady=(10, 0))
        
        # Columnas ajustadas
        columnas = [("Fact #", 60), ("Hora", 70), ("Monto", 90), ("Método", 100), ("Vendedor", 100), ("Cliente", 160)]
        for col, ancho in columnas:
            ctk.CTkLabel(h_table, text=col, width=ancho, font=("Roboto", 11, "bold")).pack(side="left", padx=5)

        scroll_caja = ctk.CTkScrollableFrame(modulo_frame)
        scroll_caja.pack(fill="both", expand=True)

        ventas_hoy = self.db.obtener_auditoria_diaria(fecha_consulta)
        
        # --- BLOQUE CORREGIDO (SANGRIAS) ---
        for v in ventas_hoy:
            # v[0]=id, v[1]=hora, v[2]=total, v[3]=metodo, v[4]=nombre_cajero, v[5]=nombre_cliente
            fila = ctk.CTkFrame(scroll_caja)
            fila.pack(fill="x", pady=1)
            
            # Datos de la fila
            ctk.CTkLabel(fila, text=f"#{v[0]}", width=60).pack(side="left", padx=5)
            
            hora_v = v[1].strftime('%H:%M') if hasattr(v[1], 'strftime') else str(v[1])[:5]
            ctk.CTkLabel(fila, text=hora_v, width=70).pack(side="left", padx=5)
            
            ctk.CTkLabel(fila, text=f"$ {v[2]:,.2f}", width=90, font=("Roboto", 11, "bold")).pack(side="left", padx=5)
            
            ctk.CTkLabel(fila, text=str(v[3]).upper(), width=100).pack(side="left", padx=5)
            
            # Nombre del Cajero (Cambiado a color cyan para resaltar)
            nombre_cajero = v[4] if v[4] else "Sistema"
            ctk.CTkLabel(fila, text=nombre_cajero, width=100, text_color="cyan").pack(side="left", padx=5)
            
            # Nombre del Cliente
            nombre_cliente = v[5] if v[5] else "Consumidor Final"
            ctk.CTkLabel(fila, text=nombre_cliente, width=160, anchor="w").pack(side="left", padx=5)
            
            # Botón de PDF con protección de variable id_v
            ctk.CTkButton(fila, text="📄", width=30, 
                          command=lambda id_v=v[0]: self.generar_recibo_pdf(id_v)).pack(side="right", padx=10)

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

    def agregar_al_carrito(self, event=None):
        try:
            indices = self.lista_sugerencias.curselection()
            if indices:
                texto = self.lista_sugerencias.get(indices[0])
            else:
                texto = self.entry_buscar.get().strip()
        except Exception as e:
            print(f"Error al obtener selección: {e}")
            return

        if not texto or texto == "Sin resultados":
            return

        busqueda = texto.split(" | ")[0] if " | " in texto else texto
        resultado = self.db.buscar_producto(busqueda)
        
        if resultado:
            # resultado[0] suele ser la tupla (id, nombre, precio, stock...)
            prod = resultado[0] if isinstance(resultado, list) else resultado
            
            # --- CAMBIO IMPORTANTE AQUÍ ---
            # Capturamos el ID real de la base de datos (generalmente prod[0])
            id_db = prod[0] 
            codigo = str(id_db) # Usamos el ID como clave del carrito
            nombre = str(prod[1])
            precio = float(prod[2])
            
            if codigo in self.carrito:
                self.carrito[codigo]['cantidad'] += 1
                self.carrito[codigo]['subtotal'] = self.carrito[codigo]['cantidad'] * precio
            else:
                # GUARDAMOS EL ID DENTRO DEL DICCIONARIO
                self.carrito[codigo] = {
                    'id': id_db,        # <--- ¡ESTO ES LO QUE TE FALTABA!
                    'nombre': nombre, 
                    'precio': precio, 
                    'cantidad': 1, 
                    'subtotal': precio
                }
            
            # --- LIMPIEZA TOTAL ---
            self.entry_buscar.delete(0, tk.END)
            self.lista_sugerencias.delete(0, tk.END)
            self.lista_sugerencias.place_forget() 
            self._refrescar_vista_carrito()
            self.actualizar_total_interfaz()
            self.entry_buscar.focus()

    def actualizar_total_interfaz(self):
        """Calcula el total en USD y Bs, y actualiza el label en pantalla"""
        total_usd = 0.0
        for info in self.carrito.values():
            total_usd += float(info['subtotal'])
        
        # Calculamos la conversión a Bolívares
        total_bs = total_usd * self.tasa
        
        if hasattr(self, 'lbl_total'):
            # Usamos \n para que se vea uno sobre otro, o un guion si lo prefieres de lado
            texto_pantalla = f"TOTAL: ${total_usd:,.2f}\n({total_bs:,.2f} Bs.)"
            self.lbl_total.configure(text=texto_pantalla)
        
        return total_usd

    def _refrescar_vista_carrito(self):
        # Limpiar la tabla antes de rellenar
        for item in self.tabla_cart.get_children():
            self.tabla_cart.delete(item)

        # Rellenar con lo que hay en el diccionario
        for cod, info in self.carrito.items():
            self.tabla_cart.insert("", "end", values=(
                info['cantidad'], 
                info['nombre'], 
                f"{info['precio']:.2f}", 
                f"{info['subtotal']:.2f}",
                "🗑️ ELIMINAR" # Texto que sale al lado de cada producto
            ))
        
        # Forzamos que la tabla se redibuje (esto evita el fondo blanco)
        self.tabla_cart.update()
        
    def _seleccionar_cliente(self):
        dlg = ClienteDialog(self, self.db)
        self.wait_window(dlg)
        
        # Verificamos que el botón no haya sido destruido por error
        if not self.btn_cliente.winfo_exists():
            return

        if dlg.result: 
            self.current_client = dlg.result
            self.btn_cliente.configure(text=f"Cliente: {self.current_client[1]}", fg_color="#2ecc71")
            self._refrescar_vista_carrito()
        else:
            # Si quieres que por defecto sea Consumidor Final, asígnalo aquí
            self.current_client = ("0", "Consumidor Final", "N/A") 
            self.btn_cliente.configure(text="Cliente: Consumidor Final", fg_color="#1976d2")
            

    def _on_metodo_pago_change(self, value):
        # antiguo handler (ya no usado) — mantener compatibilidad
        self._set_metodo_pago(value)

    def _mostrar_menu_efectivo(self):
        """Crea un menú flotante para elegir el tipo de moneda en efectivo"""
        # Creamos el menú con un estilo oscuro básico
        menu_moneda = tk.Menu(self, tearoff=0, background='#1f1f1f', foreground='white', activebackground='#3498db', font=("Arial", 11))
        
        # Opciones
        menu_moneda.add_command(label="💵 Efectivo en Dólares ($)", command=lambda: self._set_metodo_pago("efectivo_usd"))
        menu_moneda.add_separator()
        menu_moneda.add_command(label="🇻🇪 Efectivo en Bolívares (Bs)", command=lambda: self._set_metodo_pago("efectivo_bs"))
        
        # Calculamos la posición del botón de efectivo para mostrar el menú justo ahí
        btn = self.payment_buttons["efectivo"]
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        
        menu_moneda.tk_popup(x, y)

    def _set_metodo_pago(self, metodo):
        self.metodo_seleccionado = metodo
        
        # Mostrar selector de moneda si es efectivo
        if metodo == "efectivo":
            self.moneda_frame.pack(pady=5)
            self._cambiar_tipo_moneda_efectivo(self.opcion_moneda.get())
        else:
            self.moneda_frame.pack_forget()

        # Mostrar cuadro de referencia si es transferencia o pago móvil
        if metodo in ("transferencia", "pago movil"):
            self.referencia_frame.pack(pady=5)
        else:
            self.referencia_frame.pack_forget()

        self._update_payment_buttons()

    def _cambiar_tipo_moneda_efectivo(self, valor):
        """Actualiza el método interno según el SegmentedButton"""
        if "Dólares" in valor:
            self.metodo_seleccionado = "efectivo_usd"
        else:
            self.metodo_seleccionado = "efectivo_bs"

    def _update_payment_buttons(self):
        for key, btn in self.payment_buttons.items():
            if key == getattr(self, 'metodo_seleccionado', 'efectivo'):
                btn.configure(fg_color="#16a085", text_color="white")
            else:
                btn.configure(fg_color="#2b2b2b", text_color="#d1d1d1")

    def presionar_boton_cobrar(self):
        """Esta es la función que debe ejecutar tu botón 'COBRAR'"""
        
        # 1. Validación de Carrito (¿Hay algo que vender?)
        if not self.carrito: # O len(self.carrito) == 0
            messagebox.showwarning("Carrito Vacío", "Debes agregar al menos un producto al carrito.")
            return

        # 2. Validación de Cliente
        if not hasattr(self, 'current_client') or self.current_client is None:
            messagebox.showwarning("Falta Cliente", "Debes seleccionar un cliente.")
            return

        # 3. Validación de Método de Pago (¿Cómo van a pagar?)
        if not hasattr(self, 'metodo_seleccionado') or self.metodo_seleccionado is None:
            messagebox.showwarning("Falta Método", "Selecciona un método de pago.")
            return

        # SI PASA TODAS LAS VALIDACIONES, ENTONCES ABRE LA VENTANA QUE HICIMOS
        self.finalizar_venta()

    def confirmar_registro_completo(self, ventana_cobro, datos_pago):
        """Procesa el guardado final de la venta con el desglose de pagos"""
        try:
            # 1. Calcular total real del carrito
            total_usd = self.actualizar_total_interfaz()

            # 2. Preparar el diccionario de pago que se guardará en la cabecera
            datos_db = dict(datos_pago) if isinstance(datos_pago, dict) else {}
            datos_db['total_usd'] = total_usd

            # 3. Construir lista de items para insertar en detalle
            carrito_items = []
            for codigo, info in self.carrito.items():
                producto_id = info.get('id', codigo)
                carrito_items.append({
                    'id': producto_id,
                    'cantidad': int(info.get('cantidad', 1)),
                    'precio_unitario': float(info.get('precio', 0)),
                    'subtotal': float(info.get('subtotal', 0))
                })

            vendedor_id = self.current_user[0] if self.current_user else 1
            cliente_id = self.current_client[0] if self.current_client else None

            # 4. Crear la cabecera de la venta
            venta_id = self.db.crear_venta(datos_db, vendedor_id, cliente_id, self.tasa)

            if not venta_id:
                messagebox.showerror("Error", "No se pudo guardar la venta en la base de datos (cabecera).")
                return

            # 5. Insertar el detalle y ajustar stock
            for item in carrito_items:
                ok = self.db.insertar_detalle_venta(venta_id, item['id'], item['cantidad'], item['precio_unitario'], item['subtotal'])
                if not ok:
                    # Registrar el fallo pero no interrumpir el loop de limpieza
                    print(f"Aviso: no se pudo insertar detalle para producto {item['id']}")
                # intentar restar stock (usa la clave que manejes en la tabla productos)
                try:
                    self.db.restar_stock(item['id'], item['cantidad'])
                except Exception:
                    pass

            messagebox.showinfo("Éxito", f"Venta #{venta_id} registrada correctamente.")

            # 6. Limpiar la venta actual
            self.carrito.clear()
            self._refrescar_vista_carrito()
            self.actualizar_total_interfaz()
            try:
                self.entry_referencia.delete(0, tk.END)
            except Exception:
                pass
            try:
                ventana_cobro.destroy()
            except Exception:
                pass
            self.entry_buscar.focus()
            # 7. Generar recibo automáticamente
            try:
                self.generar_recibo_pdf(venta_id, datos_db)
            except Exception as e:
                print(f"Advertencia: no se pudo generar recibo PDF automáticamente: {e}")

        except Exception as e:
            messagebox.showerror("Error Crítico", f"Ocurrió un error al procesar: {e}")

    

    def finalizar_venta(self):
        total_usd = self.actualizar_total_interfaz() 
        total_bs = total_usd * self.tasa

        vent_pago = ctk.CTkToplevel(self)
        vent_pago.title("Caja: Finalizar Venta")
        vent_pago.geometry("650x900")
        vent_pago.attributes("-topmost", True)
        vent_pago.grab_set()

        # Variables de montos fijos
        var_usd = tk.StringVar(value="0.00")       
        var_bs_efec = tk.StringVar(value="0.00")
        var_punto = tk.StringVar(value="0.00")
        var_biopago = tk.StringVar(value="0.00")

        # --- LÓGICA DE AUTO-RELLENO INICIAL ---
        metodo_ini = getattr(self, 'metodo_seleccionado', 'efectivo_usd')
        if metodo_ini == "efectivo_usd": var_usd.set(f"{total_usd:.2f}")
        elif metodo_ini == "efectivo_bs": var_bs_efec.set(f"{total_bs:.2f}")
        elif metodo_ini == "tarjeta": var_punto.set(f"{total_bs:.2f}")
        elif metodo_ini == "biopago": var_biopago.set(f"{total_bs:.2f}")

        ctk.CTkLabel(vent_pago, text="RESUMEN DE COBRO", font=("Arial", 22, "bold")).pack(pady=10)
        
        # 1. BLOQUE DE EFECTIVO
        f_efectivo = ctk.CTkFrame(vent_pago, fg_color="transparent")
        f_efectivo.pack(fill="x", padx=40, pady=5)
        
        def crear_fila(master, label, var, color=None):
            f = ctk.CTkFrame(master, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, width=180, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(f, textvariable=var, width=150, font=("Arial", 14, "bold"), border_color=color)
            ent.pack(side="left", padx=10)
            ent.bind("<Button-1>", lambda e: var.set("") if parse_monto(var.get() or 0) >= total_usd else None)

        ctk.CTkLabel(f_efectivo, text="DINERO EN EFECTIVO", font=("Arial", 11, "bold"), text_color="#5dade2").pack(anchor="w")
        crear_fila(f_efectivo, "Dólares ($):", var_usd, "#27ae60")
        crear_fila(f_efectivo, "Bolívares (Bs):", var_bs_efec)

        # 2. BLOQUE DE TARJETAS (PUNTO / BIOPAGO)
        f_tarjetas = ctk.CTkFrame(vent_pago, fg_color="transparent")
        f_tarjetas.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(f_tarjetas, text="TARJETAS (PUNTO / BIOPAGO)", font=("Arial", 11, "bold"), text_color="#a569bd").pack(anchor="w")
        crear_fila(f_tarjetas, "Punto de Venta:", var_punto, "#2980b9")
        crear_fila(f_tarjetas, "Biopago:", var_biopago, "#16a085")

        # 3. BLOQUE DINÁMICO (PAGO MÓVIL / TRANSFERENCIA)
        ctk.CTkLabel(vent_pago, text="PAGOS BANCARIOS (CON REFERENCIA)", font=("Arial", 11, "bold"), text_color="#f4d03f").pack(padx=40, anchor="w")
        
        f_scroll = ctk.CTkScrollableFrame(vent_pago, height=200, fg_color="#1a1a1a")
        f_scroll.pack(fill="x", padx=30, pady=5)

        self.lista_bancos = []

        def agregar_bancario(tipo="Pago Móvil", monto="0.00"):
            f_l = ctk.CTkFrame(f_scroll, fg_color="transparent")
            f_l.pack(fill="x", pady=3)
            
            cb = ctk.CTkComboBox(f_l, values=["Pago Móvil", "Transferencia"], width=130)
            cb.set(tipo)
            cb.pack(side="left", padx=2)
            
            en_m = ctk.CTkEntry(f_l, placeholder_text="Monto Bs", width=100)
            en_m.insert(0, monto)
            en_m.pack(side="left", padx=2)
            
            en_r = ctk.CTkEntry(f_l, placeholder_text="Referencia", width=140)
            en_r.pack(side="left", padx=2)

            btn_d = ctk.CTkButton(f_l, text="✕", width=30, fg_color="#c0392b", command=lambda: eliminar_l(f_l, obj))
            btn_d.pack(side="left", padx=2)

            obj = {"tipo": cb, "monto": en_m, "ref": en_r}
            self.lista_bancos.append(obj)
            en_m.bind("<KeyRelease>", lambda e: validar())
            validar()

        def eliminar_l(frame, d):
            self.lista_bancos.remove(d)
            frame.destroy()
            validar()

        ctk.CTkButton(vent_pago, text="+ Otro Pago Móvil / Transf", width=200, height=30, command=agregar_bancario).pack(pady=5)

        # Carga inicial bancaria si aplica
        if metodo_ini in ["pago movil", "transferencia"]:
            t = "Pago Móvil" if metodo_ini == "pago movil" else "Transferencia"
            agregar_bancario(t, f"{total_bs:.2f}")

        lbl_status = ctk.CTkLabel(vent_pago, text="", font=("Arial", 15, "bold"))
        lbl_status.pack(pady=10)

        # --- VALIDACIÓN ---
        def validar(*args):
            try:
                # Sumatoria de todo lo que Luis ingresó en la ventana
                v_usd = parse_monto(var_usd.get())
                v_bs_efec = parse_monto(var_bs_efec.get())
                v_bs_tarjetas = parse_monto(var_punto.get()) + parse_monto(var_biopago.get())
                v_bs_bancos = sum(parse_monto(b["monto"].get()) for b in self.lista_bancos)
                
                # Convertimos todo a USD para comparar con el total del carrito
                total_ingresado_usd = v_usd + ((v_bs_efec + v_bs_tarjetas + v_bs_bancos) / self.tasa)
                
                diferencia_usd = total_ingresado_usd - total_usd
                diferencia_bs = diferencia_usd * self.tasa # Convertimos la diferencia a Bs
                # Umbral muy pequeño para comparaciones (evita aceptar montos incompletos)
                epsilon = 0.0001

                if diferencia_usd < -epsilon:
                    # CASO: FALTA DINERO
                    lbl_status.configure(
                        text=f"FALTAN: ${abs(diferencia_usd):,.2f} / {abs(diferencia_bs):,.2f} Bs.", 
                        text_color="#e74c3c"
                    )
                    btn_final.configure(state="disabled")
                else:
                    # CASO: VUELTO O PAGO EXACTO
                    if diferencia_usd > epsilon:
                        lbl_status.configure(
                            text=f"VUELTO: ${diferencia_usd:,.2f} / {diferencia_bs:,.2f} Bs.", 
                            text_color="#2ecc71"
                        )
                    else:
                        lbl_status.configure(text="✓ PAGO COMPLETO", text_color="#2ecc71")
                    btn_final.configure(state="normal")
            except:
                pass

        for v in [var_usd, var_bs_efec, var_punto, var_biopago]:
            v.trace_add("write", validar)

        def procesar():
            m_digital = parse_monto(var_punto.get()) + parse_monto(var_biopago.get()) + sum(parse_monto(b["monto"].get()) for b in self.lista_bancos)
            # Unir todas las referencias (incluyendo Punto/Bio si Luis anotó algo en el futuro, aunque aquí son fijos)
            r_final = ", ".join([f"{b['tipo'].get()}: {b['ref'].get()}" for b in self.lista_bancos if parse_monto(b['monto'].get()) > 0])
            
            self.confirmar_registro_completo(vent_pago, {
                "usd": var_usd.get(), "bs_e": var_bs_efec.get(), 
                "bs_p": str(parse_monto(var_punto.get()) + parse_monto(var_biopago.get())), 
                "bs_t": str(sum(parse_monto(b["monto"].get()) for b in self.lista_bancos)), "ref": r_final
            })

        btn_final = ctk.CTkButton(vent_pago, text="REGISTRAR VENTA", height=60, font=("Arial", 18, "bold"), fg_color="#27ae60", command=procesar)
        btn_final.pack(pady=20, padx=40, fill="x")
        validar()

    def limpiar_formulario_inv(self):
        self.in_cod.delete(0, 'end')
        self.in_nom.delete(0, 'end')
        self.in_cat.delete(0, 'end')
        self.in_pre_c.delete(0, 'end')
        self.in_pre_v.delete(0, 'end')
        self.in_sto.delete(0, 'end')
        self.in_min.delete(0, 'end')

    def generar_recibo_pdf(self, venta_id, datos_pago=None): # Añadimos datos_pago como opcional
        # 1. Recuperar datos desde DB
        venta = self.db.obtener_venta(venta_id)
        items = self.db.obtener_items_venta(venta_id)

        if not venta:
            print("Error: No se encontró la venta para el PDF")
            return None

        # Configuración de carpeta y archivo
        receipts_dir = os.path.join(os.path.dirname(__file__), 'receipts')
        os.makedirs(receipts_dir, exist_ok=True)
        filename = f"recibo_{venta_id}.pdf"
        path = os.path.join(receipts_dir, filename)

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4
        x = 50
        y = height - 50

        # --- ENCABEZADO ---
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, y, "MI NEGOCIO") 
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, y, "Rif: J-00000 | Telf: 0412-0000000")
        y -= 30

        # --- INFO DE VENTA ---
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, f"RECIBO N°: {venta_id}")
        fecha_str = venta[1].strftime('%d/%m/%Y %H:%M') if hasattr(venta[1], 'strftime') else str(venta[1])
        c.drawRightString(width-50, y, f"Fecha: {fecha_str}")
        y -= 15
        
        # --- CLIENTE Y CAJERO (Agregado) ---
        nombre_cl = venta[6] if (len(venta) > 6 and venta[6]) else "CONSUMIDOR FINAL"
        cedula_cl = venta[7] if (len(venta) > 7 and venta[7]) else "N/A"
        nombre_vendedor = venta[8] if len(venta) > 8 else (self.current_user[1] if self.current_user else "Luis")

        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"CLIENTE: {nombre_cl}")
        c.drawRightString(width-50, y, f"CEDULA/RIF: {cedula_cl}") 
        y -= 12
        c.drawString(x, y, f"CAJERO: {nombre_vendedor}")
        y -= 25

        # --- TABLA DE PRODUCTOS ---
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, "CANT")
        c.drawString(x + 50, y, "DESCRIPCIÓN")
        c.drawRightString(width - 120, y, "P.UNIT")
        c.drawRightString(width - 50, y, "SUBTOTAL")
        y -= 5
        c.line(x, y, width-50, y)
        y -= 15

        c.setFont("Helvetica", 10)
        for it in items:
            p_id, cant, p_unit, subtot = it[0], it[1], float(it[2]), float(it[3])
            prod = self.db.get_producto_por_id(p_id)
            nombre = prod[2] if prod else f"Producto ID {p_id}"
            c.drawString(x, y, str(cant))
            c.drawString(x + 50, y, nombre[:35]) 
            c.drawRightString(width - 120, y, f"{p_unit:,.2f}")
            c.drawRightString(width - 50, y, f"{subtot:,.2f}")
            y -= 15

        # --- TOTALES Y DESGLOSE (Agregado) ---
        total_usd = float(venta[2])
        tasa = getattr(self, 'tasa', 1.0) 
        y -= 10
        c.line(width-200, y, width-50, y)
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 150, y, "TOTAL USD:")
        c.drawRightString(width - 50, y, f"$ {total_usd:,.2f}")
        y -= 18
        c.drawRightString(width - 150, y, "TOTAL BS:")
        c.drawRightString(width - 50, y, f"Bs. {total_usd * tasa:,.2f}")

        # Sección de Desglose de Pago (Solo si hay datos_pago)
        if datos_pago:
            y -= 20
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x, y, "DETALLE DE PAGO:")
            y -= 12
            c.setFont("Helvetica", 9)
            if float(datos_pago.get('usd', 0)) > 0:
                c.drawString(x + 10, y, f"Efectivo $: {float(datos_pago['usd']):,.2f}"); y -= 10
            if float(datos_pago.get('bs_e', 0)) > 0:
                c.drawString(x + 10, y, f"Efectivo Bs: {float(datos_pago['bs_e']):,.2f}"); y -= 10
            if float(datos_pago.get('bs_p', 0)) > 0:
                c.drawString(x + 10, y, f"Punto/Bio: {float(datos_pago['bs_p']):,.2f} Bs"); y -= 10
            if float(datos_pago.get('bs_t', 0)) > 0:
                c.drawString(x + 10, y, f"Bancos/PM: {float(datos_pago['bs_t']):,.2f} Bs"); y -= 10
            
            if datos_pago.get('ref'):
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(x + 10, y, f"Ref: {datos_pago['ref']}")

        y -= 30
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(width/2, y, "¡Gracias por su compra!")
        c.save()
        os.startfile(path)
        return path
    
    def ventana_cierre_turno(self):
        pregunta = messagebox.askyesno(
            "Confirmar Cierre", 
            "¿Estás seguro de que deseas cerrar el turno actual?\n\n"
            "Esto generará el reporte de ventas totales de hoy."
        )
        
        if not pregunta: # Si presiona "No"
            return

        usuario_id = self.current_user[0] if self.current_user else "1"
        nombre_cajero = self.current_user[1] if self.current_user else "Luis"
        datos_cierre = self.db.obtener_cierre_cajero(usuario_id)
        
        if not datos_cierre:
            messagebox.showinfo("Cierre de Caja", "No has realizado ventas en este turno.")
            return

        top = ctk.CTkToplevel(self)
        top.title("Corte de Caja")
        top.geometry("350x500")
        top.attributes("-topmost", True) # Que siempre esté al frente
        
        # Header
        ctk.CTkLabel(top, text="💰 RESUMEN DE VENTAS", font=("Roboto", 16, "bold")).pack(pady=20)
        ctk.CTkLabel(top, text=f"Cajero: {nombre_cajero}", font=("Roboto", 12)).pack()
        ctk.CTkLabel(top, text=f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", font=("Roboto", 10, "italic")).pack(pady=5)

        # Contenedor de montos
        frame_montos = ctk.CTkFrame(top, fg_color="gray15")
        frame_montos.pack(fill="both", expand=True, padx=30, pady=10)

        total_usd = 0
        for metodo, monto, cant in datos_cierre:
            total_usd += float(monto)
            fila = ctk.CTkFrame(frame_montos, fg_color="transparent")
            fila.pack(fill="x", pady=8, padx=10)
            
            ctk.CTkLabel(fila, text=str(metodo).upper(), font=("Roboto", 11, "bold")).pack(side="left")
            ctk.CTkLabel(fila, text=f"$ {float(monto):,.2f}", text_color="springgreen").pack(side="right")

        # Total Destacado
        ctk.CTkLabel(top, text=f"TOTAL A ENTREGAR", font=("Roboto", 12, "bold")).pack(pady=(10,0))
        ctk.CTkLabel(top, text=f"$ {total_usd:,.2f}", font=("Roboto", 24, "bold"), text_color="#3498db").pack(pady=5)

        # Botón Final
        btn_print = ctk.CTkButton(top, text="CONFIRMAR Y GENERAR PDF", 
                                 command=lambda: self.imprimir_ticket_cierre(datos_cierre, total_usd, top))
        btn_print.pack(pady=20, padx=30, fill="x")

        
    

    def imprimir_ticket_cierre(self, datos, total_general, ventana_padre):
        from reportlab.pdfgen import canvas
        import os

        # Agregamos el nombre dinámico del cajero
        nombre_cajero = self.current_user[1] if self.current_user else "Luis"
        fecha_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        filename = f"cierre_{nombre_cajero}_{fecha_str}.pdf"
        
        try:
            c = canvas.Canvas(filename, pagesize=(226, 400)) 
            width, height = 226, 400
            
            # Encabezado
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width/2, height - 30, "CORTE DE CAJA")
            c.setFont("Helvetica", 9)
            # Aquí sale el nombre real del cajero
            c.drawCentredString(width/2, height - 45, f"Cajero: {nombre_cajero}")
            c.drawCentredString(width/2, height - 55, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            c.line(10, height - 65, width - 10, height - 65)

            # Detalle por método
            y = height - 85
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20, y, "MÉTODO")
            c.drawRightString(width - 20, y, "MONTO")
            y -= 15
            
            c.setFont("Helvetica", 10)
            for metodo, monto, cant in datos:
                # Limpiamos el nombre del método para que no salgan guiones bajos
                nombre_m = str(metodo).replace('_', ' ').upper()
                c.drawString(20, y, f"{nombre_m} ({cant})")
                c.drawRightString(width - 20, y, f"$ {float(monto):,.2f}")
                y -= 20

            # Total Final
            c.line(10, y, width - 10, y)
            y -= 20
            c.setFont("Helvetica-Bold", 12)
            c.drawString(20, y, "TOTAL:")
            c.drawRightString(width - 20, y, f"$ {total_general:,.2f}")
            
            # Espacio para firma
            y -= 60
            c.line(40, y, width - 40, y)
            c.setFont("Helvetica", 8)
            c.drawCentredString(width/2, y - 10, "Firma del Cajero")

            c.save()
            os.startfile(filename) 
            ventana_padre.destroy() 
            messagebox.showinfo("Éxito", "Cierre generado correctamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el ticket: {e}")

class LoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.title("Login - Cajero")
        self.db = db
        self.result = None
        self.geometry("360x200")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color="#1a1a1a")

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

    def ejecutar_login(self):
        dlg = LoginDialog(self, self.db)
        self.wait_window(dlg)
        
        if dlg.result:
            self.usuario_actual = dlg.result # (id, nombre, user, rol)
            self.deiconify()
            
            # Actualizamos la barra de estado con el nombre real
            self.lbl_user_status.configure(
                text=f"👤 CAJERO: {self.usuario_actual[1]} | ROL: {self.usuario_actual[3].upper()}",
                text_color="#2ecc71" # Verde para indicar sesión activa
            )
        else:
            self.quit()

class ClienteDialog(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Gestión de Clientes")
        self.geometry("800x600") # Un poco más grande para que respire
        self.minsize(600, 450)   # Evita que se encoja tanto que desaparezcan los botones
        self.db = db
        self.result = None 
        
        # 1. TÍTULO (Fijo arriba)
        self.lbl_titulo = ctk.CTkLabel(self, text="Seleccionar Cliente", font=("Arial", 22, "bold"))
        self.lbl_titulo.pack(pady=(15, 5), fill="x")

        # 2. BUSCADOR (Se ajusta al ancho, pero no crece hacia abajo)
        self.frame_busqueda = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.frame_busqueda.pack(fill="x", padx=20, pady=10)

        self.entry_buscar = ctk.CTkEntry(
            self.frame_busqueda, 
            placeholder_text="Escriba nombre, cédula o ID para filtrar...",
            height=40
        )
        self.entry_buscar.pack(side="left", padx=15, pady=10, expand=True, fill="x")
        self.entry_buscar.bind("<KeyRelease>", lambda e: self._buscar())

        # --- ESTILO ---
        parent.aplicar_estilo_oscuro()

        # 3. CONTENEDOR DE TABLA (El "Acordeón": crece y se encoge)
        import tkinter as tk
        self.contenedor_tabla = tk.Frame(self, bg="#2b2b2b")
        # expand=True es la clave para que la tabla use todo el espacio sobrante
        self.contenedor_tabla.pack(fill="both", expand=True, padx=20, pady=5)

        self.tree = ttk.Treeview(
            self.contenedor_tabla, 
            columns=("id", "nombre", "cedula", "telefono"), 
            show="headings"
        )
        
        # Definir encabezados
        for col in ("id", "nombre", "cedula", "telefono"):
            self.tree.heading(col, text=col.upper())

        # Configurar pesos de columnas (para que se estiren proporcionalmente)
        self.tree.column("id", width=60, minwidth=50, anchor="center")
        self.tree.column("nombre", width=300, minwidth=200)
        self.tree.column("cedula", width=150, minwidth=100)
        self.tree.column("telefono", width=150, minwidth=100)

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.contenedor_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # 4. BOTONES (Anclados abajo, se reparten el ancho)
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(fill="x", side="bottom", padx=20, pady=20)

        # Usamos expand=True en cada botón para que se repartan el espacio horizontal equitativamente
        self.btn_seleccionar = ctk.CTkButton(
            self.frame_botones, text="✓ SELECCIONAR", fg_color="#2ecc71", 
            hover_color="#27ae60", font=("Arial", 13, "bold"), command=self._confirmar_seleccion
        )
        self.btn_seleccionar.pack(side="left", padx=10, expand=True, fill="x")

        self.btn_nuevo = ctk.CTkButton(
            self.frame_botones, text="+ NUEVO CLIENTE", command=self._nuevo_cliente
        )
        self.btn_nuevo.pack(side="left", padx=10, expand=True, fill="x")

        self.btn_cancelar = ctk.CTkButton(
            self.frame_botones, text="CANCELAR", fg_color="#e74c3c", 
            hover_color="#c0392b", command=self.destroy
        )
        self.btn_cancelar.pack(side="left", padx=10, expand=True, fill="x")
        self.tree.bind("<Double-1>", lambda e: self._confirmar_seleccion())

        self._buscar()

    def _forzar_dibujo(self):
        """Asegura que los botones se pinten al final"""
        self.update()
        self.btn_seleccionar.lift()
        self.btn_nuevo.lift()
        self.btn_cancelar.lift()

    def _buscar(self):
        """Obtiene el texto del buscador y actualiza la tabla"""
        criterio = self.entry_buscar.get().strip()
        
        # Llamamos a tu método de database.py
        resultados = self.db.buscar_cliente(criterio)

        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Si resultados es None (por error), no hacer nada
        if not resultados:
            return

        # Insertar los datos
        # PostgreSQL retorna una lista de tuplas [(id, nom, ced, tel), ...]
        if isinstance(resultados, list):
            for row in resultados:
                self.tree.insert("", "end", values=row)
        # Si por alguna razón devolvió un solo registro (tupla)
        elif isinstance(resultados, tuple):
            self.tree.insert("", "end", values=resultados)

    def _confirmar_seleccion(self):
        """Captura el cliente seleccionado y cierra la ventana"""
        seleccion = self.tree.focus()
        if not seleccion:
            messagebox.showwarning("Atención", "Por favor, seleccione un cliente de la lista.")
            return

        # Obtener los valores de la fila seleccionada
        valores = self.tree.item(seleccion, "values")
        
        # Buscamos el objeto completo por ID para asegurar integridad
        cliente_completo = self.db.get_cliente_por_id(valores[0])
        
        if cliente_completo:
            self.result = cliente_completo
            self.master.update_idletasks() # Avisa a la ventana principal que se prepare
            self.destroy()

    def _nuevo_cliente(self):
        """Ventana emergente rápida para agregar cliente"""
        nombre = simpledialog.askstring("Nuevo Cliente", "Nombre Completo:", parent=self)
        if not nombre: return

        cedula = simpledialog.askstring("Identificación", "Cédula o RIF:", parent=self) or "V-00000000"
        telefono = simpledialog.askstring("Contacto", "Teléfono:", parent=self) or "N/A"

        # Guardar en DB (usando tu método que ya tiene RETURNING id)
        nuevo_id = self.db.crear_cliente((nombre, cedula, telefono))
        
        if nuevo_id:
            messagebox.showinfo("Éxito", "Cliente guardado correctamente.")
            self.entry_buscar.delete(0, 'end') # Limpiar buscador
            self._buscar() # Refrescar lista para que aparezca el nuevo

if __name__ == "__main__":
    app = MyMPos()
    app.mainloop()