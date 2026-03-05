import customtkinter as ctk
from tkinter import ttk

class PreciosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.bus = ctk.CTkEntry(self, placeholder_text="Escanee código o escriba nombre...", 
                                height=50, font=("Arial", 20))
        self.bus.pack(fill="x", pady=20)
        self.bus.bind("<KeyRelease>", self.buscar_rapido)

        # Labels grandes para el precio (Tu estilo original)
        self.lbl_nombre = ctk.CTkLabel(self, text="PRODUCTO", font=("Arial", 30, "bold"))
        self.lbl_nombre.pack(pady=10)
        
        self.lbl_usd = ctk.CTkLabel(self, text="$ 0.00", font=("Arial", 60), text_color="#00E676")
        self.lbl_usd.pack(pady=5)
        
        self.lbl_bs = ctk.CTkLabel(self, text="0.00 Bs", font=("Arial", 40), text_color="orange")
        self.lbl_bs.pack(pady=5)

    def buscar_rapido(self, event=None):
        filtro = self.bus.get().strip()
        if len(filtro) < 2: return
        
        # Cambiamos a la nueva función que creamos arriba
        p = self.app.db.buscar_producto_precios(filtro)
        
        if p:
            # p[2] es el nombre, p[4] es precio_venta según el SELECT de arriba
            self.lbl_nombre.configure(text=str(p[2]))
            self.lbl_usd.configure(text=f"$ {float(p[4]):.2f}")
            self.lbl_bs.configure(text=f"{(float(p[4]) * self.app.tasa):.2f} Bs")
        else:
            self.lbl_nombre.configure(text="NO ENCONTRADO")
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