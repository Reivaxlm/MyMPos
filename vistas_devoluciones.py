import customtkinter as ctk
from tkinter import ttk, messagebox
import datetime

class DevolucionesFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="#121212")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10), padx=20)
        
        ctk.CTkLabel(header, text="📑 CENTRO DE DEVOLUCIONES Y RECLAMOS", 
                      font=("Segoe UI", 24, "bold"), text_color="#FF5252").pack(side="left")

        # Botón de volver al home
        ctk.CTkButton(header, text="⬅ Volver", width=80, fg_color="#333333", 
                      command=self.app.mostrar_dashboard).pack(side="right")

        # Buscador superior
        search_f = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=15, height=80)
        search_f.pack(fill="x", padx=20, pady=10)
        search_f.pack_propagate(False)
        
        ctk.CTkLabel(search_f, text="BUSCAR VENTA (ID o NOMBRE):", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(20, 10))
        self.ent_id = ctk.CTkEntry(search_f, placeholder_text="Ej: 154 o Juan Perez", width=300, height=40)
        self.ent_id.pack(side="left", padx=10)
        self.ent_id.bind("<Return>", lambda e: self.buscar_venta())
        
        ctk.CTkButton(search_f, text="🔍 BUSCAR TICKET", font=("Segoe UI", 13, "bold"),
                      fg_color="#FF5252", hover_color="#D32F2F", width=150, height=40,
                      command=self.buscar_venta).pack(side="left", padx=10)

        # Contenedor Principal (Dos columnas)
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=10)

        # Columna Izquierda: Detalles del Pago
        self.left_col = ctk.CTkFrame(self.content, fg_color="#1A1A1A", corner_radius=15, width=350)
        self.left_col.pack(side="left", fill="both", padx=(0, 10))
        self.left_col.pack_propagate(False)
        
        ctk.CTkLabel(self.left_col, text="DATOS DE LA VENTA", font=("Segoe UI", 16, "bold"), text_color="#AAAAAA").pack(pady=20)
        
        self.info_frame = ctk.CTkFrame(self.left_col, fg_color="transparent")
        self.info_frame.pack(fill="both", expand=True, padx=20)
        
        # Columna Derecha: Lista de Artículos
        self.right_col = ctk.CTkFrame(self.content, fg_color="#1A1A1A", corner_radius=15)
        self.right_col.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.right_col, text="ARTÍCULOS EN EL TICKET", font=("Segoe UI", 16, "bold"), text_color="#AAAAAA").pack(pady=20)
        
        # --- ESTILO DE TABLA ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dev.Treeview", 
                        background="#2b2b2b", 
                        foreground="white", 
                        fieldbackground="#2b2b2b", 
                        bordercolor="#2b2b2b",
                        borderwidth=0,
                        rowheight=35)
        style.configure("Dev.Treeview.Heading", background="#333333", foreground="white", relief="flat")
        style.map("Dev.Treeview", background=[('selected', '#FF5252')])

        # Barra inferior de acción
        action_f = ctk.CTkFrame(self.right_col, fg_color="transparent", height=80)
        action_f.pack(fill="x", side="bottom", padx=20, pady=20)
        
        self.btn_procesar = ctk.CTkButton(action_f, text="GESTIONAR DEVOLUCIÓN / TRAMITAR CAMBIO", 
                                          font=("Segoe UI", 15, "bold"),
                                          fg_color="#D32F2F", text_color="white", height=50,
                                          state="disabled", command=self.confirmar_devolucion)
        self.btn_procesar.pack(fill="x", expand=True)

        self.tree_f = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.tree_f.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        self.tree = ttk.Treeview(self.tree_f, columns=("ID", "PROD", "CANT", "PRECIO", "TOTAL"), show="headings", style="Dev.Treeview")
        for col in ("ID", "PROD", "CANT", "PRECIO", "TOTAL"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=80)
        self.tree.column("PROD", width=250, anchor="w")
        self.tree.pack(fill="both", expand=True)

    def buscar_venta(self):
        busqueda = self.ent_id.get().strip()
        if not busqueda: return
        
        venta = None
        if busqueda.isdigit() or busqueda.upper().startswith("MYM"):
            venta = self.app.db.obtener_venta(busqueda)
        
        if not venta:
            ventas_nom = self.app.db.buscar_ventas_por_cliente(busqueda)
            if not ventas_nom:
                messagebox.showerror("Error", "No se encontró ningún ticket con el ID o Cliente indicado.")
                return
            
            if len(ventas_nom) > 1:
                msg = "Se encontraron varias ventas. Por favor ingrese el ID exacto:\n\n"
                for v in ventas_nom:
                    msg += f"ID: {v[0]} - Fecha: {v[1].strftime('%d/%m')} - Cliente: {v[2]} - Total: ${v[3]}\n"
                
                nuevo_id = ctk.CTkInputDialog(text=msg, title="Múltiples Resultados").get_input()
                if nuevo_id and nuevo_id.isdigit():
                    venta = self.app.db.obtener_venta(nuevo_id)
                else: return
            else:
                venta = self.app.db.obtener_venta(ventas_nom[0][0])

        if not venta:
            messagebox.showerror("Error", "Venta no encontrada.")
            return

        for w in self.info_frame.winfo_children(): w.destroy()
        for item in self.tree.get_children(): self.tree.delete(item)
        
        self.lbl_id = self.add_info("📝 TICKET #", str(venta[0]))
        self.lbl_fecha = self.add_info("📅 FECHA", str(venta[1].strftime('%d/%m/%Y %H:%M')))
        self.lbl_cliente = self.add_info("👤 CLIENTE", str(venta[6] or "Gral"))
        metodo_raw = str(venta[3])
        # Limpiar metodos vacios (ej: "Bio: | Punto:" -> "")
        partes = [p.strip() for p in metodo_raw.split('|')]
        metodo_limpio = " | ".join([p for p in partes if len(p.split(':')) > 1 and p.split(':')[1].strip()])
        
        self.lbl_metodo = self.add_info("💳 MÉTODO", metodo_limpio or "No especificado")
        self.lbl_total = self.add_info("💰 TOTAL PAGADO", f"${float(venta[2]):,.2f}", "#FFD600")

        items = self.app.db.obtener_items_venta(venta[0])
        if not items:
            self.tree.insert("", "end", values=("", "⚠️ TICKET SIN DETALLES (ANTIGUO)", "", "", ""))
            self.btn_procesar.configure(state="disabled")
        else:
            for p_id, cant, precio, sub in items:
                prod = self.app.db.get_producto_por_id(p_id)
                nombre = prod[2] if prod else "Desconocido"
                self.tree.insert("", "end", values=(p_id, nombre, int(cant), f"${float(precio):,.2f}", f"${float(sub):,.2f}"))
            self.btn_procesar.configure(state="normal")
        
        self.current_venta_id = venta[0]

    def add_info(self, label, value, color="white"):
        f = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        f.pack(fill="x", pady=5)
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 11, "bold"), text_color="#888").pack(anchor="w")
        
        # Si el texto es muy largo (ej: muchos métodos), bajamos la fuente y activamos wrap
        val_str = str(value)
        f_size = 14 if len(val_str) < 25 else 12
        
        l = ctk.CTkLabel(f, text=val_str, font=("Segoe UI", f_size, "bold"), 
                         text_color=color, wraplength=300, justify="left")
        l.pack(anchor="w")
        return l

    def confirmar_devolucion(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un artículo de la lista.")
            return
        
        item_data = self.tree.item(sel[0], "values")
        p_id, nombre, cant_max = item_data[0], item_data[1], int(item_data[2])
        precio_antiguo = float(item_data[3].replace("$", "").replace(",", ""))
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gestionar Operación")
        dialog.geometry("450x550")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"OPERACIÓN CON: {nombre}", font=("Segoe UI", 16, "bold"), text_color="#FF5252").pack(pady=20)
        
        ctk.CTkLabel(dialog, text="1. Elija la cantidad a procesar:", font=("Segoe UI", 12)).pack()
        ent_cant = ctk.CTkEntry(dialog, width=100, placeholder_text=str(cant_max))
        ent_cant.pack(pady=5)
        ent_cant.insert(0, str(cant_max))
        
        ctk.CTkLabel(dialog, text="2. Seleccione el tipo de trámite:", font=("Segoe UI", 12)).pack(pady=(15,0))
        tipo_var = ctk.StringVar(value="DEVOLUCIÓN")
        ctk.CTkOptionMenu(dialog, values=["DEVOLUCIÓN (Reembolso)", "CAMBIO (Por otro Item)"], variable=tipo_var).pack(pady=10)
        
        # Frame para búsqueda de nuevo producto (solo si es cambio)
        cambio_frame = ctk.CTkFrame(dialog, fg_color="#1A1A1A", corner_radius=10)
        
        self.new_p_id = None
        self.new_p_precio = 0.0
        
        lbl_new = ctk.CTkLabel(cambio_frame, text="Busque el nuevo producto:", font=("Segoe UI", 11, "bold"))
        lbl_new.pack(pady=5)
        ent_new = ctk.CTkEntry(cambio_frame, placeholder_text="Nombre o Código...", width=300)
        ent_new.pack(pady=5)
        
        lbl_res = ctk.CTkLabel(cambio_frame, text="Seleccione resultado:", text_color="gray")
        lbl_res.pack()
        combo_res = ctk.CTkOptionMenu(cambio_frame, values=["Escriba para buscar..."], width=300)
        combo_res.pack(pady=10)
        
        lbl_diff = ctk.CTkLabel(dialog, text="DIFERENCIA A COBRAR: $0.00", font=("Segoe UI", 18, "bold"), text_color="#FFD600")
        
        def on_tipo_change(*args):
            if tipo_var.get().startswith("CAMBIO"):
                cambio_frame.pack(fill="x", padx=20, pady=10)
                lbl_diff.pack(pady=20)
            else:
                cambio_frame.pack_forget()
                lbl_diff.pack_forget()
        
        tipo_var.trace_add("write", on_tipo_change)
        
        def buscar_nuevo_item(e):
            txt = ent_new.get().strip()
            if len(txt) < 2: return
            res = self.app.db.consultar_producto_rapido(txt)
            if res:
                self.res_map = {f"{r[0]} - ${r[1]:,.2f} (Stock: {r[2]})": r for r in res}
                combo_res.configure(values=list(self.res_map.keys()))
                combo_res.set(list(self.res_map.keys())[0])
                actualizar_cálculos()
        
        ent_new.bind("<KeyRelease>", buscar_nuevo_item)
        
        def actualizar_cálculos(*args):
            try:
                c = int(ent_cant.get() or 0)
                if tipo_var.get().startswith("CAMBIO"):
                    sel_new = combo_res.get()
                    if sel_new in self.res_map:
                        p_data = self.res_map[sel_new]
                        self.new_p_id = p_data[0] # Esto asume que consultar_producto_rapido retorna ID, pero verifiquemos
                        # Si consultar_producto_rapido retorna (nombre, precio, stock), necesitamos el ID.
                        # Corregiré Database si hace falta o buscaré por nombre.
                        self.new_p_precio = float(p_data[1])
                        
                        monto_dev = precio_antiguo * c
                        monto_nuevo = self.new_p_precio * c
                        diff = monto_nuevo - monto_dev
                        
                        if diff >= 0:
                            lbl_diff.configure(text=f"DIFERENCIA A COBRAR: ${diff:,.2f}", text_color="#00E676")
                        else:
                            lbl_diff.configure(text=f"CLIENTE A FAVOR: ${abs(diff):,.2f}", text_color="#FFD600")
                else:
                    lbl_diff.configure(text="DIFERENCIA: $0.00")
            except: pass

        combo_res.configure(command=actualizar_cálculos)
        ent_cant.bind("<KeyRelease>", actualizar_cálculos)

        def ejecutar():
            try:
                c = int(ent_cant.get() or 0)
                if c <= 0 or c > cant_max:
                    messagebox.showerror("Error", f"Cantidad inválida. Máximo {cant_max}")
                    return
            except: return

            if tipo_var.get().startswith("DEVOLUCIÓN"):
                # Caso Devolución Simple
                if messagebox.askyesno("Confirmar", "¿Procesar reembolso y reintegrar stock?"):
                    self.app.db.registrar_devolucion(self.current_venta_id, p_id, c, "Devolución Simple", self.app.usuario_actual[0])
                    messagebox.showinfo("Éxito", "Devolución procesada.")
                    dialog.destroy()
                    self.buscar_venta()
            else:
                # Caso Cambio
                sel_new = combo_res.get()
                if sel_new not in getattr(self, "res_map", {}):
                    messagebox.showerror("Error", "Seleccione un producto nuevo válido.")
                    return
                
                p_new_data = self.res_map[sel_new]
                # Buscar el ID real si no viene en consultar_producto_rapido
                p_real = self.app.db.buscar_producto(p_new_data[0])
                if not p_real: 
                    messagebox.showerror("Error", "No se pudo recuperar el ID del nuevo producto.")
                    return
                
                # p_real: (codigo, nombre, precio, stock) -> Necesitamos el ID interno
                # Usaremos buscar_producto_precios que sí retorna ID
                p_id_data = self.app.db.buscar_producto_precios(p_new_data[0])
                if not p_id_data: return
                p_nuevo_id = p_id_data[0][0]
                
                if messagebox.askyesno("Confirmar Cambio", f"Se cambiará {c}x {nombre} por {c}x {p_new_data[0]}.\n¿Continuar?"):
                    # 1. Regresar stock del viejo
                    self.app.db.registrar_devolucion(self.current_venta_id, p_id, c, f"Cambio por {p_new_data[0]}", self.app.usuario_actual[0])
                    # 2. Descontar stock del nuevo
                    # Usamos un método de stock existente
                    self.app.db.descontar_stock(p_new_data[0], c)
                    
                    messagebox.showinfo("Éxito", "Cambio realizado correctamente.")
                    dialog.destroy()
                    self.buscar_venta()

        ctk.CTkButton(dialog, text="✅ FINALIZAR TRÁMITE", font=("Segoe UI", 14, "bold"),
                      fg_color="#00E676", text_color="black", height=45, command=ejecutar).pack(pady=20)
