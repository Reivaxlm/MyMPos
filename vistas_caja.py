import customtkinter as ctk
from tkinter import messagebox

class CajaChicaFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pack(fill="both", expand=True)
        
        # Tarjeta principal que ocupa espacio pero permite scroll interno
        self.card = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=15)
        self.card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.7, relheight=0.75)
        
        self.setup_ui()

    def setup_ui(self):
        # Título
        ctk.CTkLabel(self.card, text="Movimiento de Caja", font=("Segoe UI", 24, "bold")).pack(pady=(20, 10))

        # Selector
        self.seg_button = ctk.CTkSegmentedButton(self.card, values=["Entrada", "Salida"], 
                                                 command=self.cambiar_modo, height=45,
                                                 selected_color="#2979FF", unselected_color="#0F0F0F")
        self.seg_button.pack(pady=10, padx=40, fill="x")
        self.seg_button.set("Entrada")
        
        # --- AQUÍ ESTÁ EL CAMBIO: ScrollableFrame para que el contenido no se corte ---
        self.scroll_frame = ctk.CTkScrollableFrame(self.card, fg_color="transparent")
        self.scroll_frame.pack(pady=10, padx=40, fill="both", expand=True)

        self.combo_categoria = ctk.CTkOptionMenu(self.scroll_frame, values=["Aporte de cambio", "Cobro de deuda"], 
                                                 height=50, fg_color="#0F0F0F", button_color="#2979FF")
        self.combo_categoria.pack(pady=10, fill="x")

        self.ent_monto = ctk.CTkEntry(self.scroll_frame, placeholder_text="Monto ($)", height=50, fg_color="#0F0F0F", border_width=0)
        self.ent_monto.pack(pady=10, fill="x")

        self.ent_ref = ctk.CTkEntry(self.scroll_frame, placeholder_text="Descripción", height=50, fg_color="#0F0F0F", border_width=0)
        self.ent_ref.pack(pady=10, fill="x")
       
        self.btn_guardar = ctk.CTkButton(self.card, text="REGISTRAR MOVIMIENTO", height=60, 
                                         fg_color="#2979FF", hover_color="#1e5cb3",
                                         font=("Segoe UI", 16, "bold"), 
                                         command=self.guardar_movimiento)
        self.btn_guardar.pack(pady=(10, 20), padx=40, fill="x")
        
    def cambiar_modo(self, valor):
        if valor == "Entrada":
            self.combo_categoria.configure(values=["Aporte de cambio", "Cobro de deuda", "Otros"])
        else:
            self.combo_categoria.configure(values=["Pago proveedor", "Gasto operativo", "Retiro de seguridad"])
        self.combo_categoria.set(self.combo_categoria._values[0])

    def guardar_movimiento(self):
        monto = self.ent_monto.get()
        concepto = self.combo_categoria.get()
        tipo = self.seg_button.get().upper()
        # Obtenemos el ID del usuario desde la app
        usuario_id = self.app.usuario_actual[0] 
        
        # Debes implementar este método en database.py para guardar el usuario_id
        exito = self.app.db.registrar_caja_chica(tipo, concepto, monto, usuario_id)
        
        if exito:
            messagebox.showinfo("Éxito", "Movimiento registrado")
        else:
            messagebox.showerror("Error", "No se pudo guardar")