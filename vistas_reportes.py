import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import pandas as pd
from tkinter import filedialog

from pyparsing import col

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
        self.table_f = ctk.CTkFrame(self, fg_color="transparent")
        self.table_f.pack(fill="both", expand=True, padx=20, pady=(10, 20))
                
        self.cargar_dashboard("HOY")

    def exportar_a_excel(self, datos, columnas, nombre_defecto):
        if not datos:
            messagebox.showwarning("Aviso", "No hay datos para exportar")
            return
        
        archivo = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                            initialfile=nombre_defecto,
                                            filetypes=[("Excel", "*.xlsx")])
        if archivo:
            df = pd.DataFrame(datos, columns=columnas)
            df.to_excel(archivo, index=False)
            messagebox.showinfo("Éxito", "Exportado correctamente")

    def cargar_dashboard(self, rango):
        # Lógica de fechas
        hoy = datetime.now()
        if rango == "HOY": i = f = hoy.strftime("%Y-%m-%d")
        elif rango == "SEMANA": i = (hoy - timedelta(days=7)).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")
        else: i = hoy.replace(day=1).strftime("%Y-%m-%d"); f = hoy.strftime("%Y-%m-%d")

        # DESTRUIR LO VIEJO ANTES DE DIBUJAR
        for w in self.charts_container.winfo_children(): w.destroy()
        # Si creaste f_linea fuera de charts_container, destrúyelo también:
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w != self.cards_f and w != self.table_f:
                # Ojo: asegúrate de identificar el frame de la línea
                pass

        # Datos
        total, cant = self.app.db.obtener_resumen_kpi(i, f)
        top_prod = self.app.db.obtener_top_productos(i, f)
        metodos = self.app.db.obtener_metodos_pago_pie(i, f)
        ultimas = self.app.db.obtener_ultimas_ventas_detalladas(i, f)
        datos_sucios = self.app.db.obtener_metodos_raw(i, f)

        conteo = {
            "Efectivo": 0.0,
            "Pago móvil": 0.0,
            "Punto": 0.0,
            "Bio": 0.0,
            "Transferencia": 0.0
        }

        for fila in datos_sucios:
            texto_completo = str(fila[0])
            
            # 1. Separamos por la barra vertical
            partes = texto_completo.split('|') 
            
            for parte in partes:
                parte = parte.upper().strip()
                
                numeros = re.findall(r"[-+]?\d*\.\d+|\d+", parte)
                if not numeros: continue
                monto = float(numeros[-1]) 

                # Detección más robusta
                if "EFECTIVO" in parte:
                    conteo["Efectivo"] += monto
                elif "TRANSF" in parte: # Detecta "Transferencia"
                    conteo["Transferencia"] += monto
                elif "PAGO M" in parte or "MOVIL" in parte:
                    conteo["Pago móvil"] += monto
                elif "PUNTO" in parte:
                    conteo["Punto"] += monto
                elif "BIO" in parte:
                    conteo["Bio"] += monto

        # 4. Limpiamos para la gráfica
        metodos = [(k, v) for k, v in conteo.items() if v > 0]

        # --- Actualizar KPIs ---
        for w in self.cards_f.winfo_children(): w.destroy()
        self.crear_card(self.cards_f, "TOTAL INGRESOS", f"${total:,.2f}", "#FFD600")
        self.crear_card(self.cards_f, "VENTAS REALIZADAS", str(cant), "#00E676")
        self.crear_card(self.cards_f, "TICKET MEDIO", f"${(total/cant if cant > 0 else 0):,.2f}", "#2979FF")

        # --- Dibujar Gráficas ---
        for w in self.charts_container.winfo_children(): w.destroy()
        header_prod = ctk.CTkFrame(self.charts_container, fg_color="transparent")
        ctk.CTkButton(header_prod, text="📥 Descargar", width=80, fg_color="#217346",
                    command=lambda: self.exportar_a_excel(top_prod, ["Producto", "Cantidad"], "Top_Productos")
                    ).pack(side="right")
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
            nombres = [m[0] for m in metodos]
            valores = [m[1] for m in metodos]
            
            colores_dict = {
                'Efectivo': '#00E676', 
                'Pago móvil': '#2979FF', 
                'Transferencia': '#FFD600',
                'Bio': '#AA00FF', 
                'Punto': '#FF5252'
            }
            lista_colores = [colores_dict.get(n, '#FFFFFF') for n in nombres]
            
            wedges, texts, autotexts = ax2.pie(
                valores, 
                autopct='%1.1f%%', 
                startangle=140,
                colors=lista_colores,
                wedgeprops={'edgecolor': '#121212', 'linewidth': 2}
            )
            
            plt.setp(autotexts, size=9, weight="bold", color="white")
            ax2.legend(wedges, nombres, title="MÉTODOS", loc="center left", 
                       bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9, frameon=False, labelcolor='white')
            ax2.set_title("PAGOS POR MÉTODO", color='white', size=11, weight='bold', pad=10)
        else:
            ax2.text(0.5, 0.5, "Sin datos de pago", color="white", ha="center")
            ax2.axis('off')

        for w in self.charts_container.winfo_children():
            if str(type(w)) == "<class 'matplotlib.backends.backend_tkagg.FigureCanvasTkAgg'>":
                w.destroy() # Evitar que se encimen gráficas viejas

        canvas2 = FigureCanvasTkAgg(fig2, master=self.charts_container)
        canvas2.get_tk_widget().pack(side="right", fill="both", expand=True, padx=10)

        # --- Gráfica 3: Líneas (Ventas por Hora) ---
        ventas_hora = self.app.db.obtener_ventas_por_hora(i, f)

        fig3, ax3 = plt.subplots(figsize=(10, 3), dpi=85, facecolor='#121212')
        ax3.set_facecolor('#1e1e1e')

        if ventas_hora:
            horas = [int(h[0]) for h in ventas_hora]
            montos = [float(h[1]) for h in ventas_hora]
            
            # Dibujamos la línea con puntos
            ax3.plot(horas, montos, color='#FFD600', marker='o', linewidth=2, markersize=6)
            # Rellenamos el área debajo para que se vea más moderno
            ax3.fill_between(horas, montos, color='#FFD600', alpha=0.1)
            
            ax3.set_title("FLUJO DE VENTAS POR HORA", color='white', size=11, weight='bold')
            ax3.set_xticks(range(0, 24)) # Mostrar todas las horas del día
            ax3.tick_params(colors='white', labelsize=8)
            ax3.grid(True, linestyle='--', alpha=0.1)
        else:
            ax3.text(0.5, 0.5, "Sin datos hoy", color="white", ha="center")

        canvas3 = FigureCanvasTkAgg(fig3, master=self.charts_container)
        canvas3.get_tk_widget().pack(fill="x", pady=10)

        # --- Actualizar Tabla ---
        # --- Estilo para el Treeview ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
            background="#1e1e1e",
            foreground="white",
            rowheight=30,
            fieldbackground="#1e1e1e",
            borderidwidth=0,
            font=("Segoe UI", 10)
        )
        style.map("Treeview", background=[('selected', '#1f538d')]) # Color al seleccionar
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )

        for w in self.table_f.winfo_children(): w.destroy()
        
        # Header con título y botón de exportar
        header_tabla = ctk.CTkFrame(self.table_f, fg_color="transparent")
        header_tabla.pack(fill="x", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(header_tabla, text="ÚLTIMOS MOVIMIENTOS", font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkButton(header_tabla, text="📥 Excel", width=80, fg_color="#217346",
                      command=lambda: self.exportar_a_excel(ultimas, ["ID", "Hora", "Cliente", "Total", "Método"], "Historial_Ventas")
                     ).pack(side="right")

        # CONTENEDOR ELÁSTICO
        tree_frame = ctk.CTkFrame(self.table_f, fg_color="#1e1e1e")
        tree_frame.pack(fill="both", expand=True)

        # Crear el Treeview
        tree = ttk.Treeview(tree_frame, columns=("ID", "HORA", "CLIENTE", "TOTAL", "MÉTODO"), show="headings")
        
        # Configurar columnas (todo junto para evitar errores de referencia)
        tree.column("ID", width=50, anchor="center", stretch=False)
        tree.column("HORA", width=100, anchor="center", stretch=False)
        tree.column("CLIENTE", width=150, anchor="w", stretch=True)
        tree.column("TOTAL", width=100, anchor="e", stretch=False)
        tree.column("MÉTODO", width=200, anchor="w", stretch=True)
        
        for col in ("ID", "HORA", "TOTAL", "MÉTODO"): 
            tree.heading(col, text=col)
        
        # Insertar datos
        for v in ultimas: 
            tree.insert("", "end", values=v)
            
        # Empacar Treeview y Scrollbar
        tree.pack(side="left", fill="both", expand=True)
        
        scroll = ctk.CTkScrollbar(tree_container, command=tree.yview)
        scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)

    def crear_card(self, master, titulo, valor, color):
        f = ctk.CTkFrame(master, fg_color="#1e1e1e", border_width=1, border_color="#333", height=90)
        f.pack(side="left", padx=10, expand=True, fill="both")
        ctk.CTkLabel(f, text=titulo, font=("Arial", 11, "bold"), text_color="gray").pack(pady=(10,0))
        ctk.CTkLabel(f, text=valor, font=("Arial", 22, "bold"), text_color=color).pack(pady=5)