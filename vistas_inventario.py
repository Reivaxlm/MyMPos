import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog

class InventarioFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.actualizar_tabla()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        
        # BARRA DE HERRAMIENTAS
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=5)
        
        ctk.CTkButton(toolbar, text="+ AGREGAR PRODUCTO", fg_color="#2979FF", 
                      command=self.nuevo_producto).pack(side="left", padx=5)
        
        self.ent_buscar = ctk.CTkEntry(toolbar, placeholder_text="Buscar en inventario...")
        self.ent_buscar.pack(side="right", fill="x", expand=True, padx=5)
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.actualizar_tabla(self.ent_buscar.get()))

        # TABLA (TU MECANISMO DE COLUMNAS)
        self.tree = ttk.Treeview(self, columns=("ID", "Cod", "Nom", "Costo", "Venta", "Stock"), show="headings")
        for c in ("ID", "Cod", "Nom", "Costo", "Venta", "Stock"): 
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100)
        self.tree.pack(fill="both", expand=True, pady=10)
        
        # Botones de edición
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="EDITAR SELECCIONADO", fg_color="orange", text_color="black",
                      command=self.editar_producto).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="ELIMINAR", fg_color="#FF1744", 
                      command=self.eliminar_producto).pack(side="right", padx=5)

    def actualizar_tabla(self, filtro=""):
        for i in self.tree.get_children(): self.tree.delete(i)
        # Usamos tu método original de la DB
        productos = self.app.db.buscar_productos_por_texto(filtro)
        for p in productos:
            self.tree.insert("", "end", values=p)

    def nuevo_producto(self):
        # Aquí va tu lógica de simpledialog o ventana Toplevel para insertar en la DB
        # self.app.db.insertar_producto(...)
        pass

    def editar_producto(self):
        seleccion = self.tree.focus()
        if not seleccion: return
        valores = self.tree.item(seleccion, "values")
        # Tu lógica original para editar basándote en el ID (valores[0])
        pass

    def eliminar_producto(self):
        seleccion = self.tree.focus()
        if not seleccion: return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar este producto?"):
            id_p = self.tree.item(seleccion, "values")[0]
            self.app.db.eliminar_producto(id_p)
            self.actualizar_tabla()