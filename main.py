import customtkinter as ctk
from database import Database
from bcv_tasa import obtener_tasa_bcv
from vistas_login import LoginDialog
from vistas_ventas import VentasFrame
from vistas_inventario import InventarioFrame
from vistas_reportes import ReportesFrame
from vistas_precios import PreciosFrame
from vistas_usuarios import UsuariosFrame

class MyMPos(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.tasa = 1.0
        self.usuario_actual = None
        self.carrito = {}

        self.withdraw()
        self.after(100, self.login)

    def login(self):
        try:
            self.tasa = obtener_tasa_bcv() or self.db.obtener_tasa_guardada() or 1.0
        except: self.tasa = 1.0

        login = LoginDialog(None, self.db)
        self.wait_window(login)

        if login.success:
            self.usuario_actual = login.user_data
            self.deiconify()
            self.setup_main_window()
        else:
            self.destroy()

    def setup_main_window(self):
        user_nom = self.usuario_actual[2] if self.usuario_actual else "Admin"
        self.title(f"MyMPos Pro - {user_nom}")
        self.geometry("1280x720")
        
        self.sidebar = ctk.CTkFrame(self, width=80, fg_color="#1A1A1A")
        self.sidebar.pack(side="left", fill="y")
        ctk.CTkButton(self.sidebar, text="🏠", width=40, command=self.mostrar_dashboard).pack(pady=20)

        self.contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor.pack(side="right", fill="both", expand=True)
        self.mostrar_dashboard()

    def ir(self, clase_frame):
        self.limpiar()
        clase_frame(self.contenedor, self)

    def limpiar(self):
        """Elimina todos los widgets dentro del contenedor principal"""
        # Verificamos que el contenedor exista para evitar errores
        if hasattr(self, "contenedor"):
            for widget in self.contenedor.winfo_children():
                widget.destroy()

    def mostrar_dashboard(self):
        self.limpiar() # Limpia
        grid = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        grid.pack(expand=True)
        
        # Botones del menú
        opciones = [
            ("VENTAS", "🛒", "#00E676", VentasFrame),
            ("PRECIOS", "🏷️", "#FFEB3B", PreciosFrame),
            ("STOCK", "📦", "#D500F9", InventarioFrame),
            ("REPORTES", "📊", "#2979FF", ReportesFrame)
        ]

        for i, (txt, ico, col, frame) in enumerate(opciones):
            btn = self.crear_boton(grid, txt, ico, col, lambda f=frame: self.ir(f))
            btn.grid(row=i//2, column=i%2, padx=15, pady=15)

    def crear_boton(self, master, texto, icono, color, comando):
        f = ctk.CTkFrame(master, width=200, height=180, fg_color="#1E1E1E", corner_radius=15)
        f.pack_propagate(False)
        ctk.CTkFrame(f, height=5, fg_color=color).pack(fill="x")
        ctk.CTkLabel(f, text=icono, font=("Arial", 40)).pack(pady=15)
        ctk.CTkButton(f, text=texto, fg_color="transparent", command=comando).pack(fill="both", expand=True)
        return f

if __name__ == "__main__":
    app = MyMPos()
    app.mainloop()