import customtkinter as ctk

def crear_tarjeta_dashboard(master, titulo, icono, color, comando):
    """Crea un mosaico para el menú principal"""
    card = ctk.CTkFrame(master, corner_radius=15, fg_color="#1E1E1E", height=200)
    card.pack_propagate(False)

    # Decoración superior
    ctk.CTkFrame(card, height=8, fg_color=color).pack(fill="x", side="top")

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(expand=True)

    ctk.CTkLabel(inner, text=icono, font=("Arial", 60)).pack()
    ctk.CTkLabel(inner, text=titulo, font=("Roboto", 18, "bold")).pack(pady=10)

    # Hacer que toda la tarjeta sea cliqueable
    for widget in [card, inner]:
        widget.bind("<Button-1>", lambda e: comando())
    
    return card