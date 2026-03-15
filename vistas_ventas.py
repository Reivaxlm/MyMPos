import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from modulo_cierre import realizar_cierre
from modulo_factura import generar_factura_pdf
from modulo_clientes import BuscarClienteDialog
from utilidades import parse_monto

class VentasFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.actualizar_tabla()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- ESTILOS DE TABLA GLOBALES ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#1E1E1E",
            foreground="white",
            rowheight=35,
            fieldbackground="#1E1E1E",
            bordercolor="#333333",
            borderwidth=0,
            font=("Segoe UI", 12)
        )
        style.map("Treeview", background=[('selected', '#2979FF')])
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 12, "bold")
        )

        self.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. PANEL INFERIOR (Lo declaramos PRIMERO para que se quede abajo)
        panel_inf = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=15, height=90)
        panel_inf.pack(fill="x", side="bottom", pady=(10, 0)) # <--- Va al fondo
        panel_inf.pack_propagate(False)

        # Contenedor de Totales (Izquierda)
        totales_frame = ctk.CTkFrame(panel_inf, fg_color="transparent")
        totales_frame.pack(side="left", padx=20, pady=15)

        self.lbl_total = ctk.CTkLabel(totales_frame, text="TOTAL: $ 0.00", font=("Segoe UI", 36, "bold"), text_color="#00E676")
        self.lbl_total.pack(side="left", padx=(0, 15))

        self.lbl_total_bs = ctk.CTkLabel(totales_frame, text="0.00 Bs", font=("Segoe UI", 22, "bold"), text_color="#FFB300")
        self.lbl_total_bs.pack(side="left", pady=(10, 0)) # Ligero ajuste hacia abajo

        # Contenedor de Botones (Derecha)
        btn_frame = ctk.CTkFrame(panel_inf, fg_color="transparent")
        btn_frame.pack(side="right", padx=20, pady=15)

        ctk.CTkButton(btn_frame, text="🧹 Vaciar", fg_color="transparent", hover_color="#331111", border_width=1, border_color="#FF1744", text_color="#FF1744", command=self.vaciar_carrito, width=110, height=45, font=("Segoe UI", 14, "bold"), corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Eliminar Prod.", fg_color="#D32F2F", hover_color="#B71C1C", command=self.eliminar_item_seleccionado, width=140, height=45, font=("Segoe UI", 14, "bold"), corner_radius=8).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💳 PROCESAR PAGO", fg_color="#2979FF", hover_color="#1565C0", command=self.cobrar, width=200, height=55, font=("Segoe UI", 16, "bold"), corner_radius=8).pack(side="left", padx=(15, 0))

        # --- PANEL SUPERIOR ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", pady=(0, 15))

        # Buscador moderno guiado
        busqueda_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        busqueda_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(busqueda_frame, text="🔍", font=("Segoe UI", 20)).pack(side="left", padx=(0, 10))
        self.entry_buscar = ctk.CTkEntry(busqueda_frame, placeholder_text="Buscar por nombre o código de barra...", 
                                       height=45, font=("Segoe UI", 16), corner_radius=8)
        self.entry_buscar.pack(side="left", fill="x", expand=True)
        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)
        self.entry_buscar.bind("<Return>", lambda e: self.agregar_desde_lista(None))

        # Botón de cierre más elegante
        ctk.CTkButton(self.top_frame, text="🔒 CIERRE DE CAJA", fg_color="#FBC02D", hover_color="#F9A825",
                      text_color="black", height=45, corner_radius=8, font=("Segoe UI", 14, "bold"),
                      command=self.ejecutar_cierre_desde_interfaz, 
                      width=180).pack(side="right", padx=(20, 0))
        
        # LISTA DE SUGERENCIAS (El menú desplegable que faltaba)
        self.lista_sugerencias = tk.Listbox(
            self, width=70, height=6, font=("Arial", 11),
            bg="#2b2b2b", fg="white", borderwidth=1, relief="flat",
            selectbackground="#1f538d"
        )
        self.lista_sugerencias.place_forget() # Oculto por defecto
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.agregar_desde_lista)

        # Si haces clic en cualquier parte del frame, se cierra la lista
        self.bind("<Button-1>", lambda e: self.lista_sugerencias.place_forget())

        # --- TABLA DE CARRITO (Mecanismo Treeview) ---
        # Contenedor para darle borde moderno a la tabla
        tabla_container = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=10)
        tabla_container.pack(fill="both", expand=True, pady=10)
        
        columnas = ("Cant", "Producto", "Precio $", "Subtotal $")
        self.tree = ttk.Treeview(tabla_container, columns=columnas, show="headings", height=15)
        for col in columnas:
            self.tree.heading(col, text=col)
            # Acoplamos mejor los anchos y centramos el nombre
            width = 350 if "Producto" in col else 120
            self.tree.column(col, width=width, anchor="center")
            
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

        # Crear el menú que aparecerá al hacer clic derecho
        self.menu_tabla = tk.Menu(self, tearoff=0)
        self.menu_tabla.add_command(label="Eliminar Producto", command=self.eliminar_item_seleccionado)

        # Vincular el clic derecho de la tabla al menú
        self.tree.bind("<Button-3>", self.mostrar_menu_contextual) # Windows/Linux
        self.tree.bind("<Button-2>", self.mostrar_menu_contextual) # Mac

        # Vincular la tecla Suprimir/Delete para borrar rápido
        self.tree.bind("<Delete>", lambda e: self.eliminar_item_seleccionado())

        # Vincular teclas + y -
        self.tree.bind("<KP_Add>", lambda e: self.cambiar_cantidad_teclado(1))
        self.tree.bind("+", lambda e: self.cambiar_cantidad_teclado(1))
        self.tree.bind("=", lambda e: self.cambiar_cantidad_teclado(1))
        self.tree.bind("<KP_Subtract>", lambda e: self.cambiar_cantidad_teclado(-1))
        self.tree.bind("-", lambda e: self.cambiar_cantidad_teclado(-1))
        

    # --- MÉTODO PARA EL CIERRE ---
    def ejecutar_cierre_desde_interfaz(self):
        
        usuario_id = self.app.usuario_actual[0]
        
        # Importamos el módulo de cierre
        from modulo_cierre import realizar_cierre
        
        try:
            pdf = realizar_cierre(usuario_id)
            messagebox.showinfo("Cierre", f"Cierre generado: {pdf}")
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cerrar: {e}")

    # --- LÓGICA DE BÚSQUEDA Y CARRITO ---

    def _filtrar_busqueda_combo(self, event):
        # Cancelar la búsqueda anterior si existe
        if hasattr(self, '_after_id'):
            self.after_cancel(self._after_id)
        
        # Debounce más rápido para sentirse instantáneo
        self._after_id = self.after(100, self._ejecutar_busqueda_real)

    def _ejecutar_busqueda_real(self):
        texto = self.entry_buscar.get().strip()
        if len(texto) < 2:
            self.lista_sugerencias.place_forget()
            return

        productos = self.app.db.consultar_producto_rapido(texto)
        
        self.lista_sugerencias.delete(0, tk.END)
        if productos:
            # Iterar menos items y hacerlo más compacto
            for p in productos[:7]:  # p = (id, nombre, precio, stock)
                self.lista_sugerencias.insert(tk.END, f"{p[1]} | ${p[2]} | Stock: {p[3]}")
            
            # Calculamos la posición correcta y ajustamos el ancho base a la caja
            x_pos = self.entry_buscar.winfo_x()
            y_pos = self.entry_buscar.winfo_y() + self.entry_buscar.winfo_height()
            
            self.lista_sugerencias.place(x=x_pos, y=y_pos, width=self.entry_buscar.winfo_width())
            self.lista_sugerencias.lift() 
        else:
            self.lista_sugerencias.place_forget()

    def agregar_desde_lista(self, event):
        seleccion = self.lista_sugerencias.curselection()
        if not seleccion:
            # Si no hay selección pero se presionó Enter, tomamos el primer item si existe
            if self.lista_sugerencias.size() > 0:
                idx = 0
            else: return
        else:
            idx = seleccion[0]
            
        item_texto = self.lista_sugerencias.get(idx)
        nombre_prod = item_texto.split(" | ")[0]
        
        # Obtenemos datos frescos de ese producto
        res = self.app.db.consultar_producto_rapido(nombre_prod)
        if res:
            p = res[0] # (id, nombre, precio, stock)
            self.agregar_al_carrito(p[0], p[1], float(p[2]), p[3])
        
        self.entry_buscar.delete(0, tk.END)
        self.lista_sugerencias.place_forget()

    def cambiar_cantidad_teclado(self, delta):
        seleccion = self.tree.selection()
        if not seleccion:
            return
        
        # Obtener el nombre del producto de la fila seleccionada
        valores = self.tree.item(seleccion[0], "values")
        nombre_p = valores[1] # Asegúrate de que el nombre esté en la columna 1
        
        if nombre_p in self.app.carrito:
            # Aquí está la magia: modificamos la cantidad existente
            nueva_cant = self.app.carrito[nombre_p]['cant'] + delta
            
            # Si la cantidad es menor o igual a 0, eliminamos el item
            if nueva_cant <= 0:
                del self.app.carrito[nombre_p]
            else:
                self.app.carrito[nombre_p]['cant'] = nueva_cant
                
            # Refrescamos la tabla y los cálculos
            self.actualizar_tabla()
        else:
            print(f"DEBUG: El producto {nombre_p} no está en el carrito.")

    def agregar_al_carrito(self, pid, nombre, precio, stock_max):
        # 1. Verificar si el producto ya está en el carrito
        if nombre in self.app.carrito:
            # Si ya existe, aumentamos la cantidad en 1
            nueva_cantidad = self.app.carrito[nombre]['cant'] + 1
            
            # Opcional: Validar que no exceda el stock real
            if nueva_cantidad > stock_max:
                messagebox.showwarning("Stock Insuficiente", f"Solo hay {stock_max} unidades disponibles.")
                return
                
            self.app.carrito[nombre]['cant'] = nueva_cantidad
        else:
            # Si es nuevo, lo agregamos con cantidad 1
            self.app.carrito[nombre] = {
                'id': pid,
                'precio': precio,
                'cant': 1
            }
        
        # 2. Refrescar la tabla para que se vea el cambio
        self.actualizar_tabla()
        
        # 3. Limpiar buscador y devolver el foco
        self.entry_buscar.delete(0, tk.END)
        self.lista_sugerencias.place_forget()
        self.entry_buscar.focus_set()

    def actualizar_tabla(self):
        # Limpiar la tabla visual
        for i in self.tree.get_children(): self.tree.delete(i)
        
        total_usd = 0.0
        for nom, datos in self.app.carrito.items():
            sub = datos['precio'] * datos['cant']
            total_usd += sub
            self.tree.insert("", "end", values=(datos['cant'], nom, f"{datos['precio']:.2f}", f"{sub:.2f}"))
        
        # Actualizar etiquetas de total
        self.lbl_total.configure(text=f"TOTAL: $ {total_usd:.2f}")
        self.lbl_total_bs.configure(text=f"{(total_usd * self.app.tasa):.2f} Bs")

    def vaciar_carrito(self):
        self.app.carrito = {}
        self.actualizar_tabla()

    def agregar_referencia_ui(self, container):
        # Cada vez que llamen a esta función, creamos una nueva fila
        frame_pago = ctk.CTkFrame(container, fg_color="transparent")
        frame_pago.pack(fill="x", pady=5)
        
        # Combo para tipo de pago
        tipo = ctk.CTkComboBox(frame_pago, values=["Punto", "Pago Móvil", "Efectivo", "Transferencia"], width=120)
        tipo.pack(side="left", padx=5)
        
        # Campo de monto
        monto = ctk.CTkEntry(frame_pago, placeholder_text="Monto Bs", width=100)
        monto.pack(side="left", padx=5)
        
        # Campo de referencia
        ref = ctk.CTkEntry(frame_pago, placeholder_text="Ref", width=80)
        ref.pack(side="left", padx=5)
        
        return {"tipo": tipo, "monto": monto, "ref": ref}
    
    def eliminar_item_seleccionado(self):
        # 1. Verificamos selección
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un producto en la tabla para eliminarlo.")
            return

        # 2. Sacamos el nombre del producto (Columna 'Producto')
        # Según tu Treeview, el nombre es el segundo valor (índice 1)
        valores = self.tree.item(seleccion[0], "values")
        nombre_p = valores[1]

        # 3. Lo quitamos del diccionario y refrescamos
        if nombre_p in self.app.carrito:
            del self.app.carrito[nombre_p]
            self.actualizar_tabla()
            # El foco vuelve al buscador para seguir vendiendo rápido
            self.entry_buscar.focus_set()
    
    def mostrar_menu_contextual(self, event):
        # Seleccionar la fila donde se hizo clic derecho automáticamente
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu_tabla.post(event.x_root, event.y_root)

    def cobrar(self):
        # 1. Validaciones y Cliente
        if not self.app.carrito:
            messagebox.showwarning("Atención", "El carrito está vacío")
            return

        dlg = BuscarClienteDialog(self, self.app.db)
        self.wait_window(dlg)
        if not dlg.result: return 
        cliente = dlg.result
        
        total_usd = sum(d['precio'] * d['cant'] for d in self.app.carrito.values())
        total_bs = total_usd * self.app.tasa

        # 2. Ventana de Cobro
        vent_pago = ctk.CTkToplevel(self)
        vent_pago.title("Cobro")
        vent_pago.geometry("450x650")
        vent_pago.grab_set()

        ctk.CTkLabel(vent_pago, text=f"TOTAL: {total_bs:.2f} Bs", font=("Arial", 16, "bold")).pack(pady=10)
        
        # LABEL DINÁMICO (Falta/Vuelto)
        lbl_estado = ctk.CTkLabel(vent_pago, text=f"Falta: {total_bs:.2f} Bs", font=("Arial", 22, "bold"), text_color="#FF5252")
        lbl_estado.pack(pady=10)

        # Entradas Fijas
        entradas = {
            'efectivo_usd': ctk.CTkEntry(vent_pago, placeholder_text="Efectivo ($)"),
            'efectivo_bs': ctk.CTkEntry(vent_pago, placeholder_text="Efectivo (Bs)"),
            'bio': ctk.CTkEntry(vent_pago, placeholder_text="Biopago (Bs)"),
            'punto': ctk.CTkEntry(vent_pago, placeholder_text="Punto (Bs)")
        }
        for entry in entradas.values(): entry.pack(pady=2, padx=20, fill="x")

        # Lista dinámica
        self.lista_dinamica = []
        scroll = ctk.CTkScrollableFrame(vent_pago, height=150)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        def actualizar_calculadora(*args):
            # Sumar todos los ingresos convertidos a Bs
            m_usd = parse_monto(entradas['efectivo_usd'].get()) * self.app.tasa
            m_bs = parse_monto(entradas['efectivo_bs'].get())
            m_bio = parse_monto(entradas['bio'].get())
            m_punto = parse_monto(entradas['punto'].get())
            m_dinamicos = sum(parse_monto(p['monto'].get()) for p in self.lista_dinamica)
            
            total_ingresado = m_usd + m_bs + m_bio + m_punto + m_dinamicos
            diferencia = total_bs - total_ingresado

            # Lógica: Si falta dinero -> Rojo. Si sobra -> Verde (Vuelto)
            if diferencia > 0:
                lbl_estado.configure(text=f"Falta: {diferencia:.2f} Bs", text_color="#FF5252")
            else:
                lbl_estado.configure(text=f"Vuelto: {abs(diferencia):.2f} Bs", text_color="#00E676")

        for e in entradas.values(): e.bind("<KeyRelease>", actualizar_calculadora)

        def agregar_fila(metodo_inicial):
            f = ctk.CTkFrame(scroll, fg_color="#333333")
            f.pack(fill="x", pady=2) 
            
            metodo_var = ctk.StringVar(value=metodo_inicial)
            opciones = ctk.CTkOptionMenu(f, values=["Pago Móvil", "Transferencia"], variable=metodo_var, width=120)
            opciones.pack(side="left", padx=5)
            
            monto = ctk.CTkEntry(f, placeholder_text="Bs", width=80)
            monto.bind("<KeyRelease>", actualizar_calculadora)
            monto.pack(side="left", padx=5)
            
            ref = ctk.CTkEntry(f, placeholder_text="Ref", width=80)
            ref.pack(side="left", padx=5)
            
            self.lista_dinamica.append({'tipo': metodo_var, 'monto': monto, 'ref': ref})
            actualizar_calculadora()

        def finalizar():
            try:
                # 1. Calculamos montos fijos
                m_usd = parse_monto(entradas['efectivo_usd'].get()) * self.app.tasa
                m_bs = parse_monto(entradas['efectivo_bs'].get())
                m_bio = parse_monto(entradas['bio'].get())
                m_punto = parse_monto(entradas['punto'].get())
                
                # 2. Creamos la lista de detalles con los montos reales (solo si son > 0)
                detalles_finales = []
                if parse_monto(entradas['efectivo_usd'].get()) > 0:
                    detalles_finales.append(f"Efectivo $: {entradas['efectivo_usd'].get()}")
                if m_bs > 0: detalles_finales.append(f"Efectivo Bs: {m_bs}")
                if m_bio > 0: detalles_finales.append(f"Bio: {m_bio}")
                if m_punto > 0: detalles_finales.append(f"Punto: {m_punto}")
                
                total_p = m_usd + m_bs + m_bio + m_punto
                
                # 3. Agregamos los pagos dinámicos (Pago Móvil / Transferencia)
                for p in self.lista_dinamica:
                    # Usamos .get() porque ahora 'tipo' es un StringVar del OptionMenu
                    nombre_metodo = p['tipo'].get() if hasattr(p['tipo'], 'get') else p['tipo']
                    m = parse_monto(p['monto'].get())
                    r = p['ref'].get().strip()
                    
                    if m > 0:
                        if not r:
                            messagebox.showerror("Error", f"Falta referencia en {nombre_metodo}")
                            return
                        total_p += m
                        detalles_finales.append(f"{nombre_metodo}: {m} (Ref: {r})")

                # 4. Validación de pago completo
                if total_p < (total_bs - 0.01):
                    messagebox.showerror("Error", "Monto insuficiente")
                    return

                # 5. UNIMOS TODO EN UNA SOLA CADENA
                metodo_detalle = " | ".join(detalles_finales)
                
                # EL RESTO DEL CÓDIGO SE MANTIENE IGUAL...
                datos_v = {'total_usd': total_usd, 'metodo': metodo_detalle}
                id_v = self.app.db.crear_venta(datos_v, self.app.usuario_actual[0], cliente[0], self.app.tasa)
                
                if id_v:
                    for nom, d in self.app.carrito.items():
                        # REGISTRO DE ITEM (Automáticamente descuenta stock)
                        self.app.db.registrar_item_venta(id_v, d['id'], d['cant'], d['precio'], float(d['precio'])*int(d['cant']))
                    
                    generar_factura_pdf(
                        id_v, 
                        cliente[1], 
                        cliente[2], 
                        self.app.carrito, 
                        total_usd, 
                        total_bs, 
                        self.app.tasa, 
                        metodo_detalle
                    )
                    messagebox.showinfo("Éxito", "Venta registrada")
                    vent_pago.destroy()
                    self.vaciar_carrito()
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
        for e in entradas.values(): e.bind("<KeyRelease>", actualizar_calculadora)

        # EL BOTÓN DE AGREGAR: Fuera de las funciones, empaquetado en vent_pago
        btn_pago_e = ctk.CTkButton(
            vent_pago, 
            text="➕ Agregar Pago Electrónico", 
            fg_color="#1f538d",
            command=lambda: agregar_fila("Pago Móvil")
        )
        btn_pago_e.pack(pady=10)

        # BOTÓN CONFIRMAR
        ctk.CTkButton(vent_pago, text="CONFIRMAR COBRO", fg_color="green", command=finalizar).pack(pady=20)
        self.lista_pagos = []

def sumar_pagos(self):
    total = 0
    for p in self.lista_pagos:
        total += parse_monto(p["monto"].get())
    return total