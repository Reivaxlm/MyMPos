import customtkinter as ctk
from tkinter import messagebox, ttk

class GastosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.actualizar_tabla()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- CONFIGURACIÓN DE ESTILO OSCURO PARA LA TABLA ---
        style = ttk.Style()
        style.theme_use("default") # Forzar tema base para poder modificarlo
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

        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True)

        # Panel Izquierdo (Formulario)
        form_card = ctk.CTkFrame(main_split, fg_color="#1E1E1E", width=300, corner_radius=15)
        form_card.pack(side="left", fill="y", padx=(0, 20))
        form_card.pack_propagate(False)
        
        ctk.CTkLabel(form_card, text="💸 NUEVO GASTO", font=("Segoe UI", 20, "bold"), text_color="#FF5252").pack(pady=25)
        
        self.desc = ctk.CTkEntry(form_card, placeholder_text="Descripción", height=40)
        self.desc.pack(pady=10, padx=20, fill="x")
        
        self.cat = ctk.CTkComboBox(form_card, values=["Renta", "Nómina", "Servicios", "Otros"], height=40)
        self.cat.pack(pady=10, padx=20, fill="x")
        
        self.monto = ctk.CTkEntry(form_card, placeholder_text="Monto $", height=40)
        self.monto.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkButton(form_card, text="REGISTRAR GASTO", fg_color="#D32F2F", hover_color="#B71C1C",
                      font=("Segoe UI", 14, "bold"), height=50,
                      command=self.registrar).pack(pady=30, padx=20, fill="x")

        # Panel Derecho (Tabla)
        table_panel = ctk.CTkFrame(main_split, fg_color="#1E1E1E", corner_radius=15)
        table_panel.pack(side="right", fill="both", expand=True)

        columnas = ("Fecha", "Categoría", "Descripción", "Monto")
        self.tree = ttk.Treeview(table_panel, columns=columnas, show="headings", style="Treeview")
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def registrar(self):
        try:
            monto_val = float(self.monto.get())
            query = "INSERT INTO public.gastos (descripcion, categoria, monto, fecha) VALUES (%s, %s, %s, CURRENT_DATE)"
            self.app.db.execute(query, (self.desc.get(), self.cat.get(), monto_val))
            messagebox.showinfo("Éxito", "Gasto registrado")
            self.desc.delete(0, 'end'); self.monto.delete(0, 'end')
            self.actualizar_tabla()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def actualizar_tabla(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            data = self.app.db.fetchall("SELECT fecha, categoria, descripcion, monto FROM public.gastos ORDER BY id DESC LIMIT 50")
            for row in data: self.tree.insert("", "end", values=row)
        except: pass