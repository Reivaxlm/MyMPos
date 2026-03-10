from tkinter import messagebox

import customtkinter as ctk
from database import Database
from bcv_tasa import obtener_tasa_bcv
from vistas_login import LoginDialog
from vistas_ventas import VentasFrame
from vistas_inventario import InventarioFrame
from vistas_reportes import ReportesFrame
from vistas_precios import PreciosFrame
from vistas_usuarios import UsuariosFrame
from utilidades import parse_monto

class MyMPos(ctk.CTk):
    def __init__(self):
        super().__init__()
        # --- CONFIGURACIÓN MODERNA ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Escalado para Termux (para que no se vea minúsculo)
        ctk.set_widget_scaling(1.1) 
        
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
        self.configure(fg_color="#0F0F0F") # Fondo ultra oscuro

        # SIDEBAR ESTILIZADO
        self.sidebar = ctk.CTkFrame(self, width=100, fg_color="#161616", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo o Avatar en el Sidebar
        ctk.CTkLabel(self.sidebar, text="MyM", font=("Impact", 24), text_color="#3b8ed0").pack(pady=20)
        
        # Botones de navegación rápida con iconos
        self.btn_home = ctk.CTkButton(self.sidebar, text="🏠", width=60, height=60, 
                                     fg_color="transparent", hover_color="#222222",
                                     font=("Arial", 24), command=self.mostrar_dashboard)
        self.btn_home.pack(pady=10)

        # CONTENEDOR PRINCIPAL CON BORDES REDONDEADOS
        self.contenedor = ctk.CTkFrame(self, fg_color="#121212") # Un poco más claro que el negro puro
        self.contenedor.pack(side="right", fill="both", expand=True, padx=20, pady=20)
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
        self.limpiar()
        
        # Frame contenedor
        container = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=20)
        
        opciones = [
            ("VENTAS", "🛒", "#00E676", VentasFrame),
            ("PRECIOS", "🏷️", "#FFD600", PreciosFrame),
            ("STOCK", "📦", "#AA00FF", InventarioFrame),
            ("REPORTES", "📊", "#2979FF", ReportesFrame)
        ]

        for i, (txt, ico, col, frame) in enumerate(opciones):
            # Aquí llamamos a la nueva función de botón directo
            btn = self.crear_boton(container, txt, ico, col, lambda f=frame: self.ir(f))
            btn.grid(row=i//2, column=i%2, padx=20, pady=20)

    def crear_boton(self, master, texto, icono, color, comando):
        
        btn = ctk.CTkButton(
            master,
            text=f"{icono}\n\n{texto}", # Saltos de línea para organizar
            font=("Segoe UI", 20, "bold"),
            width=250,
            height=220,
            corner_radius=20,
            fg_color="#1E1E1E",
            hover_color="#2A2A2A",
            border_width=3,
            border_color=color,
            command=comando,
            anchor="center" # Centra todo el contenido
        )
        return btn
    
    def boton_cierre_caja(self):
        from modulo_cierre import realizar_cierre
        try:
            pdf = realizar_cierre()
            messagebox.showinfo("Cierre", f"Cierre generado con éxito: {pdf}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cerrar la caja: {e}")

def crear_contenedor_vista(self, titulo):
    # Esto crea un header estilizado para cada sección
    header = ctk.CTkFrame(self.contenedor, fg_color="transparent")
    header.pack(fill="x", pady=(0, 20))
    
    ctk.CTkLabel(header, text=titulo, font=("Segoe UI", 24, "bold")).pack(side="left")
    
    # Botón de volver al home
    ctk.CTkButton(header, text="⬅ Volver", width=80, fg_color="#333333", 
                  command=self.mostrar_dashboard).pack(side="right")
    
    return self.contenedor

if __name__ == "__main__":
    app = MyMPos()
    app.mainloop()