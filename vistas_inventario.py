import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog, filedialog
import pandas as pd

class InventarioFrame(ctk.CTkFrame):
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
            font=("Segoe UI", 11)
        )
        style.map("Treeview", background=[('selected', '#AA00FF')])
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 11, "bold")
        )

        # BARRA DE HERRAMIENTAS
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 15))
        
        ctk.CTkButton(toolbar, text="📦 + AGREGAR PRODUCTO", fg_color="#AA00FF", hover_color="#7B1FA2",
                      height=40, font=("Segoe UI", 14, "bold"), corner_radius=8,
                      command=self.nuevo_producto).pack(side="left", padx=5)
        
        ctk.CTkButton(toolbar, text="⚠️ EXPORTAR BAJO STOCK", fg_color="#D32F2F", hover_color="#B71C1C",
                      height=40, font=("Segoe UI", 14, "bold"), corner_radius=8,
                      command=self.exportar_bajo_stock).pack(side="left", padx=5)
        
        busqueda_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        busqueda_frame.pack(side="right", fill="x", expand=True, padx=5)

        ctk.CTkLabel(busqueda_frame, text="🔍", font=("Segoe UI", 18)).pack(side="left", padx=(10, 5))
        self.ent_buscar = ctk.CTkEntry(busqueda_frame, placeholder_text="Buscar en inventario...",
                                       height=40, font=("Segoe UI", 14), corner_radius=8)
        self.ent_buscar.pack(side="left", fill="x", expand=True)
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.actualizar_tabla(self.ent_buscar.get()))

        # TABLA (TU MECANISMO DE COLUMNAS)
        # Contenedor para la tabla
        tabla_container = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=10)
        tabla_container.pack(fill="both", expand=True, pady=10)

        todas_las_columnas = ("ID", "Cod", "Nom", "Costo $", "Precio C/U", "Stock", "Vendidos")
        columnas_visibles = ("Cod", "Nom", "Costo $", "Precio C/U", "Stock", "Vendidos")
        
        self.tree = ttk.Treeview(tabla_container, columns=todas_las_columnas, displaycolumns=columnas_visibles, show="headings")
        
        for c in todas_las_columnas: 
            self.tree.heading(c, text=c)
            # Acoples de ancho de columnas
            if c == "Nom":
                width, anchor = 250, "w"
            elif c == "Cod":
                width, anchor = 120, "center"
            else:
                width, anchor = 80, "center"
            
            self.tree.column(c, width=width, anchor=anchor)
            
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Botones de edición
        btns = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=15, height=70)
        btns.pack(fill="x", pady=(10, 0))
        btns.pack_propagate(False)

        ctk.CTkButton(btns, text="✏️ EDITAR SELECCIONADO", fg_color="#FFB300", hover_color="#FF8F00", text_color="black",
                      font=("Segoe UI", 14, "bold"), height=40, corner_radius=8,
                      command=self.editar_producto).pack(side="left", padx=20, pady=15)
                      
        ctk.CTkButton(btns, text="🗑️ ELIMINAR", fg_color="#D32F2F", hover_color="#B71C1C", text_color="white",
                      font=("Segoe UI", 14, "bold"), height=40, corner_radius=8,
                      command=self.eliminar_producto).pack(side="right", padx=20, pady=15)

    def actualizar_tabla(self, filtro=""):
        for i in self.tree.get_children(): self.tree.delete(i)
        # Usamos tu método original de la DB
        productos = self.app.db.buscar_productos_por_texto(filtro)
        for p in productos:
            self.tree.insert("", "end", values=p)

    def nuevo_producto(self):
        self.abrir_ventana_producto("Nuevo Producto")

    def editar_producto(self):
        seleccion = self.tree.focus()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un producto para editar.")
            return
        valores = self.tree.item(seleccion, "values")
        
        # Necesitamos todos los datos del producto (categoría y stock mínimo a menudo no están en la vista rápida)
        # Consultamos el producto completo usando el código de barras (valores[1])
        producto_completo = self.app.db.get_producto_por_codigo(valores[1])
        
        if producto_completo:
            self.abrir_ventana_producto("Editar Producto", producto_completo)
        else:
            messagebox.showerror("Error", "No se pudo cargar la información completa del producto.")

    def abrir_ventana_producto(self, titulo, producto_data=None):
        vent = ctk.CTkToplevel(self)
        vent.title(titulo)
        vent.geometry("400x550")
        vent.grab_set()
        
        # Centrar la ventana
        vent.update_idletasks()
        x = (vent.winfo_screenwidth() // 2) - (400 // 2)
        y = (vent.winfo_screenheight() // 2) - (550 // 2)
        vent.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(vent, text=titulo, font=("Segoe UI", 20, "bold")).pack(pady=(20, 10))
        
        # Frame contenedor
        frame_form = ctk.CTkFrame(vent, fg_color="transparent")
        frame_form.pack(fill="both", expand=True, padx=30)
        
        # Campos
        entradas = {}
        campos = [
            ("codigo", "Código de Barras"),
            ("nombre", "Nombre/Descripción"),
            ("costo", "Costo ($)"),
            ("venta", "Precio Venta ($)"),
            ("stock", "Stock Actual"),
            ("minimo", "Stock Mínimo"),
            ("categoria", "Categoría")
        ]
        
        for clave, placeholder in campos:
            ent = ctk.CTkEntry(frame_form, placeholder_text=placeholder, height=35)
            ent.pack(fill="x", pady=7)
            entradas[clave] = ent
            
        # Si estamos editando, rellenar los datos
        # Asume que el producto viene de la DB: (id, codigo, nombre, costo, venta, stock, min, cat)
        codigo_original = None
        if producto_data:
            codigo_original = producto_data[1]  # Guardar el código original para el UPDATE
            
            entradas["codigo"].insert(0, str(producto_data[1]))
            entradas["nombre"].insert(0, str(producto_data[2]))
            entradas["costo"].insert(0, str(producto_data[3]))
            entradas["venta"].insert(0, str(producto_data[4]))
            entradas["stock"].insert(0, str(producto_data[5]))
            entradas["minimo"].insert(0, str(producto_data[6]))
            entradas["categoria"].insert(0, str(producto_data[7]) if producto_data[7] else "")
            
        def guardar():
            # Validación básica
            if not entradas["codigo"].get() or not entradas["nombre"].get():
                messagebox.showerror("Error", "Código y Nombre son obligatorios.", parent=vent)
                return
                
            try:
                # 1: código_barras, 2: nombre, 3: precio_compra, 4: precio_venta, 5: stock, 6: stock_minimo, 7: categoria
                datos = (
                    entradas["codigo"].get(),
                    entradas["nombre"].get().upper(),
                    float(entradas["costo"].get() or 0),
                    float(entradas["venta"].get() or 0),
                    float(entradas["stock"].get() or 0),
                    int(entradas["minimo"].get() or 0),
                    entradas["categoria"].get().upper()
                )
                
                if producto_data:
                    # EDITAR
                    datos_update = (
                        entradas["nombre"].get().upper(),
                        float(entradas["costo"].get() or 0),
                        float(entradas["venta"].get() or 0),
                        float(entradas["stock"].get() or 0),
                        int(entradas["minimo"].get() or 0),
                        entradas["categoria"].get().upper(),
                        codigo_original # El WHERE
                    )
                    
                    if self.app.db.actualizar_producto(datos_update):
                        messagebox.showinfo("Éxito", "Producto actualizado.", parent=vent)
                        vent.destroy()
                        self.actualizar_tabla(self.ent_buscar.get())
                    else:
                        messagebox.showerror("Error", "No se pudo actualizar.", parent=vent)
                else:
                    # NUEVO
                    if self.app.db.registrar_producto(datos):
                        messagebox.showinfo("Éxito", "Producto creado.", parent=vent)
                        vent.destroy()
                        self.actualizar_tabla(self.ent_buscar.get())
                    else:
                        messagebox.showerror("Error", "No se pudo crear (El código podría estar duplicado).", parent=vent)
            except ValueError:
                messagebox.showerror("Error", "Formato numérico inválido.", parent=vent)
                
        # Botones de acción
        frame_btns = ctk.CTkFrame(vent, fg_color="transparent")
        frame_btns.pack(fill="x", pady=20, padx=30)
        
        ctk.CTkButton(frame_btns, text="Cancelar", fg_color="#333", command=vent.destroy, width=120).pack(side="left")
        ctk.CTkButton(frame_btns, text="💾 Guardar", fg_color="#2979FF", command=guardar, width=120).pack(side="right")

    def eliminar_producto(self):
        seleccion = self.tree.focus()
        if not seleccion: return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este producto?"):
            id_p = self.tree.item(seleccion, "values")[0]
            self.app.db.eliminar_producto(id_p)
            self.actualizar_tabla()

    def exportar_bajo_stock(self):
        """Exporta a Excel los productos que están por debajo de su stock mínimo"""
        datos = self.app.db.obtener_productos_bajo_stock()
        
        if not datos:
            messagebox.showinfo("Inventario al día", "No hay productos con stock bajo actualmente.")
            return

        archivo = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                            initialfile=f"Bajo_Stock_{pd.Timestamp.now().strftime('%d_%m_%Y')}",
                                            filetypes=[("Excel", "*.xlsx")])
        if archivo:
            try:
                # datos viene como: (id, cod, nombre, stock, min)
                columnas = ["ID", "Código", "Producto", "Stock Actual", "Stock Mínimo"]
                df = pd.DataFrame(datos, columns=columnas)
                df.to_excel(archivo, index=False)
                messagebox.showinfo("Éxito", f"Se han exportado {len(datos)} productos correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {e}")