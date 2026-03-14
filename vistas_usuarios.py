import customtkinter as ctk
from tkinter import messagebox
import hashlib
import math

class UsuariosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="#121212")
        self.app = app
        self.pack(fill="both", expand=True)
        self.setup_ui()

    def setup_ui(self):
        # 1. Título Superior (Empaquetado normal arriba)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(30, 0))
        
        ctk.CTkLabel(header, text="👤 GESTIÓN DE PERSONAL", 
                      font=("Segoe UI", 28, "bold"), 
                      text_color="#00BCD4").pack()
        
        ctk.CTkLabel(header, text="Registre nuevos empleados y asigne roles de acceso", 
                      font=("Segoe UI", 14), 
                      text_color="#AAAAAA").pack()

        # 2. Contenedor de Centrado (Ocupa el resto del espacio disponible)
        # Esto asegura que la tarjeta se vea en cualquier resolución de pantalla
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.pack(fill="both", expand=True)

        # 3. La Tarjeta (Card)
        # Usamos pack con pady para que flote y sea más estable que 'place'
        self.main_card = ctk.CTkFrame(center_frame, fg_color="#1A1A1A", 
                                      corner_radius=22, 
                                      border_width=2, 
                                      border_color="#333333")
        self.main_card.pack(pady=10, padx=20) 
        # Eliminamos pack_propagate(False) y height fijo para que el botón sea visible

        # Icono de Usuario Flotante
        self.lbl_icon = ctk.CTkLabel(self.main_card, text="➕", font=("Segoe UI", 40))
        self.lbl_icon.pack(pady=(15, 5))

        # Formulario
        form_container = ctk.CTkFrame(self.main_card, fg_color="transparent")
        form_container.pack(fill="both", expand=True, padx=40)

        # Nombre Completo
        ctk.CTkLabel(form_container, text="NOMBRE COMPLETO", font=("Segoe UI", 10, "bold"), text_color="#00BCD4").pack(anchor="w", pady=(5, 0))
        self.ent_nombre = ctk.CTkEntry(form_container, placeholder_text="Ej: Juan Pérez", height=38, font=("Segoe UI", 13), corner_radius=10)
        self.ent_nombre.pack(fill="x", pady=(2, 8))

        # Usuario
        ctk.CTkLabel(form_container, text="USUARIO DE ACCESO", font=("Segoe UI", 10, "bold"), text_color="#00BCD4").pack(anchor="w")
        self.ent_new_u = ctk.CTkEntry(form_container, placeholder_text="Nombre de Usuario", height=38, font=("Segoe UI", 13), corner_radius=10)
        self.ent_new_u.pack(fill="x", pady=(2, 8))

        # Contraseña
        ctk.CTkLabel(form_container, text="CONTRASEÑA", font=("Segoe UI", 10, "bold"), text_color="#00BCD4").pack(anchor="w")
        self.ent_new_p = ctk.CTkEntry(form_container, placeholder_text="********", show="*", height=38, font=("Segoe UI", 13), corner_radius=10)
        self.ent_new_p.pack(fill="x", pady=(2, 8))

        # Rol
        ctk.CTkLabel(form_container, text="NIVEL DE PRIVILEGIOS", font=("Segoe UI", 10, "bold"), text_color="#00BCD4").pack(anchor="w")
        self.rol_var = ctk.StringVar(value="Cajero")
        self.seg_button = ctk.CTkSegmentedButton(form_container, values=["Cajero", "Admin"], 
                                                 variable=self.rol_var,
                                                 height=35,
                                                 font=("Segoe UI", 12, "bold"),
                                                 selected_color="#00BCD4")
        self.seg_button.pack(fill="x", pady=(2, 15))

        # Botón de Registro
        self.btn_reg = ctk.CTkButton(self.main_card, text="REGISTRAR EMPLEADO", 
                                     font=("Segoe UI", 15, "bold"),
                                     fg_color="#00BCD4", 
                                     hover_color="#0097A7",
                                     text_color="#000000",
                                     height=45, 
                                     corner_radius=12,
                                     command=self.registrar)
        self.btn_reg.pack(pady=(5, 25), padx=40, fill="x")

        # Animación del icono
        self.angle = 0
        self.animate_icon()

    def animate_icon(self):
        try:
            if not self.main_card.winfo_exists(): return
            self.angle += 0.1
            offset = math.sin(self.angle) * 5
            self.lbl_icon.pack_configure(pady=(35 + offset, 10 - offset))
            self.after(50, self.animate_icon)
        except: pass

    def registrar(self):
        nom = self.ent_nombre.get().strip()
        u = self.ent_new_u.get().strip()
        p = self.ent_new_p.get().strip()
        
        if not nom or not u or not p:
            messagebox.showwarning("Atención", "Por favor rellene todos los campos.")
            return

        confirmar = messagebox.askyesno("Confirmar", f"¿Desea crear el usuario '{u}' con rol '{self.rol_var.get()}'?")
        if confirmar:
            p_hash = hashlib.sha256(p.encode()).hexdigest()
            exito = self.app.db.registrar_nuevo_usuario(u, nom.upper(), p_hash, self.rol_var.get())
            
            if exito:
                messagebox.showinfo("Éxito", f"¡Empleado {nom.upper()} registrado correctamente!")
                self.ent_nombre.delete(0, 'end')
                self.ent_new_u.delete(0, 'end')
                self.ent_new_p.delete(0, 'end')
            else:
                messagebox.showerror("Error", "No se pudo crear el usuario. Verifique si el nombre de usuario ya existe.")