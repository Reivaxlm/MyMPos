import customtkinter as ctk
from tkinter import ttk
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ReportesFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="#121212")
        self.app = app
        self.pack(fill="both", expand=True)
        self.setup_ui()

    def setup_ui(self):
        # 1. Filtros Superiores
        f_header = ctk.CTkFrame(self, fg_color="transparent")
        f_header.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(f_header, text="PANEL ADMINISTRATIVO", font=("Segoe UI", 22, "bold")).pack(side="left")
        
        for t, r in [("HOY", "HOY"), ("7 DÍAS", "SEMANA"), ("MES", "MES")]:
            ctk.CTkButton(f_header, text=t, width=90, fg_color="#1e1e1e", border_width=1,
                          command=lambda r=r: self.cargar_dashboard(r)).pack(side="right", padx=5)

        # 2. Contenedor de Tarjetas (KPIs)
        self.cards_f = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_f.pack(fill="x", padx=20, pady=10)

        # 3. Contenedor Medio (Dos Gráficas)
        self.charts_container = ctk.CTkFrame(self, fg_color="transparent")
        self.charts_container.pack(fill="both", expand=True, padx=20)

        # 4. Tabla de Últimas Ventas (Abajo)
        self.table_f = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=15)
        self.table_f.pack(fill="x", padx=30, pady=20)
        
        self.cargar_dashboard("HOY")

    def cargar_dashboard(self, rango):
        # Lógica de fechas
        hoy = datetime.now()
        if rango == "HOY": i = f = hoy.strftime("%Y-%m-%d")
        elif rango == "SEMANA": i = (hoy - timedelta(days=7)).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")
        else: i = hoy.replace(day=1).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")

        # Datos
        total, cant = self.app.db.obtener_resumen_kpi(i, f)
        top_prod = self.app.db.obtener_top_productos(i, f)
        metodos = self.app.db.obtener_metodos_pago_pie(i, f)
        ultimas = self.app.db.obtener_ultimas_ventas_detalladas(i, f)

        # --- Actualizar KPIs ---
        for w in self.cards_f.winfo_children(): w.destroy()
        self.crear_card(self.cards_f, "TOTAL INGRESOS", f"${total:,.2f}", "#FFD600")
        self.crear_card(self.cards_f, "VENTAS REALIZADAS", str(cant), "#00E676")
        self.crear_card(self.cards_f, "TICKET MEDIO", f"${(total/cant if cant > 0 else 0):,.2f}", "#2979FF")

        # --- Dibujar Gráficas ---
        for w in self.charts_container.winfo_children(): w.destroy()
        
        # Gráfica 1: Barras (Productos)
        fig1, ax1 = plt.subplots(figsize=(4, 3), dpi=85, facecolor='#121212')
        ax1.set_facecolor('#1e1e1e')
        if top_prod:
            ax1.bar([p[0][:10] for p in top_prod], [p[1] for p in top_prod], color='#2979FF')
            ax1.set_title("TOP PRODUCTOS", color='white', size=10)
            ax1.tick_params(colors='white', labelsize=7)
        
        canvas1 = FigureCanvasTkAgg(fig1, master=self.charts_container)
        canvas1.get_tk_widget().pack(side="left", fill="both", expand=True, padx=5)

       # --- Gráfica 2: Torta (Métodos de Pago) ---
        fig2, ax2 = plt.subplots(figsize=(5, 4), dpi=85, facecolor='#121212')
        
        if metodos:
            nombres = [m[0].capitalize() for m in metodos]
            valores = [m[1] for m in metodos]
            
            # Colores asignados
            colores = {'Efectivo': '#00E676', 'Pago movil': '#2979FF', 'Transferencia': '#FFD600', 'Zelle': '#AA00FF'}
            lista_colores = [colores.get(n, '#FFFFFF') for n in nombres]
            
            # Dibujamos el pastel
            wedges, texts, autotexts = ax2.pie(
                valores, 
                labels=None, 
                autopct='%1.1f%%', 
                startangle=140,
                colors=lista_colores,
                wedgeprops={'edgecolor': '#121212', 'linewidth': 2}
            )
            
            plt.setp(autotexts, size=9, weight="bold", color="white")
            
            # Leyenda lateral limpia
            ax2.legend(
                wedges, nombres,
                title="MÉTODOS",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                fontsize=9,
                frameon=False,
                labelcolor='white'
            )
            
            ax2.set_title("PAGOS POR MÉTODO", color='white', size=11, weight='bold', pad=10)
        else:
            ax2.text(0.5, 0.5, "Sin datos de pago", color="white", ha="center")
            ax2.axis('off')

        canvas2 = FigureCanvasTkAgg(fig2, master=self.charts_container)
        canvas2.get_tk_widget().pack(side="right", fill="both", expand=True, padx=10)

        # --- Actualizar Tabla ---
        for w in self.table_f.winfo_children(): w.destroy()
        ctk.CTkLabel(self.table_f, text="ÚLTIMOS MOVIMIENTOS", font=("Arial", 12, "bold")).pack(pady=5)
        tree = ttk.Treeview(self.table_f, columns=("ID", "HORA", "TOTAL", "MÉTODO"), show="headings", height=5)
        for col in ("ID", "HORA", "TOTAL", "MÉTODO"): tree.heading(col, text=col)
        for v in ultimas: tree.insert("", "end", values=v)
        tree.pack(fill="x", padx=10, pady=10)

    def crear_card(self, master, titulo, valor, color):
        f = ctk.CTkFrame(master, fg_color="#1e1e1e", border_width=1, border_color="#333", height=90)
        f.pack(side="left", padx=10, expand=True, fill="both")
        ctk.CTkLabel(f, text=titulo, font=("Arial", 11, "bold"), text_color="gray").pack(pady=(10,0))
        ctk.CTkLabel(f, text=valor, font=("Arial", 22, "bold"), text_color=color).pack(pady=5)