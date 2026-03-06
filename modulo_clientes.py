import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog

class BuscarClienteDialog(ctk.CTkToplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.result = None
        self.title("Seleccionar Cliente")
        self.geometry("600x500")
        self.grab_set()

        self.entry_buscar = ctk.CTkEntry(self, placeholder_text="Nombre o Cédula...")
        self.entry_buscar.pack(pady=10, padx=20, fill="x")
        self.entry_buscar.bind("<KeyRelease>", self._buscar)

        self.tree = ttk.Treeview(self, columns=("ID", "Nombre", "Cedula"), show="headings")
        for c in ("ID", "Nombre", "Cedula"): self.tree.heading(c, text=c)
        self.tree.pack(pady=10, padx=20, fill="both", expand=True)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(fill="x", pady=10)
        ctk.CTkButton(btn_f, text="Seleccionar", command=self._seleccionar).pack(side="left", padx=20)
        ctk.CTkButton(btn_f, text="Nuevo", command=self._nuevo_cliente).pack(side="right", padx=20)
        self.after(100, self._buscar) 

    def _buscar(self, event=None):
        # Limpia la tabla
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        
        # Obtiene clientes (si el campo está vacío, tu función debería traer todos)
        # Si al no escribir nada no trae nada, asegúrate de que self.db.buscar_cliente 
        # tenga una condición que diga: if not termino: return todos_los_clientes
        clientes = self.db.buscar_cliente(self.entry_buscar.get())
        
        # Inserta en la tabla
        for c in clientes: 
            self.tree.insert("", "end", values=(c[0], c[1], c[2]))

    def _seleccionar(self):
        sel = self.tree.focus()
        if sel:
            v = self.tree.item(sel, "values")
            self.result = self.db.get_cliente_por_id(v[0])
            self.destroy()

    def _nuevo_cliente(self):
        nombre = simpledialog.askstring("Nuevo", "Nombre:", parent=self)
        if nombre:
            cedula = simpledialog.askstring("ID", "Cédula:", parent=self)
            self.db.crear_cliente((nombre, cedula, "N/A"))
            self._buscar()