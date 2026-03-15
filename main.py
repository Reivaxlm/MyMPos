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
from vistas_compras import ComprasFrame
from vistas_devoluciones import DevolucionesFrame
from utilidades import parse_monto
from vistas_caja import CajaChicaFrame
from vistas_proveedores import ProveedoresFrame
from vistas_gastos import GastosFrame

class MyMPos(ctk.CTk):
    def __init__(self):
        super().__init__()
        # --- CONFIGURACIÓN MODERNA ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Escalado y fuentes globales
        ctk.set_widget_scaling(1.1)
        self.fuente_principal = ("Segoe UI", 14)
        self.fuente_titulos = ("Segoe UI", 24, "bold")
        
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
        self.sidebar = ctk.CTkFrame(self, width=80, fg_color="#1A1A1A", corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # Logo o Avatar en el Sidebar
        self.logo_label = ctk.CTkLabel(self.sidebar, text="MyM", font=("Segoe UI Black", 24), text_color="#2979FF")
        self.logo_label.pack(pady=30)
        
        # Botones de navegación rápida con iconos
        self.btn_home = ctk.CTkButton(self.sidebar, text="🏠", width=50, height=50, 
                                     fg_color="transparent", hover_color="#2B2B2B",
                                     font=("Arial", 28), command=self.mostrar_dashboard)
        self.btn_home.pack(pady=10)

        # CONTENEDOR PRINCIPAL CON BORDES REDONDEADOS
        self.contenedor = ctk.CTkFrame(self, fg_color="#121212", corner_radius=15)
        self.contenedor.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=20)
        self.mostrar_dashboard()

    def ir(self, clase_frame):
        print(f"Cargando: {clase_frame.__name__}")
        self.limpiar()
        try:
            # Aquí pasamos 'self' para que la vista tenga acceso a la BD
            clase_frame(self.contenedor, self)
        except Exception as e:
            print(f"ERROR AL CARGAR VISTA: {e}")
            self.mostrar_dashboard()

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
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título en el dashboard - Más interactivo y llamativo
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        import datetime, math
        hora = datetime.datetime.now().hour
        if hora < 12:
            saludo = "🌅 ¡Buenos días"
        elif hora < 19:
            saludo = "☀️ ¡Buenas tardes"
        else:
            saludo = "🌙 ¡Buenas noches"
            
        nombre_user = self.usuario_actual[2] if self.usuario_actual else "Admin"
            
        # Un frame interno para darle un toque de color tipo tarjeta
        self.saludo_card = ctk.CTkFrame(header, fg_color="#1E1E1E", corner_radius=15, border_width=2, border_color="#2979FF")
        self.saludo_card.pack(fill="x", ipady=5, ipadx=20) # Reducido ipady
        
        self.lbl_saludo = ctk.CTkLabel(self.saludo_card, text=f"{saludo}, {nombre_user}!", font=("Segoe UI", 26, "bold"), text_color="#FFFFFF") # Tamaño fuente reducido
        self.lbl_saludo.pack(anchor="w", padx=20, pady=(5, 0))
        
        self.lbl_rocket = ctk.CTkLabel(self.saludo_card, text="¿Qué módulo deseas utilizar hoy? 🚀", font=("Segoe UI", 13), text_color="#00E676") # Tamaño fuente reducido
        self.lbl_rocket.pack(anchor="w", padx=20, pady=(2, 5))

        # ---- Animación Pulsante de Cabecera ----
        self.header_angle = 0
        def animate_header():
            try:
                if not getattr(self, "saludo_card", None) or not self.saludo_card.winfo_exists(): return
                self.header_angle += 0.1
                grosor = 2 + math.sin(self.header_angle) * 1  # Brillo dinámico en borde
                self.saludo_card.configure(border_width=grosor)
                self.saludo_card.after(50, animate_header)
            except Exception:
                pass
        animate_header()

        # Grid para los botones
        grid_frame = ctk.CTkScrollableFrame(
            container, 
            fg_color="transparent"
        )
        grid_frame.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        # 2. Configura las columnas para que siempre haya 3 cuadros por fila (ajustable)
        grid_frame.columnconfigure((0, 1, 2), weight=1)

        rol = self.usuario_actual[3] if self.usuario_actual else "Cajero"
        
        opciones_full = [
            ("VENTAS", "🛒", "#00E676", VentasFrame, "Procesar y registrar ventas"),
            ("STOCK", "📦", "#AA00FF", InventarioFrame, "Gestión del inventario"),
            ("COMPRAS", "➕", "#FF5252", ComprasFrame, "Entrada de mercancía nueva"),
            ("PROVEEDORES", "🤝", "#76FF03", ProveedoresFrame, "Directorio y contactos"), # NUEVO
            ("GASTOS", "💸", "#FF3D00", GastosFrame, "Registro de gastos operativos"),   # NUEVO
            ("DEVOLUCIÓN", "🔄", "#F44336", DevolucionesFrame, "Gestión de reclamos"),
            ("PRECIOS", "💰", "#FFD600", PreciosFrame, "Consulta rápida de precios"),
            ("REPORTES", "📊", "#2979FF", ReportesFrame, "Métricas y movimientos"),
            ("USUARIOS", "👤", "#00BCD4", UsuariosFrame, "Gestión de personal"),
            ("CAJA CHICA", "💵", "#FF9800", CajaChicaFrame, "Control de entradas y salidas"),
        ]

        # Filtrado por privilegios solicitado:
        # Cajero: Ventas, Compras, Precios, Devolución.
        if rol == "Cajero":
            permitidos = ["VENTAS", "COMPRAS", "PRECIOS", "DEVOLUCIÓN"]
            opciones = [opt for opt in opciones_full if opt[0] in permitidos]
            cols = 2 
        else:
            opciones = opciones_full
            cols = 3 

        # DIBUJADO DINÁMICO (Esto arregla el error de filas/columnas)
        for i, (txt, ico, col, frame, desc) in enumerate(opciones):
            fila = i // cols
            columna = i % cols
            btn = self.crear_boton(grid_frame, txt, ico, col, desc, lambda f=frame: self.ir(f))
            btn.grid(row=fila, column=columna, padx=15, pady=15, sticky="nsew")

    def crear_boton(self, master, texto, icono, color, desc, comando):
        import math
        class AnimatedButton(ctk.CTkFrame):
            def __init__(self, parent, text, icon, col, description, cmd):
                super().__init__(parent, width=280, height=210, corner_radius=15, fg_color="#1A1A1A", border_width=2, border_color=col)
                self.pack_propagate(False)
                self.comando = cmd
                self.base_color = col
                
                # Elemento icono usando 'place' para facilitar la animación
                self.icon_label = ctk.CTkLabel(self, text=icon, font=("Segoe UI", 55))
                self.icon_label.place(relx=0.5, rely=0.35, anchor="center")
                
                self.title_label = ctk.CTkLabel(self, text=text, font=("Segoe UI", 20, "bold"), text_color="#FFFFFF")
                self.title_label.place(relx=0.5, rely=0.70, anchor="center")
                
                self.desc_label = ctk.CTkLabel(self, text=description, font=("Segoe UI", 12), text_color="#AAAAAA")
                self.desc_label.place(relx=0.5, rely=0.88, anchor="center")
                
                # Binds
                for w in [self, self.icon_label, self.title_label, self.desc_label]:
                    w.bind("<Enter>", self.on_enter)
                    w.bind("<Leave>", self.on_leave)
                    w.bind("<Button-1>", self.on_click)
                    
                self.anim_angle = 0.0
                self.hovering = False
                self.animate()
                
            def animate(self):
                try:
                    if not self.winfo_exists(): return
                    self.anim_angle += 0.15
                    
                    # Si el usuario hace hover, la animación es más intensa
                    multiplier = 0.04 if self.hovering else 0.015
                    offset = math.sin(self.anim_angle) * multiplier
                    
                    self.icon_label.place(relx=0.5, rely=0.35 + offset, anchor="center")
                    self.after(40, self.animate)
                except Exception:
                    pass
                
            def on_enter(self, e):
                self.hovering = True
                self.configure(fg_color="#222222", border_color="#FFFFFF")
                self.icon_label.configure(font=("Segoe UI", 65)) # Crece al pasar el ratón
                
            def on_leave(self, e):
                self.hovering = False
                self.configure(fg_color="#1A1A1A", border_color=self.base_color)
                self.icon_label.configure(font=("Segoe UI", 55))
                
            def on_click(self, e):
                self.configure(border_width=4)
                self.after(100, lambda: self.configure(border_width=2) if self.winfo_exists() else None)
                if self.comando: self.comando()
                
        return AnimatedButton(master, texto, icono, color, desc, comando)
    
def crear_contenedor_vista(self, titulo):
        header = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header, text=titulo, font=("Segoe UI", 24, "bold")).pack(side="left")
        ctk.CTkButton(header, text="⬅ Volver", width=80, fg_color="#333333", 
                      command=self.mostrar_dashboard).pack(side="right")
        return self.contenedor
def ir(self, clase_frame):
        print(f"Intentando cargar: {clase_frame.__name__}") # Esto te dirá si al menos se llama
        self.limpiar()
        try:
            clase_frame(self.contenedor, self)
        except Exception as e:
            print(f"ERROR AL CARGAR LA VISTA: {e}")
            # Si falla, vuelve al dashboard para no dejar la pantalla negra
            self.mostrar_dashboard()

if __name__ == "__main__":
    app = MyMPos()
    app.mainloop()