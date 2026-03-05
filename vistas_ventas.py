import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from modulo_factura import generar_factura_pdf
from modulo_clientes import BuscarClienteDialog

class VentasFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
        self.actualizar_tabla()

    def setup_ui(self):
        self.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- BUSCADOR ---
        ctk.CTkLabel(self, text="BUSCAR PRODUCTO", font=("Arial", 12, "bold")).pack(pady=(5,0))
        self.entry_buscar = ctk.CTkEntry(self, placeholder_text="Escriba nombre o escanee código...", width=500, height=40)
        self.entry_buscar.pack(pady=5)
        self.entry_buscar.bind("<KeyRelease>", self._filtrar_busqueda_combo)

        # LISTA DE SUGERENCIAS (El menú desplegable que faltaba)
        self.lista_sugerencias = tk.Listbox(
            self, width=70, height=6, font=("Arial", 11),
            bg="#2b2b2b", fg="white", borderwidth=1, relief="flat",
            selectbackground="#1f538d"
        )
        self.lista_sugerencias.place_forget() # Oculto por defecto
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.agregar_desde_lista)

        # --- TABLA DE CARRITO (Mecanismo Treeview) ---
        columnas = ("Cant", "Producto", "Precio $", "Subtotal $")
        self.tree = ttk.Treeview(self, columns=columnas, show="headings", height=15)
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100 if "Producto" not in col else 300)
        self.tree.pack(fill="both", expand=True, pady=10)

        # --- PANEL INFERIOR: TOTALES Y ACCIONES ---
        panel_inf = ctk.CTkFrame(self, fg_color="transparent")
        panel_inf.pack(fill="x", pady=10)

        self.lbl_total = ctk.CTkLabel(panel_inf, text="TOTAL: $ 0.00", font=("Arial", 28, "bold"), text_color="#00E676")
        self.lbl_total.pack(side="left", padx=20)

        self.lbl_total_bs = ctk.CTkLabel(panel_inf, text="0.00 Bs", font=("Arial", 20), text_color="orange")
        self.lbl_total_bs.pack(side="left", padx=10)

        ctk.CTkButton(panel_inf, text="VACIAR", fg_color="#FF1744", command=self.vaciar_carrito, width=100).pack(side="right", padx=10)
        ctk.CTkButton(panel_inf, text="PROCESAR PAGO", fg_color="#2979FF", command=self.cobrar, height=45, font=("Arial", 14, "bold")).pack(side="right", padx=10)

    # --- LÓGICA DE BÚSQUEDA Y CARRITO ---

    def _filtrar_busqueda_combo(self, event):
        texto = self.entry_buscar.get().strip()
        if len(texto) < 2:
            self.lista_sugerencias.place_forget()
            return

        # Consultamos a la DB (Usa tu método original)
        productos = self.app.db.consultar_producto_rapido(texto)
        
        if productos:
            self.lista_sugerencias.delete(0, tk.END)
            for p in productos:
                # p[0]=nombre, p[1]=precio, p[2]=stock
                self.lista_sugerencias.insert(tk.END, f"{p[0]} | ${p[1]} | Stock: {p[2]}")
            
            # Posicionamiento dinámico de la lista
            self.lista_sugerencias.place(x=self.entry_buscar.winfo_x(), y=self.entry_buscar.winfo_y() + 45)
            self.lista_sugerencias.lift()
        else:
            self.lista_sugerencias.place_forget()

    def agregar_desde_lista(self, event):
        seleccion = self.lista_sugerencias.curselection()
        if not seleccion: return
        
        item_texto = self.lista_sugerencias.get(seleccion[0])
        nombre_prod = item_texto.split(" | ")[0]
        
        # Obtenemos datos frescos de ese producto
        res = self.app.db.consultar_producto_rapido(nombre_prod)
        if res:
            p = res[0]
            self.añadir_al_carrito(p[0], float(p[1]))
        
        self.entry_buscar.delete(0, tk.END)
        self.lista_sugerencias.place_forget()

    def añadir_al_carrito(self, nombre, precio):
        if nombre in self.app.carrito:
            self.app.carrito[nombre]['cant'] += 1
        else:
            # Importante: añadir la clave 'nombre' para que modulo_factura la vea
            self.app.carrito[nombre] = {
                'nombre': nombre, 
                'precio': precio, 
                'cant': 1
            }
        self.actualizar_tabla()

    def actualizar_tabla(self):
        # Limpiar la tabla visual
        for i in self.tree.get_children(): self.tree.delete(i)
        
        total_usd = 0.0
        for nom, datos in self.app.carrito.items():
            sub = datos['precio'] * datos['cant']
            total_usd += sub
            self.tree.insert("", "end", values=(datos['cant'], nom, f"{datos['precio']:.2f}", f"{sub:.2f}"))
        
        # Actualizar etiquetas de total
        self.lbl_total.configure(text=f"TOTAL: $ {total_usd:.2f}")
        self.lbl_total_bs.configure(text=f"{(total_usd * self.app.tasa):.2f} Bs")

    def vaciar_carrito(self):
        self.app.carrito = {}
        self.actualizar_tabla()

    def cobrar(self):
        if not self.app.carrito:
            messagebox.showwarning("Atención", "El carrito está vacío")
            return

        # Diálogo de cliente (modulo_clientes.py)
        dlg = BuscarClienteDialog(self, self.app.db)
        self.wait_window(dlg)
        
        if dlg.result:
            cliente = dlg.result # (id, nombre, cedula...)
            total_usd = sum(d['precio'] * d['cant'] for d in self.app.carrito.values())
            
            # 1. Crear Venta en DB
            datos_pago = {'total_usd': total_usd, 'metodo': 'EFECTIVO'}
            id_v = self.app.db.crear_venta(datos_pago, self.app.usuario_actual[0], cliente[0], self.app.tasa)
            
            if id_v:
                # 2. Registrar cada producto
                for nom, d in self.app.carrito.items():
                    self.app.db.registrar_item_venta(id_v, nom, d['cant'], d['precio'])
                
                # 3. Generar Factura PDF
                generar_factura_pdf(
                    id_v, cliente[1], cliente[2], 
                    self.app.carrito, total_usd, 
                    total_usd * self.app.tasa, self.app.tasa, "EFECTIVO"
                )
                
                messagebox.showinfo("Éxito", f"Venta #{id_v} procesada correctamente")
                self.vaciar_carrito()