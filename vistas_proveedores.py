import customtkinter as ctk
from tkinter import messagebox, ttk

class ProveedoresFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Título
        ctk.CTkLabel(self, text="Directorio de Proveedores", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        # Formulario
        form = ctk.CTkFrame(self)
        form.pack(pady=10, padx=20, fill="x")
        
        self.ent_nombre = ctk.CTkEntry(form, placeholder_text="Nombre del Proveedor")
        self.ent_nombre.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        self.ent_prod = ctk.CTkEntry(form, placeholder_text="Producto principal")
        self.ent_prod.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        ctk.CTkButton(form, text="Guardar", fg_color="green", command=self.guardar_proveedor).pack(side="left", padx=10)
        
        # Tabla (Treeview)
        self.tree = ttk.Treeview(self, columns=("ID", "Nombre", "Producto"), show="headings")
        self.tree.heading("ID", text="ID"); self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Producto", text="Producto"); self.tree.pack(pady=10, padx=20, fill="both", expand=True)
        self.cargar_datos()

    def guardar_proveedor(self):
        query = "INSERT INTO public.proveedores (nombre, producto_principal) VALUES (%s, %s)"
        self.app.db.execute(query, (self.ent_nombre.get(), self.ent_prod.get()))
        self.cargar_datos()
        messagebox.showinfo("Éxito", "Proveedor registrado")

    def cargar_datos(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        data = self.app.db.fetchall("SELECT * FROM public.proveedores")
        for row in data: self.tree.insert("", "end", values=row)