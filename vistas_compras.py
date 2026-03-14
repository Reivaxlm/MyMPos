import customtkinter as ctk
from tkinter import ttk, messagebox

class ComprasFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="#121212")
        self.app = app
        self.pack(fill="both", expand=True)
        self.producto_seleccionado = None
        self.setup_ui()

    def setup_ui(self):
        # Título
        ctk.CTkLabel(self, text="ENTRADA DE MERCANCÍA (COMPRAS)", font=("Segoe UI", 24, "bold"), text_color="#00E676").pack(pady=20)

        # Contenedor Principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=40)

        # IZQUIERDA: Buscador y Selección
        left_panel = ctk.CTkFrame(main_container, fg_color="#1A1A1A", corner_radius=15, border_width=1, border_color="#333333")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        ctk.CTkLabel(left_panel, text="1. BUSCAR PRODUCTO", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        search_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        search_frame.pack(fill="x", padx=20)
        
        self.ent_buscar = ctk.CTkEntry(search_frame, placeholder_text="Nombre o Código...", height=40, font=("Segoe UI", 14))
        self.ent_buscar.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.buscar_productos())

        # Tabla de resultados rápida
        columnas = ("ID", "Producto", "Stock Actual", "Costo Actual")
        self.tree = ttk.Treeview(left_panel, columns=columnas, show="headings", height=10)
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.column("Producto", width=200, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_product_select)

        # DERECHA: Formulario de Entrada
        right_panel = ctk.CTkFrame(main_container, fg_color="#1A1A1A", corner_radius=15, border_width=1, border_color="#333333", width=350)
        right_panel.pack(side="right", fill="both", padx=(10, 0), pady=10)
        right_panel.pack_propagate(False)

        ctk.CTkLabel(right_panel, text="2. REGISTRAR ENTRADA", font=("Segoe UI", 16, "bold")).pack(pady=10)

        self.lbl_info = ctk.CTkLabel(right_panel, text="Seleccione un producto...", font=("Segoe UI", 14, "italic"), text_color="#AAAAAA", wraplength=300)
        self.lbl_info.pack(pady=20)

        # Campos de entrada
        self.form_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.form_frame.pack(fill="x", padx=30)

        ctk.CTkLabel(self.form_frame, text="Cantidad que entra:", font=("Segoe UI", 13)).pack(anchor="w")
        self.ent_cantidad = ctk.CTkEntry(self.form_frame, height=40, placeholder_text="Ej: 50")
        self.ent_cantidad.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(self.form_frame, text="Nuevo Costo Unitario ($):", font=("Segoe UI", 13)).pack(anchor="w")
        self.ent_costo = ctk.CTkEntry(self.form_frame, height=40, placeholder_text="Ej: 0.85")
        self.ent_costo.pack(fill="x", pady=(0, 20))

        self.btn_guardar = ctk.CTkButton(right_panel, text="✅ PROCESAR ENTRADA", font=("Segoe UI", 14, "bold"), 
                                         fg_color="#00E676", hover_color="#00C853", text_color="#000000",
                                         height=45, command=self.procesar_entrada, state="disabled")
        self.btn_guardar.pack(pady=20, padx=30, fill="x")

    def buscar_productos(self):
        busqueda = self.ent_buscar.get()
        # if len(busqueda) < 2: return
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        productos = self.app.db.buscar_productos_por_texto(busqueda, limit=15)
        for p in productos:
            # p: (id, cod, nombre, costo, venta, stock, vendidos)
            self.tree.insert("", "end", values=(p[0], p[2], p[5], f"${p[3]:.2f}"))

    def on_product_select(self, event):
        seleccion = self.tree.selection()
        if not seleccion: return
        
        item = self.tree.item(seleccion[0])
        valores = item['values']
        self.producto_seleccionado = {
            'id': valores[0],
            'nombre': valores[1],
            'stock': valores[2],
            'costo': valores[3]
        }
        
        self.lbl_info.configure(text=f"Producto: {self.producto_seleccionado['nombre']}\nStock actual: {self.producto_seleccionado['stock']}", 
                                text_color="#FFFFFF", font=("Segoe UI", 14, "bold"))
        self.btn_guardar.configure(state="normal")
        # Pre-llenar costo actual
        costo_limpio = str(self.producto_seleccionado['costo']).replace('$', '')
        self.ent_costo.delete(0, 'end')
        self.ent_costo.insert(0, costo_limpio)

    def procesar_entrada(self):
        if not self.producto_seleccionado: return
        
        cant_str = self.ent_cantidad.get()
        costo_str = self.ent_costo.get()
        
        try:
            cantidad = int(cant_str)
            costo = float(costo_str)
            if cantidad <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
            return

        confirmar = messagebox.askyesno("Confirmar", f"¿Desea ingresar {cantidad} unidades de '{self.producto_seleccionado['nombre']}' a un costo de ${costo:.2f}?")
        
        if confirmar:
            exito = self.app.db.aumentar_stock(self.producto_seleccionado['id'], cantidad, costo)
            if exito:
                messagebox.showinfo("Éxito", "Mercancía ingresada correctamente.")
                self.limpiar_formulario()
                self.buscar_productos() # Refrescar tabla
            else:
                messagebox.showerror("Error", "No se pudo actualizar el stock en la base de datos.")

    def limpiar_formulario(self):
        self.ent_cantidad.delete(0, 'end')
        self.ent_costo.delete(0, 'end')
        self.lbl_info.configure(text="Seleccione un producto...", text_color="#AAAAAA", font=("Segoe UI", 14, "italic"))
        self.btn_guardar.configure(state="disabled")
        self.producto_seleccionado = None
