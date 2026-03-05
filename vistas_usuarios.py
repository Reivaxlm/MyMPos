import customtkinter as ctk
from tkinter import ttk, messagebox
import hashlib

class UsuariosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self, text="GESTIÓN DE USUARIOS", font=("Arial", 20, "bold")).pack(pady=10)
        
        # Formulario rápido que tenías en el main
        self.ent_new_u = ctk.CTkEntry(self, placeholder_text="Nombre de Usuario")
        self.ent_new_u.pack(pady=5)
        
        self.ent_new_p = ctk.CTkEntry(self, placeholder_text="Contraseña", show="*")
        self.ent_new_p.pack(pady=5)
        
        self.rol_var = ctk.StringVar(value="cajero")
        ctk.CTkSegmentedButton(self, values=["cajero", "admin"], variable=self.rol_var).pack(pady=10)
        
        ctk.CTkButton(self, text="REGISTRAR USUARIO", fg_color="green", 
                      command=self.registrar).pack(pady=10)

    def registrar(self):
        u = self.ent_new_u.get()
        p = self.ent_new_p.get()
        if u and p:
            p_hash = hashlib.sha256(p.encode()).hexdigest()
            self.app.db.registrar_nuevo_usuario(u, "Nombre Empleado", p_hash, self.rol_var.get())
            messagebox.showinfo("Éxito", "Usuario creado")