import customtkinter as ctk
from tkinter import messagebox, ttk

class ProveedoresFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.cargar_datos()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#1E1E1E",
            foreground="white",
            fieldbackground="#1E1E1E",
            rowheight=35,
            borderwidth=0,
            font=("Segoe UI", 11)
        )
        style.map("Treeview", background=[('selected', '#2979FF')])
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 12, "bold")
        )

        # Panel superior de registro
        top_panel = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=15)
        top_panel.pack(fill="x", pady=(0, 15))
        
        self.ent_nombre = ctk.CTkEntry(top_panel, placeholder_text="Nombre del Proveedor", height=45)
        self.ent_nombre.pack(side="left", padx=10, pady=15, expand=True, fill="x")
        
        self.ent_prod = ctk.CTkEntry(top_panel, placeholder_text="Producto Principal", height=45)
        self.ent_prod.pack(side="left", padx=10, pady=15, expand=True, fill="x")
        
        ctk.CTkButton(top_panel, text="➕ GUARDAR", fg_color="#2979FF", command=self.guardar_proveedor, height=45).pack(side="right", padx=15)

        # Tabla
        tabla_container = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=10)
        tabla_container.pack(fill="both", expand=True)

        columnas = ("ID", "Nombre", "Producto")
        self.tree = ttk.Treeview(tabla_container, columns=columnas, show="headings", style="Treeview")
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

    def guardar_proveedor(self):
        nombre = self.ent_nombre.get().strip()
        prod = self.ent_prod.get().strip()
        if not nombre: return
        
        try:
            query = "INSERT INTO public.proveedores (nombre, producto_principal) VALUES (%s, %s)"
            self.app.db.execute(query, (nombre, prod))
            self.cargar_datos()
            messagebox.showinfo("Éxito", "Proveedor registrado")
            self.ent_nombre.delete(0, 'end'); self.ent_prod.delete(0, 'end')
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def cargar_datos(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            data = self.app.db.fetchall("SELECT id, nombre, producto_principal FROM public.proveedores ORDER BY id DESC")
            for row in data: self.tree.insert("", "end", values=row)
        except: pass