import customtkinter as ctk
from tkinter import messagebox

class GastosFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # UI
        ctk.CTkLabel(self, text="Registro de Gastos Operativos", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        self.card = ctk.CTkFrame(self, width=400, height=350)
        self.card.pack(pady=20)
        
        self.desc = ctk.CTkEntry(self.card, placeholder_text="Descripción (Ej: Pago Nómina)")
        self.desc.pack(pady=15, padx=20, fill="x")
        
        self.cat = ctk.CTkComboBox(self.card, values=["Renta", "Nómina", "Servicios", "Otros"])
        self.cat.pack(pady=15, padx=20, fill="x")
        
        self.monto = ctk.CTkEntry(self.card, placeholder_text="Monto")
        self.monto.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkButton(self.card, text="Registrar Gasto", fg_color="#E53935", command=self.registrar).pack(pady=20)

    def registrar(self):
        try:
            query = "INSERT INTO public.gastos (descripcion, categoria, monto, fecha) VALUES (%s, %s, %s, CURRENT_DATE)"
            self.app.db.execute(query, (self.desc.get(), self.cat.get(), float(self.monto.get())))
            messagebox.showinfo("Éxito", "Gasto guardado. Se reflejará en tus reportes.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")