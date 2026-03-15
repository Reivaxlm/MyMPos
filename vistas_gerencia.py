import customtkinter as ctk

class ReporteGerencialFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Obtener los datos reales de ganancias
        datos = self.app.db.obtener_resumen_ganancias()
        
        # Mostrar tarjetas (Cards) profesionales
        self.crear_card("Ventas Totales", f"${datos['ventas']:,.2f}", "#2979FF")
        self.crear_card("Gastos Operativos", f"${datos['gastos']:,.2f}", "#E53935")
        self.crear_card("GANANCIA NETA", f"${datos['utilidad_neta']:,.2f}", "#43A047")

    def crear_card(self, titulo, valor, color):
        card = ctk.CTkFrame(self, fg_color=color, width=200, height=100)
        card.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 12)).pack(pady=(10,0))
        ctk.CTkLabel(card, text=valor, font=("Segoe UI", 24, "bold")).pack(pady=5)