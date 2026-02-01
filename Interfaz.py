import customtkinter as ctk
from tkinter import messagebox, ttk
from database import Database
from bcv_tasa import obtener_tasa_bcv, formatear_moneda


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MiSistema(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.tasa = obtener_tasa_bcv() or self.db.obtener_tasa_guardada() or 1.0

        self.title("MyMPos - Gestión de Productos")
        self.geometry("900x600")

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=8, padx=12)

        ctk.CTkLabel(header, text="GESTIÓN DE PRODUCTOS", font=("Roboto", 20, "bold")).pack(side="left")
        self.label_tasa = ctk.CTkLabel(header, text=f"Tasa BCV: {self.tasa:.2f} Bs.", text_color="orange")
        self.label_tasa.pack(side="right")

        # Main layout: left form, right table
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=12, pady=8)

        left = ctk.CTkFrame(main)
        left.pack(side="left", fill="y", padx=(0, 8))

        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True)

        # Form fields
        self.entry_barcode = ctk.CTkEntry(left, placeholder_text="Código de Barras", width=320)
        self.entry_barcode.pack(pady=6)
        self.entry_barcode.bind('<Return>', lambda e: self.consultar_producto())

        self.entry_nombre = ctk.CTkEntry(left, placeholder_text="Nombre del Producto", width=320)
        self.entry_nombre.pack(pady=6)

        self.entry_precio = ctk.CTkEntry(left, placeholder_text="Precio de Venta ($)", width=320)
        self.entry_precio.pack(pady=6)

        self.entry_stock = ctk.CTkEntry(left, placeholder_text="Cantidad en Stock", width=320)
        self.entry_stock.pack(pady=6)

        self.entry_minimo = ctk.CTkEntry(left, placeholder_text="Stock Mínimo", width=320)
        self.entry_minimo.pack(pady=6)

        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(pady=12)

        ctk.CTkButton(btn_frame, text="Guardar", fg_color="#2ecc71", command=self.guardar_datos).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Eliminar", fg_color="#e74c3c", command=self.eliminar_seleccion).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Limpiar", fg_color="gray", command=self.limpiar_campos).pack(side="left", padx=6)

        # Tabla de productos (Treeview)
        cols = ("codigo", "nombre", "precio", "stock")
        self.tree = ttk.Treeview(right, columns=cols, show='headings')
        self.tree.heading('codigo', text='CÓDIGO')
        self.tree.heading('nombre', text='NOMBRE')
        self.tree.heading('precio', text='PRECIO $')
        self.tree.heading('stock', text='STOCK')
        self.tree.column('precio', width=100, anchor='e')
        self.tree.column('stock', width=80, anchor='center')
        self.tree.pack(fill='both', expand=True, padx=6, pady=6)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Cargar datos iniciales
        self.refrescar_tabla()

    def limpiar_campos(self):
        for entry in [self.entry_barcode, self.entry_nombre, self.entry_precio, self.entry_stock, self.entry_minimo]:
            entry.delete(0, 'end')

    def validar_campos(self):
        if not self.entry_barcode.get().strip() or not self.entry_nombre.get().strip():
            messagebox.showwarning("Atención", "Código y Nombre son obligatorios")
            return False
        try:
            if self.entry_precio.get().strip():
                float(self.entry_precio.get())
            if self.entry_stock.get().strip():
                int(self.entry_stock.get())
            if self.entry_minimo.get().strip():
                int(self.entry_minimo.get())
        except ValueError:
            messagebox.showerror("Error", "Precio o Stock con formato inválido")
            return False
        return True

    def guardar_datos(self):
        if not self.validar_campos():
            return
        datos = (
            self.entry_barcode.get().strip(),
            self.entry_nombre.get().strip(),
            0.0,
            float(self.entry_precio.get() or 0),
            int(self.entry_stock.get() or 0),
            int(self.entry_minimo.get() or 0),
            'General'
        )
        if self.db.registrar_producto(datos):
            messagebox.showinfo("Éxito", "Producto guardado correctamente.")
            self.limpiar_campos()
            self.refrescar_tabla()
        else:
            # intentar actualizar si ya existe
            upd = (
                self.entry_nombre.get().strip(),
                0.0,
                float(self.entry_precio.get() or 0),
                int(self.entry_stock.get() or 0),
                int(self.entry_minimo.get() or 0),
                'General',
                self.entry_barcode.get().strip()
            )
            if self.db.actualizar_producto(upd):
                messagebox.showinfo("Actualizado", "Producto actualizado correctamente.")
                self.limpiar_campos()
                self.refrescar_tabla()
            else:
                messagebox.showerror("Error", "No se pudo guardar/actualizar el producto.")

    def consultar_producto(self):
        codigo = self.entry_barcode.get().strip()
        if not codigo:
            return
        resultado = self.db.buscar_producto(codigo)
        if resultado:
            # resultado = (codigo_barras, nombre, precio_venta, stock)
            self.entry_nombre.delete(0, 'end'); self.entry_nombre.insert(0, resultado[1])
            self.entry_precio.delete(0, 'end'); self.entry_precio.insert(0, resultado[2])
            self.entry_stock.delete(0, 'end'); self.entry_stock.insert(0, resultado[3])
            precio_bs = float(resultado[2]) * self.tasa
            messagebox.showinfo("Info de Precio", f"Precio en Bs: {formatear_moneda(precio_bs)}")
        else:
            messagebox.showwarning("No encontrado", "El producto no existe.")

    def refrescar_tabla(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for p in self.db.obtener_todos_los_productos():
            # p depende del SELECT *: asumimos (id, codigo_barras, nombre, precio_compra, precio_venta, stock, stock_minimo, categoria)
            codigo = p[1]
            nombre = p[2]
            precio = f"{float(p[4]):.2f}"
            stock = p[5]
            self.tree.insert('', 'end', values=(codigo, nombre, precio, stock))

    def on_tree_select(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        vals = self.tree.item(sel, 'values')
        # llenar formulario con selección
        self.entry_barcode.delete(0, 'end'); self.entry_barcode.insert(0, vals[0])
        self.entry_nombre.delete(0, 'end'); self.entry_nombre.insert(0, vals[1])
        self.entry_precio.delete(0, 'end'); self.entry_precio.insert(0, vals[2])
        self.entry_stock.delete(0, 'end'); self.entry_stock.insert(0, vals[3])

    def eliminar_seleccion(self):
        codigo = self.entry_barcode.get().strip()
        if not codigo:
            messagebox.showwarning("Atención", "Selecciona o introduce el código a eliminar")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar producto {codigo}?"):
            if self.db.eliminar_producto(codigo):
                messagebox.showinfo("Eliminado", "Producto eliminado correctamente")
                self.limpiar_campos()
                self.refrescar_tabla()
            else:
                messagebox.showerror("Error", "No se pudo eliminar el producto")


if __name__ == "__main__":
    app = MiSistema()
    app.mainloop()