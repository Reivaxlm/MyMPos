import customtkinter as ctk
from tkinter import ttk
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ReportesFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", pady=10)
        for t, r in [("HOY", "HOY"), ("SEMANA", "SEMANA"), ("MES", "MES")]:
            ctk.CTkButton(filtros, text=t, width=120, command=lambda r=r: self.cargar_dashboard(r)).pack(side="left", padx=5)

        # KPIs (Tarjetas)
        self.kpi_f = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_f.pack(fill="x", pady=10)
        self.lbl_total = ctk.CTkLabel(self.kpi_f, text="Venta: $0.00", font=("Arial", 20, "bold"))
        self.lbl_total.pack(side="left", padx=20)
        
        # Gráfica
        self.grafica_f = ctk.CTkFrame(self)
        self.grafica_f.pack(fill="both", expand=True, pady=10)

    def cargar_dashboard(self, rango):
        # 1. Definir fechas
        hoy = datetime.now()
        if rango == "HOY": i = f = hoy.strftime("%Y-%m-%d")
        elif rango == "SEMANA": i = (hoy - timedelta(days=7)).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")
        else: i = hoy.replace(day=1).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")

        # 2. Obtener datos
        resumen = self.app.db.obtener_resumen_kpi(i, f)
        productos = self.app.db.obtener_top_productos(i, f)

        # 3. Actualizar UI
        self.lbl_total.configure(text=f"Total Vendido: ${resumen[0] or 0:,.2f} | Operaciones: {resumen[1]}")
        
        # 4. Dibujar Gráfica
        for w in self.grafica_f.winfo_children(): w.destroy()
        fig, ax = plt.subplots(figsize=(5, 2), dpi=100)
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        ax.bar([p[0] for p in productos], [p[1] for p in productos], color='#2979FF')
        ax.tick_params(colors='white')
        
        canvas = FigureCanvasTkAgg(fig, master=self.grafica_f)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)