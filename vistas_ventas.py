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
        
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", pady=5)

        # --- BUSCADOR ---
        ctk.CTkLabel(self.top_frame, text="BUSCAR:").pack(side="left", padx=5)
        self.entry_buscar = ctk.CTkEntry(self.top_frame, placeholder_text="Escriba aquí...", width=400)
        self.entry_buscar.pack(side="left", padx=5)
        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)

        ctk.CTkButton(self.top_frame, text="CIERRE DE CAJA", fg_color="#FBC02D", 
                      text_color="black", command=self.ejecutar_cierre_desde_interfaz, 
                      width=150).pack(side="left", padx=20)
        
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
        columnas = ("Cant", "Producto", "Precio $", "Subtotal $")
        self.tree = ttk.Treeview(self, columns=columnas, show="headings", height=15)
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100 if "Producto" not in col else 300)
        self.tree.pack(fill="both", expand=True, pady=10)

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

        # --- PANEL INFERIOR: TOTALES Y ACCIONES ---
        panel_inf = ctk.CTkFrame(self, fg_color="transparent")
        panel_inf.pack(fill="x", side="bottom", pady=10)

        self.lbl_total = ctk.CTkLabel(panel_inf, text="TOTAL: $ 0.00", font=("Arial", 28, "bold"), text_color="#00E676")
        self.lbl_total.pack(side="left", padx=20)

        self.lbl_total_bs = ctk.CTkLabel(panel_inf, text="0.00 Bs", font=("Arial", 20), text_color="orange")
        self.lbl_total_bs.pack(side="left", padx=10)

        ctk.CTkButton(panel_inf, text="VACIAR", fg_color="#FF1744", command=self.vaciar_carrito, width=100).pack(side="right", padx=10)
        ctk.CTkButton(panel_inf, text="ELIMINAR PRODUCTO", fg_color="#D32F2F", command=self.eliminar_item_seleccionado, width=120).pack(side="right", padx=10)
        ctk.CTkButton(panel_inf, text="PROCESAR PAGO", fg_color="#2979FF", command=self.cobrar, height=45, font=("Arial", 14, "bold")).pack(side="right", padx=10)

    # --- MÉTODO PARA EL CIERRE ---
    def ejecutar_cierre_desde_interfaz(self):
        try:
            archivo = realizar_cierre() # <--- Si esto falla, el botón se bloquea
            messagebox.showinfo("Cierre Exitoso", f"El reporte se generó en: {archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el cierre: {e}")

    # --- LÓGICA DE BÚSQUEDA Y CARRITO ---

    def _filtrar_busqueda_combo(self, event):
        # Cancelar la búsqueda anterior si existe
        if hasattr(self, '_after_id'):
            self.after_cancel(self._after_id)
        
        # Programar la búsqueda para dentro de 200ms
        self._after_id = self.after(200, self._ejecutar_busqueda_real)

    def _ejecutar_busqueda_real(self):
        texto = self.entry_buscar.get().strip()
        if len(texto) < 2:
            self.lista_sugerencias.place_forget()
            return

        productos = self.app.db.consultar_producto_rapido(texto)
        
        self.lista_sugerencias.delete(0, tk.END)
        if productos:
            for p in productos:
                self.lista_sugerencias.insert(tk.END, f"{p[0]} | ${p[1]} | Stock: {p[2]}")
            
            # 1. Calculamos la posición
            x_pos = self.entry_buscar.winfo_x()
            y_pos = self.entry_buscar.winfo_y() + self.entry_buscar.winfo_height()
            
            # 2. La mostramos
            self.lista_sugerencias.place(x=x_pos, y=y_pos)
            
            # 3. EL TRUCO: La traemos al frente de la tabla
            self.lista_sugerencias.lift() 
        else:
            self.lista_sugerencias.place_forget()

    def agregar_desde_lista(self, event):
        seleccion = self.lista_sugerencias.curselection()
        if not seleccion: return
        
        item_texto = self.lista_sugerencias.get(seleccion[0])
        nombre_prod = item_texto.split(" | ")[0]
        
        # Obtenemos datos frescos de ese producto
        res = self.app.db.consultar_producto_rapido(nombre_prod)
        if res:
            p = res[0]
            self.agregar_al_carrito(p[0], float(p[1]), p[2])
        
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

    def agregar_al_carrito(self, nombre, precio, stock_max):
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
        tipo = ctk.CTkComboBox(frame_pago, values=["Pago Móvil", "Transferencia", "Biopago", "Efectivo"], width=120)
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

        def agregar_fila(metodo):
            f = ctk.CTkFrame(scroll, fg_color="#333333")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=metodo, width=80).pack(side="left", padx=5)
            monto = ctk.CTkEntry(f, placeholder_text="Bs", width=80)
            monto.bind("<KeyRelease>", actualizar_calculadora)
            monto.pack(side="left", padx=5)
            ref = ctk.CTkEntry(f, placeholder_text="Ref", width=80)
            ref.pack(side="left", padx=5)
            self.lista_dinamica.append({'tipo': metodo, 'monto': monto, 'ref': ref})

        ctk.CTkButton(vent_pago, text="➕ Agregar PM o Transf", command=lambda: agregar_fila("Pago Móvil")).pack(pady=5)

        def finalizar():
            try:
                m_usd = parse_monto(entradas['efectivo_usd'].get()) * self.app.tasa
                m_bs = parse_monto(entradas['efectivo_bs'].get())
                m_bio = parse_monto(entradas['bio'].get())
                m_punto = parse_monto(entradas['punto'].get())
                
                detalles_list = [f"Efectivo $: {entradas['efectivo_usd'].get()}", f"Efectivo Bs: {entradas['efectivo_bs'].get()}", f"Bio: {entradas['bio'].get()}", f"Punto: {entradas['punto'].get()}"]
                total_p = m_usd + m_bs + m_bio + m_punto
                
                for p in self.lista_dinamica:
                    m = parse_monto(p['monto'].get())
                    r = p['ref'].get().strip()
                    if m > 0:
                        if not r:
                            messagebox.showerror("Error", f"Falta referencia en {p['tipo']}")
                            return
                        total_p += m
                        detalles_list.append(f"{p['tipo']}: {m}Bs (Ref: {r})")

                if total_p < (total_bs - 0.01):
                    messagebox.showerror("Error", "Monto insuficiente")
                    return

                metodo_detalle = " | ".join(detalles_list)
                datos_v = {'total_usd': total_usd, 'metodo': metodo_detalle}
                
                # GUARDADO CON EL ID DEL CLIENTE SELECCIONADO
                id_v = self.app.db.crear_venta(datos_v, self.app.usuario_actual[0], cliente[0], self.app.tasa)
                
                if id_v:
                    for nom, d in self.app.carrito.items():
                        # 1. Registro del ítem
                        self.app.db.registrar_item_venta(id_v, nom, d['cant'], d['precio'], float(d['precio'])*int(d['cant']))
                        
                        # 2. Descuento de stock con validación de consola
                        print(f"DEBUG: Intentando descontar {d['cant']} de producto '{nom}'")
                        # Debes obtener el código del producto desde 'd' (si tu carrito guarda el código)
                        resultado = self.app.db.descontar_stock(nom, d['cant'])
                        
                        if resultado is False: # O el valor que retorne tu función cuando falla
                            messagebox.showerror("Error", f"No se pudo descontar el stock de {nom}")
                            return
                    
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

        ctk.CTkButton(vent_pago, text="CONFIRMAR COBRO", fg_color="green", command=finalizar).pack(pady=20)
        self.lista_pagos = []

def sumar_pagos(self):
    total = 0
    for p in self.lista_pagos:
        total += parse_monto(p["monto"].get())
    return total