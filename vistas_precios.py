import customtkinter as ctk
from tkinter import ttk

class PreciosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        
        # BARRA DE BÚSQUEDA CENTRAL
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", pady=(20, 40))
        
        ctk.CTkLabel(search_frame, text="🔍", font=("Segoe UI", 24)).pack(side="left", padx=(10, 15))
        self.bus = ctk.CTkEntry(search_frame, placeholder_text="Escanee código o escriba nombre del producto...", 
                                height=55, font=("Segoe UI", 20), corner_radius=10)
        self.bus.pack(side="left", fill="x", expand=True)
        self.bus.bind("<KeyRelease>", self.buscar_rapido)

        # Contenedor estilo "Tarjeta" gigantesca para el resultado
        self.card_resultado = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=20, border_width=2, border_color="#333333")
        self.card_resultado.pack(fill="both", expand=True, padx=50, pady=(0, 30))

        # Usaremos "place" para poder animar el movimiento de "levitación"
        self.lbl_nombre = ctk.CTkLabel(self.card_resultado, text="🎟️ ESPERANDO PRODUCTO...", font=("Segoe UI", 36, "bold"), text_color="#AAAAAA")
        self.lbl_nombre.place(relx=0.5, rely=0.2, anchor="center")
        
        self.lbl_usd = ctk.CTkLabel(self.card_resultado, text="$ 0.00", font=("Segoe UI", 90, "bold"), text_color="#00E676")
        self.lbl_usd.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lbl_bs = ctk.CTkLabel(self.card_resultado, text="0.00 Bs", font=("Segoe UI", 50, "bold"), text_color="#FFD600")
        self.lbl_bs.place(relx=0.5, rely=0.8, anchor="center")

        import math
        self.anim_angle = 0.0
        def float_animation():
            if not self.winfo_exists(): return
            self.anim_angle += 0.1
            offset_y = math.sin(self.anim_angle) * 0.015
            
            # Animar icono suavemente
            self.lbl_nombre.place(relx=0.5, rely=0.2 + offset_y, anchor="center")
            self.lbl_usd.place(relx=0.5, rely=0.5 + (offset_y/2), anchor="center")
            
            self.after(50, float_animation)
            
        float_animation()

    def buscar_rapido(self, event=None):
        filtro = self.bus.get().strip()
        if len(filtro) < 2: return
        
        # Cambiamos a la nueva función que creamos arriba
        resultados = self.app.db.buscar_producto_precios(filtro)
        
        if resultados and len(resultados) > 0:
            p = resultados[0] # Obtener el primer resultado que es la tupla
            # p[2] es el nombre, p[4] es precio_venta según el SELECT de arriba
            self.card_resultado.configure(border_color="#00E676") # Tarjeta verde al encontrar
            self.lbl_nombre.configure(text=f"📦 {str(p[2]).upper()}", text_color="#FFFFFF")
            self.lbl_usd.configure(text=f"$ {float(p[4]):.2f}")
            self.lbl_bs.configure(text=f"{(float(p[4]) * self.app.tasa):.2f} Bs")
        else:
            self.card_resultado.configure(border_color="#FF1744") # Tarjeta roja si no existe
            self.lbl_nombre.configure(text="⚠️ NO ENCONTRADO", text_color="#FF1744")
            self.lbl_usd.configure(text="$ 0.00")
            self.lbl_bs.configure(text="0.00 Bs")

class VentanaConsultaPrecios(ctk.CTkToplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("🔍 Verificador de Precios")
        self.geometry("500x400")
        self.after(100, self.lift) # Asegura que esté al frente
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text="Consulta Rápida", font=("Arial", 20, "bold")).pack(pady=15)
        self.ent = ctk.CTkEntry(self, placeholder_text="Escanee o escriba...", width=350)
        self.ent.pack(pady=10)
        self.ent.bind("<Return>", self.ejecutar_busqueda)
        
        self.res_frame = ctk.CTkScrollableFrame(self, width=450, height=200)
        self.res_frame.pack(pady=10)

    def ejecutar_busqueda(self, event=None):
        for w in self.res_frame.winfo_children(): w.destroy()
        resultados = self.app.db.consultar_producto_rapido(self.ent.get())
        
        for nom, pre, stock in resultados:
            f = ctk.CTkFrame(self.res_frame)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=nom.upper(), font=("Arial", 12, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"${float(pre):.2f}", text_color="#00E676").pack(side="right", padx=10)