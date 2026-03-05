import customtkinter as ctk
from tkinter import messagebox
import hashlib

class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.success = False
        self.user_data = None
        
        self.title("Acceso al Sistema")
        self.geometry("400x350")
        self.grab_set() # Bloquea hasta que se identifique

        # Tu diseño de login original
        ctk.CTkLabel(self, text="BIENVENIDO", font=("Arial", 24, "bold")).pack(pady=20)
        
        self.ent_user = ctk.CTkEntry(self, placeholder_text="Usuario", width=250)
        self.ent_user.pack(pady=10)
        
        self.ent_pass = ctk.CTkEntry(self, placeholder_text="Contraseña", show="*", width=250)
        self.ent_pass.pack(pady=10)
        
        ctk.CTkButton(self, text="ENTRAR", command=self.verificar).pack(pady=20)

    def verificar(self):
        u = self.ent_user.get()
        p = self.ent_pass.get()
        # Tu mecanismo de hash original
        p_hash = hashlib.sha256(p.encode()).hexdigest()
        
        user = self.db.authenticate_user(u, p_hash)
        if user:
            self.success = True
            self.user_data = user
            self.destroy()
        else:
            messagebox.showerror("Error", "Credenciales incorrectas")