import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
from tkinter import filedialog
import pandas as pd

class ReportesFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="#121212")
        self.app = app
        self.pack(fill="both", expand=True)
        
        # Usar un Frame de Scroll para que todo quepa
        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll_canvas.pack(fill="both", expand=True)
        
        self.setup_ui()

    def setup_ui(self):
        # 1. Filtros Superiores
        f_header = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        f_header.pack(fill="x", padx=30, pady=(20, 10))
        ctk.CTkLabel(f_header, text="PANEL ADMINISTRATIVO", font=("Segoe UI", 22, "bold")).pack(side="left")
        
        for t, r in [("HOY", "HOY"), ("7 DÍAS", "SEMANA"), ("MES", "MES")]:
            ctk.CTkButton(f_header, text=t, width=90, fg_color="#1e1e1e", border_width=1,
                          command=lambda r=r: self.cargar_dashboard(r)).pack(side="right", padx=5)

        # 2. Contenedor de Tarjetas (KPIs)
        self.cards_f = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.cards_f.pack(fill="x", padx=20, pady=(0, 15))

        # 3. Contenedor Medio (Dos Gráficas)
        self.charts_container = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.charts_container.pack(fill="x", padx=20)

        # 4. Tabla de Últimas Ventas (Abajo)
        self.table_f = ctk.CTkFrame(self.scroll_canvas, fg_color="transparent")
        self.table_f.pack(fill="x", padx=20, pady=(10, 20))
                
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
        res_dev = self.app.db.obtener_resumen_devoluciones(i, f)
        cant_dev, monto_dev = res_dev[0], res_dev[1]
        
        # Ajustar total restando lo devuelto
        total_neto = max(0, total - monto_dev)

        top_prod = self.app.db.obtener_top_productos(i, f)
        ultimas = self.app.db.obtener_ultimas_ventas_detalladas(i, f)
        
        # --- Lógica de Métodos de Pago Restaurada ---
        # Como en la BD guardas strings mixtos: "Efectivo $: 10 | Efectivo Bs: 3000 | Punto: 23"
        # Usamos regex para atrapar cada bloque y calcular el total de cada método
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
            partes = texto_completo.split('|') 
            for parte in partes:
                parte = parte.upper().strip()
                import re
                numeros = re.findall(r"[-+]?\d*\.\d+|\d+", parte)
                if not numeros: continue
                monto = float(numeros[-1]) 
                
                # Truco de normalización: Si es pago digital en Bs o dice Bs, unificamos a USD dividiendo entre la tasa
                # Para que el gráfico de torta no sume 3000(bs) + 10($) = 3010
                if "BS" in parte or "PUNTO" in parte or "MOVIL" in parte or "MÓVIL" in parte or "BIO" in parte or "TRANSF" in parte or "TRASF" in parte:
                    if "$" not in parte and hasattr(self.app, 'tasa') and self.app.tasa > 0:
                        monto = monto / self.app.tasa

                # Detección
                if "EFECTIVO" in parte:
                    conteo["Efectivo"] += monto
                elif "TRANSF" in parte or "TRASF" in parte:
                    conteo["Transferencia"] += monto
                elif "PAGO" in parte or "MOVIL" in parte or "MÓVIL" in parte:
                    conteo["Pago móvil"] += monto
                elif "PUNTO" in parte:
                    conteo["Punto"] += monto
                elif "BIO" in parte:
                    conteo["Bio"] += monto

        metodos = [(k, round(v, 2)) for k, v in conteo.items() if v > 0]

        # --- Actualizar KPIs ---
        for w in self.cards_f.winfo_children(): w.destroy()
        self.crear_card(self.cards_f, "INGRESOS NETOS", f"${total_neto:,.2f}", "#FFD600")
        self.crear_card(self.cards_f, "VENTAS", str(cant), "#00E676")
        self.crear_card(self.cards_f, "DEVOLUCIONES", f"{cant_dev} (-${monto_dev:,.2f})", "#FF5252")
        self.crear_card(self.cards_f, "TICKET MEDIO", f"${(total_neto/cant if cant > 0 else 0):,.2f}", "#2979FF")

        # --- Dibujar Gráficas ---
        for w in self.charts_container.winfo_children(): w.destroy()
        
        # 1. Contenedores divididos para evitar colisiones:
        # Fila superior para la línea de tiempo (flujo de ventas)
        top_chart_frame = ctk.CTkFrame(self.charts_container, fg_color="transparent")
        top_chart_frame.pack(fill="x", pady=(0, 15))
        
        # Fila inferior para Top Productos y Torta dividiendo mitad y mitad
        bottom_charts_frame = ctk.CTkFrame(self.charts_container, fg_color="transparent")
        bottom_charts_frame.pack(fill="both", expand=True)

        header_prod = ctk.CTkFrame(bottom_charts_frame, fg_color="transparent")
        header_prod.pack(fill="x")
        ctk.CTkButton(header_prod, text="📥 Excel Productos", width=120, fg_color="#217346", hover_color="#1E613B",
                    command=lambda: self.exportar_a_excel(top_prod, ["Producto", "Cantidad"], "Top_Productos")
                    ).pack(side="right")

        # --- Gráfica 1: Líneas (Ventas por Hora) EN EL TOP ---
        ventas_hora = self.app.db.obtener_ventas_por_hora(i, f)
        fig3, ax3 = plt.subplots(figsize=(10, 2.5), dpi=85, facecolor='#121212') 
        ax3.set_facecolor('#1e1e1e')
        if ventas_hora:
            horas = [int(h[0]) for h in ventas_hora]
            montos = [float(h[1]) for h in ventas_hora]
            ax3.plot(horas, montos, color='#2979FF', marker='o', linewidth=2, markersize=4)
            ax3.fill_between(horas, montos, color='#2979FF', alpha=0.1)
            ax3.set_title("FLUJO DE VENTAS POR HORA", color='white', size=10, weight='bold')
            ax3.set_xticks(range(0, 24))
            ax3.tick_params(colors='white', labelsize=8)
            ax3.grid(True, linestyle='--', color='#444444', alpha=0.3)
        else:
            ax3.text(0.5, 0.5, "Sin actividad registrada", color="#888888", ha="center")
            ax3.axis('off')

        canvas3 = FigureCanvasTkAgg(fig3, master=top_chart_frame)
        canvas3.get_tk_widget().pack(fill="both", expand=True)

        # --- Gráfica 2: Barras (Productos) ABAJO A LA IZQUIERDA ---
        fig1, ax1 = plt.subplots(figsize=(5, 3), dpi=85, facecolor='#121212')
        ax1.set_facecolor('#1e1e1e')
        if top_prod:
            nombres_bar = [p[0][:15] for p in top_prod] 
            valores_bar = [p[1] for p in top_prod]
            ax1.bar(nombres_bar, valores_bar, color='#00E676', edgecolor='#121212', linewidth=1)
            ax1.set_title("TOP PRODUCTOS", color='white', size=10, weight='bold', pad=10)
            ax1.tick_params(colors='white', labelsize=8)
            ax1.grid(axis='y', linestyle='--', alpha=0.1)
        else:
            ax1.text(0.5, 0.5, "Sin datos de productos", color="#888888", ha="center")
            ax1.axis('off')
        
        canvas1 = FigureCanvasTkAgg(fig1, master=bottom_charts_frame)
        canvas1.get_tk_widget().pack(side="left", fill="both", expand=True, padx=(0, 10))

        # --- Gráfica 3: Torta (Métodos de Pago) ABAJO A LA DERECHA ---
        fig2, ax2 = plt.subplots(figsize=(5, 3), dpi=85, facecolor='#121212')
        if metodos:
            nombres = [m[0] for m in metodos]
            valores = [m[1] for m in metodos]
            colores_dict = {'Efectivo': '#00E676', 'Pago móvil': '#2979FF', 'Transferencia': '#FFD600', 'Bio': '#AA00FF', 'Punto': '#FF5252'}
            lista_colores = [colores_dict.get(n, '#FFFFFF') for n in nombres]
            
            wedges, texts, autotexts = ax2.pie(
                valores, autopct='%1.1f%%', startangle=140, colors=lista_colores,
                wedgeprops={'edgecolor': '#121212', 'linewidth': 2}, pctdistance=0.75
            )
            plt.setp(autotexts, size=9, weight="bold", color="white")
            ax2.legend(wedges, nombres, title="MÉTODOS", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9, frameon=False, labelcolor='white')
            ax2.set_title("PAGOS POR MÉTODO", color='white', size=11, weight='bold', pad=10)
        else:
            ax2.text(0.5, 0.5, "Sin datos de pago", color="#888888", ha="center")
            ax2.axis('off')

        canvas2 = FigureCanvasTkAgg(fig2, master=bottom_charts_frame)
        canvas2.get_tk_widget().pack(side="right", fill="both", expand=True)

        # --- Actualizar Tabla de Movimientos ---
        # Estilo para el Treeview
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
        style.map("Treeview", background=[('selected', '#1f538d')]) # Color al seleccionar
        style.configure("Treeview.Heading",
            background="#252525",
            foreground="white",
            relief="flat",
            font=("Segoe UI", 11, "bold")
        )

        for w in self.table_f.winfo_children(): w.destroy()
        
        # Header con título y botón de exportar
        header_tabla = ctk.CTkFrame(self.table_f, fg_color="transparent")
        header_tabla.pack(fill="x", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(header_tabla, text="ÚLTIMOS MOVIMIENTOS", font=("Segoe UI", 12, "bold")).pack(side="left")
        ctk.CTkButton(header_tabla, text="📥 Excel", width=80, fg_color="#217346", hover_color="#1E613B",
                      command=lambda: self.exportar_a_excel(ultimas, ["ID", "Hora", "Cliente", "Total", "Método"], "Historial_Ventas")
                     ).pack(side="right")

        # CONTENEDOR ELÁSTICO
        tree_frame = ctk.CTkFrame(self.table_f, fg_color="#1E1E1E", corner_radius=10)
        tree_frame.pack(fill="both", expand=True, pady=10)

        # Crear el Treeview con altura fija para que se vea bien
        tree = ttk.Treeview(tree_frame, columns=("ID", "HORA", "CLIENTE", "TOTAL", "MÉTODO"), 
                            show="headings", height=10)
        
        # Configurar columnas (todo junto para evitar errores de referencia)
        tree.column("ID", width=50, anchor="center", stretch=False)
        tree.column("HORA", width=100, anchor="center", stretch=False)
        tree.column("CLIENTE", width=150, anchor="w", stretch=True)
        tree.column("TOTAL", width=100, anchor="e", stretch=False)
        tree.column("MÉTODO", width=200, anchor="w", stretch=True)
        
        for col in ("ID", "HORA", "TOTAL", "MÉTODO"): 
            tree.heading(col, text=col)
        
        # Insertar datos (limpiando metodos vacios para estetica)
        for v in ultimas:
            v_list = list(v)
            metodo_raw = str(v_list[4])
            partes = [p.strip() for p in metodo_raw.split('|')]
            v_list[4] = " | ".join([p for p in partes if len(p.split(':')) > 1 and p.split(':')[1].strip()])
            tree.insert("", "end", values=v_list)
            
        # Empacar Treeview y Scrollbar
        tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        
        scroll = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        scroll.pack(side="right", fill="y", padx=(0, 2), pady=2)
        tree.configure(yscrollcommand=scroll.set)

        tree.configure(yscrollcommand=scroll.set)

    def abrir_ventana_devolucion(self, venta_data):
        v_id = venta_data[0]
        # v_id, hora, cliente, total, metodo
        detalles = self.app.db.obtener_items_venta(v_id)
        
        vent = ctk.CTkToplevel(self)
        vent.title(f"Devolución Venta #{v_id}")
        vent.geometry("500x400")
        vent.grab_set()
        
        ctk.CTkLabel(vent, text="PRODUCTOS DE LA VENTA", font=("Arial", 14, "bold")).pack(pady=10)
        
        frame_items = ctk.CTkFrame(vent)
        frame_items.pack(fill="both", expand=True, padx=20)
        
        row = 0
        self.dev_inputs = [] # (prod_id, cant_max, entry_widget)
        
        for p_id, cant, precio, sub in detalles:
            # Obtener nombre del producto
            prod = self.app.db.get_producto_por_id(p_id)
            nom = prod[2] if prod else "Producto"
            
            f = ctk.CTkFrame(frame_items, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"{nom} (Máx: {cant})", width=250, anchor="w").pack(side="left")
            e = ctk.CTkEntry(f, width=60, placeholder_text="0")
            e.pack(side="right")
            self.dev_inputs.append((p_id, cant, e))
            
        motivo_var = ctk.StringVar(value="Garantía / Falla")
        ctk.CTkLabel(vent, text="Motivo de la devolución:").pack(pady=(10, 0))
        ctk.CTkOptionMenu(vent, values=["Garantía / Falla", "Cambio de Item", "Error de Compra"], variable=motivo_var).pack(pady=5)
        
        def confirmar():
            realizados = 0
            for p_id, cant_max, e in self.dev_inputs:
                try:
                    c = int(e.get() or 0)
                    if c > 0:
                        if c > cant_max:
                            messagebox.showerror("Error", f"No puede devolver más de {cant_max} unidades.")
                            return
                        # Registrar
                        self.app.db.registrar_devolucion(v_id, p_id, c, motivo_var.get(), self.app.usuario_actual[0])
                        realizados += 1
                except: continue
            
            if realizados > 0:
                messagebox.showinfo("Éxito", "Devolución procesada correctamente (Stock reintegrado).")
                vent.destroy()
                self.cargar_dashboard("HOY")
            else:
                messagebox.showwarning("Aviso", "No ingresó ninguna cantidad a devolver.")

        ctk.CTkButton(vent, text="PROCESAR DEVOLUCIÓN", fg_color="#D32F2F", command=confirmar).pack(pady=20)

    def crear_card(self, master, titulo, valor, color):
        f = ctk.CTkFrame(master, fg_color="#1e1e1e", border_width=1, border_color="#333", height=90)
        f.pack(side="left", padx=10, expand=True, fill="both")
        ctk.CTkLabel(f, text=titulo, font=("Arial", 11, "bold"), text_color="gray").pack(pady=(10,0))
        ctk.CTkLabel(f, text=valor, font=("Arial", 22, "bold"), text_color=color).pack(pady=5)