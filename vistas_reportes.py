import customtkinter as ctk
from tkinter import ttk, messagebox
from modulo_factura import generar_factura_pdf # Por si necesitas re-imprimir

class ReportesFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)

        # SECCIÓN DE CIERRES
        cierres_f = ctk.CTkLabel(self, text="CIERRES DE CAJA", font=("Arial", 20, "bold"))
        cierres_f.pack(pady=10)
        
        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_f, text="GENERAR CORTE X", fg_color="#2979FF", 
                      command=self.corte_x).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_f, text="GENERAR CORTE Z (CIERRE)", fg_color="#FF1744", 
                      command=self.corte_z).pack(side="left", expand=True, padx=10)

        # TABLA DE VENTAS DEL DÍA
        ctk.CTkLabel(self, text="HISTORIAL DE HOY", font=("Arial", 14)).pack(pady=5)
        self.tree_v = ttk.Treeview(self, columns=("ID", "Hora", "Cliente", "Total", "Metodo"), show="headings")
        for c in ("ID", "Hora", "Cliente", "Total", "Metodo"): self.tree_v.heading(c, text=c)
        self.tree_v.pack(fill="both", expand=True, pady=10)
        self.cargar_ventas_hoy()

    def cargar_ventas_hoy(self):
        for i in self.tree_v.get_children(): self.tree_v.delete(i)
        # Tu mecanismo de consulta de ventas
        ventas = self.app.db.obtener_ventas_hoy()
        for v in ventas: self.tree_v.insert("", "end", values=v)

    def corte_x(self):
        # Tu lógica original de sumar totales sin cerrar la caja
        resumen = self.app.db.obtener_resumen_diario()
        messagebox.showinfo("Corte X", f"Total Ventas: {resumen['total']}$")

    def corte_z(self):
        # Tu lógica original de cerrar el turno en la base de datos
        if messagebox.askyesno("Cierre Z", "¿Cerrar caja definitivamente?"):
            self.app.db.cerrar_caja_diaria()
            messagebox.showinfo("Cierre", "Caja Cerrada. Reporte generado.")