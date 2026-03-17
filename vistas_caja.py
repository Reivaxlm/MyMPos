import customtkinter as ctk
from tkinter import messagebox, ttk

class CajaChicaFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.cargar_movimientos()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- ESTILO OSCURO PARA TABLA ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#1E1E1E",
            foreground="white",
            fieldbackground="#1E1E1E",
            rowheight=35,
            font=("Segoe UI", 11)
        )
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 12, "bold")
        )

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)

        # Formulario (Izquierda)
        form = ctk.CTkFrame(container, fg_color="#1E1E1E", width=320, corner_radius=15)
        form.pack(side="left", fill="y", padx=(0, 20))
        form.pack_propagate(False)
        
        ctk.CTkLabel(form, text="💵 CAJA CHICA", font=("Segoe UI", 20, "bold"), text_color="#FFB300").pack(pady=25)

        self.seg_button = ctk.CTkSegmentedButton(form, values=["Entrada", "Salida"], 
                                                 height=40, selected_color="#2979FF",
                                                 command=self.cambiar_modo)
        self.seg_button.pack(pady=10, padx=20, fill="x")
        self.seg_button.set("Entrada")

        self.combo_categoria = ctk.CTkOptionMenu(form, values=["Aporte de cambio", "Cobro de deuda"], height=45)
        self.combo_categoria.pack(pady=10, padx=20, fill="x")

        self.ent_monto = ctk.CTkEntry(form, placeholder_text="Monto ($)", height=45)
        self.ent_monto.pack(pady=10, padx=20, fill="x")

        self.ent_ref = ctk.CTkEntry(form, placeholder_text="Descripción", height=45)
        self.ent_ref.pack(pady=10, padx=20, fill="x")
       
        ctk.CTkButton(form, text="REGISTRAR", height=50, fg_color="#2979FF", 
                      font=("Segoe UI", 14, "bold"), command=self.guardar_movimiento).pack(pady=30, padx=20, fill="x")

        # Historial (Derecha)
        historial = ctk.CTkFrame(container, fg_color="#1E1E1E", corner_radius=15)
        historial.pack(side="right", fill="both", expand=True)
        
        columnas = ("Fecha", "Tipo", "Concepto", "Monto")
        self.tree = ttk.Treeview(historial, columns=columnas, show="headings", style="Treeview")
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def cambiar_modo(self, valor):
        if valor == "Entrada":
            self.combo_categoria.configure(values=["Aporte de cambio", "Cobro de deuda", "Otros"])
        else:
            self.combo_categoria.configure(values=["Pago proveedor", "Gasto operativo", "Retiro de seguridad"])
        self.combo_categoria.set(self.combo_categoria._values[0])

    def guardar_movimiento(self):
        try:
            monto = self.ent_monto.get()
            concepto = self.combo_categoria.get()
            tipo = self.seg_button.get().upper()
            usuario_id = self.app.usuario_actual[0] 
            
            if self.app.db.registrar_caja_chica(tipo, concepto, monto, usuario_id):
                messagebox.showinfo("Éxito", "Movimiento registrado")
                self.ent_monto.delete(0, 'end'); self.ent_ref.delete(0, 'end')
                self.cargar_movimientos()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def cargar_movimientos(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            data = self.app.db.fetchall("SELECT fecha, tipo, concepto, monto FROM public.caja_chica ORDER BY id DESC LIMIT 50")
            for row in data: self.tree.insert("", "end", values=row)
        except: pass