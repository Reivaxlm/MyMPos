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
        self.tasa = obtener_tasa_bcv(self) or self.db.obtener_tasa_guardada() or 1.0
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

        self.btn_reportes = ctk.CTkButton(self.sidebar, text="Reportes / Caja", command=self.mostrar_seccion_reportes)
        self.btn_reportes.pack(pady=10, padx=20)

        # --- 2. CONTENEDOR PRINCIPAL (Donde cambia el contenido) ---
        self.contenedor = ctk.CTkFrame(self, corner_radius=15)
        self.contenedor.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # usuario y cliente actuales
        self.current_user = None
        self.current_client = None

        # Pedir login antes de mostrar la interfaz
        self.after(200, self._prompt_login)
        # Mostrar Ventas por defecto
        self.mostrar_ventas()

    def _prompt_login(self):
        dlg = LoginDialog(self, self.db)
        self.wait_window(dlg)
        if getattr(dlg, 'result', None):
            self.current_user = dlg.result
            name = self.current_user[2] if len(self.current_user) > 2 else self.current_user[1]
            self.lbl_logo.configure(text=f"MyMPos - {name}")
            
            # SOLO SI EL LOGIN ES EXITOSO, mostramos las ventas
            self.mostrar_ventas() 
        else:
            self.quit()
            self.destroy()

    def limpiar_pantalla(self):
        for widget in self.contenedor.winfo_children():
            widget.destroy()

    def mostrar_ventas(self):
        self.limpiar_pantalla()
        self.carrito = {} # Reiniciar carrito al entrar a la vista

        # --- ESTILO TIPO CLIENTE (OSCURO) ---
        style = ttk.Style()
        style.theme_use("clam") 
        style.configure("Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=35, # Un poco más alta para que se vea pro
            borderwidth=0,
            font=("Roboto", 11)
        )
        style.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat")
        style.map("Treeview", background=[('selected', '#e74c3c')]) # Rojo al seleccionar para borrar

        self.scroll_container = ctk.CTkScrollableFrame(self.contenedor, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True)
        
        # Ahora usaremos self.scroll_container en lugar de self.contenedor para los elementos
        
        # Cabecera Tasa
        ctk.CTkLabel(
            self.scroll_container, 
            text=f"📊 Tasa BCV: {self.tasa:.2f} Bs.", 
            font=("Roboto", 12, "bold"),
            text_color="#3498db" # Azul suave en lugar de amarillo para que no canse la vista
        ).pack(anchor="w", padx=25, pady=(10, 0)) # "w" es West (Izquierda)
        # --- BUSCADOR VELOZ ---
        ctk.CTkLabel(self.scroll_container, text="Buscar Producto:").pack(pady=(10,0))
        
        self.entry_buscar = ctk.CTkEntry(self.scroll_container, width=500, height=40)
        self.entry_buscar.pack(pady=(5,0))
        
        # La lista FLOTANTE (se queda en el contenedor principal para que no se mueva con el scroll)
        self.lista_sugerencias = tk.Listbox(
            self.contenedor, # Este se queda fuera del scroll para que flote encima
            width=70, height=6, font=("Arial", 11),
            bg="#2b2b2b", fg="white", borderwidth=1, relief="flat"
        )

        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.agregar_al_carrito)

        # Panel de pago visual
        pago_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        pago_frame.pack(fill='x', padx=20, pady=(0,8))

        pago_center = ctk.CTkFrame(pago_frame, fg_color="transparent")
        pago_center.pack(anchor='center', pady=4)

        payment_box = ctk.CTkFrame(pago_center, corner_radius=12, fg_color="#1f1f1f")
        payment_box.pack(padx=10, pady=6)

        ctk.CTkLabel(payment_box, text="Método de pago:", font=("Arial", 12, "bold")).pack(side='left', padx=(12,8))

        pagos_frame = ctk.CTkFrame(payment_box, fg_color="transparent")
        pagos_frame.pack(side='left', padx=6)

        self.payment_buttons = {}
        pagos = [("Efectivo","efectivo"), ("Tarjeta","tarjeta"), ("Biopago","biopago"), ("Transferencia","transferencia"), ("Pago Móvil","pago movil")]
        for text, key in pagos:
            btn = ctk.CTkButton(pagos_frame, text=text, width=110, height=36, fg_color="#2b2b2b", corner_radius=8, command=lambda k=key: self._set_metodo_pago(k))
            btn.pack(side='left', padx=6)
            self.payment_buttons[key] = btn

        # Área de referencia
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

        # --- CONFIGURACIÓN DE ESTILO PARA EL CARRITO ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=30,
            fieldbackground="#2b2b2b",
            borderwidth=0
        )
        style.map("Treeview", background=[('selected', '#1f538d')])

       # 2. TABLA CON COLUMNA "ACCIÓN"
        self.columnas_cart = ("cant", "producto", "precio", "subtotal", "accion")
        self.tabla_cart = ttk.Treeview(self.scroll_container, columns=self.columnas_cart, show="headings", height=10)
        
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

        # Total
        self.lbl_total = ctk.CTkLabel(self.scroll_container, text="TOTAL: 0.00$", font=("Arial", 40, "bold"))
        self.lbl_total.pack(pady=10)

        self.btn_cobrar = ctk.CTkButton(self.scroll_container, text="COBRAR VENTA", fg_color="green", height=45, command=self.finalizar_venta)
        self.btn_cobrar.pack(pady=10)

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
            self.actualizar_total_interfaz()
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
            self.entry_buscar.focus()

    def actualizar_total_interfaz(self):
        """Calcula el total y actualiza el label en pantalla"""
        total = 0.0
        for info in self.carrito.values():
            total += float(info['subtotal'])
        
        if hasattr(self, 'lbl_total'):
            self.lbl_total.configure(text=f"TOTAL: ${total:,.2f}")
        return total

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
                "❌ QUITAR" # Texto que sale al lado de cada producto
            ))
        
        # Forzamos que la tabla se redibuje (esto evita el fondo blanco)
        self.tabla_cart.update()
        
    def _seleccionar_cliente(self):
        dlg = ClienteDialog(self, self.db)
        self.wait_window(dlg)
        
        if hasattr(dlg, 'result') and dlg.result:
            self.current_client = dlg.result
            # Esto actualiza el botón azul de la interfaz de ventas
            # Usamos el índice [1] porque suele ser el nombre en la tupla (id, nombre, ...)
            self.btn_cliente.configure(text=f"Cliente: {self.current_client[1]}", fg_color="#2ecc71")
        else:
            self.current_client = None
            self.btn_cliente.configure(text="Cliente: Consumidor Final", fg_color="#1976d2")
            

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
        # 1. ¿Hay cajero?
        if not hasattr(self, 'current_user') or self.current_user is None:
            messagebox.showerror("Error", "Inicie sesión.")
            return

        # 2. ¿Hay productos?
        if not self.tabla_cart.get_children():
            messagebox.showwarning("Error", "Carrito vacío.")
            return

        # 3. ¿Seleccionó un cliente real?
        if "Consumidor Final" in self.btn_cliente.cget("text"):
            messagebox.showwarning("Cliente", "Seleccione un cliente de la lista.")
            return
        """Procesa la venta, guarda en DB y abre la factura PDF automáticamente"""
        # 1. Verificación: ¿Hay algo que vender?
        if not self.carrito:
            messagebox.showwarning("Atención", "El carrito está vacío.")
            return

        if not messagebox.askyesno("Confirmar Venta", "¿Desea procesar el pago y finalizar?"):
            return

        try:
            # 2. Recolección de IDs de seguridad
            # IMPORTANTE: Asegúrate de que self.current_user[0] sea el ID que está en la tabla public.usuarios
            if hasattr(self, 'current_user') and self.current_user:
                u_id = str(self.current_user[0]) # Usa el ID del que inició sesión (Luis, María, etc.)
            else:
                u_id = "1"
            
            # Si no hay usuario logueado, intentamos usar un ID por defecto pero que sea UUID o texto válido
            if u_id is None:
                # Si tu tabla usa UUID, esto debería ser un UUID válido, si usa Integer, un número.
                # Por ahora, lo dejamos como None para que el reporte muestre "Sistema" si no hay nadie.
                pass

            c_id = self.current_client[0] if self.current_client else None
            
            # Referencia (Pago móvil / Transferencia)
            ref = ""
            if hasattr(self, 'entry_referencia'):
                ref = self.entry_referencia.get().strip()

            # 3. GUARDADO EN BASE DE DATOS
            # Pasamos u_id como usuario_id para que se guarde en vendedor_id
            venta_id = self.db.crear_venta(
                carrito=self.carrito,
                usuario_id=u_id,
                cliente_id=c_id,
                metodo_pago=self.metodo_seleccionado,
                referencia=ref
            )

            if venta_id:
                # 4. DISPARAR EL RECIBO
                try:
                    # Llamamos a generar_recibo_pdf pasándole el ID recién creado
                    self.generar_recibo_pdf(venta_id)
                except Exception as e:
                    print(f"Error abriendo PDF: {e}")
                    messagebox.showwarning("Aviso", "Venta guardada, pero no se pudo abrir el PDF.")

                # 5. LIMPIEZA Y ACTUALIZACIÓN
                self.carrito = {}
                self.current_client = None
                
                # Limpiar campo de texto si existe
                if hasattr(self, 'entry_referencia'):
                    self.entry_referencia.delete(0, 'end')
                
                # Refrescar toda la interfaz para que aparezca la nueva venta
                self._refrescar_vista_carrito()
                
                # Si tienes la sección de reportes abierta, la actualizamos
                if hasattr(self, 'mostrar_seccion_reportes'):
                    # Si self.ent_fecha existe, usamos su fecha, sino la de hoy
                    fecha = self.ent_fecha.get() if hasattr(self, 'ent_fecha') else None
                    self.mostrar_seccion_reportes(fecha)
                
                messagebox.showinfo("Éxito", f"Venta #{venta_id} completada.")
            else:
                messagebox.showerror("Error", "No se pudo guardar la venta en la base de datos.")

        except Exception as e:
            print(f"Error Crítico en finalizar_venta: {e}")
            messagebox.showerror("Error Crítico", f"Ocurrió un error en el proceso: {e}")

    def limpiar_formulario_inv(self):
        self.in_cod.delete(0, 'end')
        self.in_nom.delete(0, 'end')
        self.in_cat.delete(0, 'end')
        self.in_pre_c.delete(0, 'end')
        self.in_pre_v.delete(0, 'end')
        self.in_sto.delete(0, 'end')
        self.in_min.delete(0, 'end')

    def generar_recibo_pdf(self, venta_id):
        # 1. Recuperar datos desde DB (Asegúrate de usar la consulta con JOIN en database.py)
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
        
        nombre_cl = venta[6] if (len(venta) > 6 and venta[6]) else "CONSUMIDOR FINAL"
        cedula_cl = venta[7] if (len(venta) > 7 and venta[7]) else "N/A"
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"CLIENTE: {nombre_cl}")
        c.drawRightString(width-50, y, f"PAGO: {venta[3]}") 
        y -= 12
        c.setFont("Helvetica", 10)
        c.drawString(x, y, f"CÉDULA/RIF: {cedula_cl}")
        
        # --- CAMBIO AQUÍ: Mostrar NOMBRE en lugar de UUID ---
        # Si nuestra nueva consulta trae el nombre en la posición [8], lo usamos:
        nombre_vendedor = venta[8] if len(venta) > 8 else str(venta[4])[:8]
        c.drawRightString(width-50, y, f"VENDEDOR: {nombre_vendedor}")
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
        total_usd = float(venta[2])
        tasa = getattr(self, 'tasa', 1.0) 

        for it in items:
            p_id = it[0]
            cant = it[1]
            p_unit = float(it[2])
            subtot = float(it[3])
            
            prod = self.db.get_producto_por_id(p_id)
            nombre = prod[2] if prod else f"Producto ID {p_id}"

            c.drawString(x, y, str(cant))
            c.drawString(x + 50, y, nombre[:35]) 
            c.drawRightString(width - 120, y, f"{p_unit:,.2f}")
            c.drawRightString(width - 50, y, f"{subtot:,.2f}")
            
            y -= 15
            if y < 100:
                c.showPage()
                y = height - 50

        # --- TOTALES ---
        y -= 10
        c.line(width-200, y, width-50, y)
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 150, y, "TOTAL USD:")
        c.drawRightString(width - 50, y, f"$ {total_usd:,.2f}")
        
        y -= 18
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - 150, y, "TOTAL BS:")
        c.drawRightString(width - 50, y, f"Bs. {total_usd * tasa:,.2f}")
        
        # Referencia (Ahora es la posición [5] según la estructura que pasaste)
        if len(venta) > 5 and venta[5]:
            y -= 15
            c.setFont("Helvetica", 9)
            c.drawString(x, y, f"Ref: {venta[5]}")

        y -= 30
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(width/2, y, "¡Gracias por su compra!")

        c.save()
        
        try:
            os.startfile(path) 
        except Exception as e:
            print(f"Error al abrir: {e}")
        
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
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import os

        nombre_cajero = self.current_user[1] if self.current_user else "Luis"
        fecha_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        filename = f"cierre_{nombre_cajero}_{fecha_str}.pdf"
        
        try:
            c = canvas.Canvas(filename, pagesize=(226, 400)) # Tamaño ticket (80mm aprox)
            width, height = 226, 400
            
            # Encabezado
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(width/2, height - 30, "CORTE DE CAJA")
            c.setFont("Helvetica", 9)
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
                c.drawString(20, y, f"{str(metodo).upper()} ({cant})")
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
            os.startfile(filename) # Abre el PDF automáticamente
            ventana_padre.destroy() # Cierra la ventana emergente
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
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Gestión de Clientes")
        self.geometry("700x500")
        self.db = db
        self.result = None # Aquí se guardará el cliente seleccionado
        
        # Hacer que la ventana sea modal
        self.transient(parent)
        self.grab_set()
        self.focus_set()

        # --- TÍTULO ---
        self.lbl_titulo = ctk.CTkLabel(self, text="Seleccionar Cliente", font=("Arial", 20, "bold"))
        self.lbl_titulo.pack(pady=10)

        # --- BUSCADOR ---
        frame_busqueda = ctk.CTkFrame(self)
        frame_busqueda.pack(fill="x", padx=20, pady=10)

        self.entry_buscar = ctk.CTkEntry(
            frame_busqueda, 
            placeholder_text="Escriba nombre, cédula o ID para filtrar...",
            width=450
        )
        self.entry_buscar.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        # Evento: busca cada vez que se suelta una tecla
        self.entry_buscar.bind("<KeyRelease>", lambda e: self._buscar())

        # --- TABLA (TREEVIEW) ---
        frame_tabla = ctk.CTkFrame(self)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=5)

        # Configurar estilo para que la tabla sea oscura y combine
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#2b2b2b",
            foreground="white",
            rowheight=30,
            fieldbackground="#2b2b2b",
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

        # Crear la tabla
        self.tree = ttk.Treeview(frame_tabla, columns=("id", "nombre", "cedula", "telefono"), show="headings")
        
        self.tree.heading("id", text="ID")
        self.tree.heading("nombre", text="NOMBRE")
        self.tree.heading("cedula", text="CÉDULA / RIF")
        self.tree.heading("telefono", text="TELÉFONO")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("nombre", width=250)
        self.tree.column("cedula", width=120)
        self.tree.column("telefono", width=120)

        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar para la tabla
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- BOTONES DE ACCIÓN ---
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(fill="x", padx=20, pady=15)

        self.btn_seleccionar = ctk.CTkButton(
            frame_botones, 
            text="✓ SELECCIONAR", 
            fg_color="#2ecc71", 
            hover_color="#27ae60",
            font=("Arial", 13, "bold"),
            command=self._confirmar_seleccion
        )
        self.btn_seleccionar.pack(side="left", padx=5)

        self.btn_nuevo = ctk.CTkButton(
            frame_botones, 
            text="+ NUEVO CLIENTE", 
            command=self._nuevo_cliente
        )
        self.btn_nuevo.pack(side="left", padx=5)

        self.btn_cancelar = ctk.CTkButton(
            frame_botones, 
            text="CANCELAR", 
            fg_color="#e74c3c", 
            hover_color="#c0392b",
            command=self.destroy
        )
        self.btn_cancelar.pack(side="right", padx=5)

        # AL FINAL DEL INIT: Cargar la lista completa de una vez
        self._buscar()

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