"""Pantalla para registrar ventas y descontar existencias."""

import tkinter as tk
from tkinter import messagebox, ttk

from modelos import Tienda, mostrar_dinero


class VentasFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda, al_cambiar=None) -> None:
        super().__init__(parent, padding=12)
        self.tienda = tienda
        self.al_cambiar = al_cambiar
        self.productos: list[dict] = []
        self.carrito: dict[int, int] = {}
        self.clientes: list[dict] = []
        self._crear_interfaz()
        self.refrescar()

    def _crear_interfaz(self) -> None:
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Label(barra, text="Cliente (opcional):").pack(side="left")
        self.cliente = ttk.Combobox(barra, state="readonly", width=32)
        self.cliente.pack(side="left", padx=8)
        ttk.Button(barra, text="Quitar todo", command=self.vaciar).pack(side="right")
        contenido = ttk.Frame(self)
        contenido.pack(fill="both", expand=True)
        izquierda = ttk.LabelFrame(contenido, text="Productos disponibles", padding=8)
        izquierda.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.lista_productos = ttk.Treeview(
            izquierda, columns=("nombre", "precio", "stock"), show="headings", height=15
        )
        for columna, titulo, ancho in (
            ("nombre", "Producto", 220), ("precio", "Precio", 110), ("stock", "Existencia", 90)
        ):
            self.lista_productos.heading(columna, text=titulo)
            self.lista_productos.column(columna, width=ancho)
        self.lista_productos.pack(fill="both", expand=True)
        acciones = ttk.Frame(izquierda)
        acciones.pack(fill="x", pady=(8, 0))
        self.cantidad = ttk.Spinbox(acciones, from_=1, to=9999, width=8)
        self.cantidad.set("1")
        self.cantidad.pack(side="left")
        ttk.Button(acciones, text="Agregar al carrito", command=self.agregar).pack(
            side="left", padx=8
        )

        derecha = ttk.LabelFrame(contenido, text="Carrito de compra", padding=8)
        derecha.pack(side="left", fill="both", expand=True)
        self.lista_carrito = ttk.Treeview(
            derecha, columns=("nombre", "cantidad", "subtotal"), show="headings", height=15
        )
        for columna, titulo, ancho in (
            ("nombre", "Producto", 210), ("cantidad", "Cantidad", 75),
            ("subtotal", "Subtotal", 120),
        ):
            self.lista_carrito.heading(columna, text=titulo)
            self.lista_carrito.column(columna, width=ancho)
        self.lista_carrito.pack(fill="both", expand=True)
        ttk.Button(derecha, text="Quitar producto seleccionado", command=self.quitar).pack(
            anchor="e", pady=8
        )
        inferior = ttk.Frame(self)
        inferior.pack(fill="x", pady=(10, 0))
        self.total = ttk.Label(inferior, text="Total: $ 0,00", font=("", 16, "bold"))
        self.total.pack(side="left")
        ttk.Button(inferior, text="Registrar venta", command=self.registrar).pack(side="right")

    def refrescar(self) -> None:
        self.productos = self.tienda.listar_productos()
        self.lista_productos.delete(*self.lista_productos.get_children())
        for producto in self.productos:
            self.lista_productos.insert(
                "", "end", iid=str(producto["id"]),
                values=(producto["nombre"], mostrar_dinero(producto["precio_centavos"]),
                        producto["existencia"]),
            )
        self.clientes = self.tienda.listar_clientes()
        self.cliente["values"] = ["Sin cliente"] + [f"{c['nombre']} (#{c['id']})" for c in self.clientes]
        if not self.cliente.get():
            self.cliente.current(0)
        self._dibujar_carrito()

    def agregar(self) -> None:
        seleccion = self.lista_productos.selection()
        if not seleccion:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista.", parent=self)
            return
        try:
            cantidad = int(self.cantidad.get())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cantidad inválida", "Escribe una cantidad entera mayor que cero.", parent=self)
            return
        producto_id = int(seleccion[0])
        producto = next(p for p in self.productos if p["id"] == producto_id)
        if self.carrito.get(producto_id, 0) + cantidad > producto["existencia"]:
            messagebox.showerror(
                "Existencias insuficientes",
                f"Solo hay {producto['existencia']} unidades de {producto['nombre']}.",
                parent=self,
            )
            return
        self.carrito[producto_id] = self.carrito.get(producto_id, 0) + cantidad
        self.cantidad.set("1")
        self._dibujar_carrito()

    def quitar(self) -> None:
        seleccion = self.lista_carrito.selection()
        if seleccion:
            self.carrito.pop(int(seleccion[0]), None)
            self._dibujar_carrito()

    def vaciar(self) -> None:
        self.carrito.clear()
        self._dibujar_carrito()

    def _dibujar_carrito(self) -> None:
        self.lista_carrito.delete(*self.lista_carrito.get_children())
        total = 0
        for producto_id, cantidad in self.carrito.items():
            producto = next((p for p in self.productos if p["id"] == producto_id), None)
            if producto is None:
                continue
            subtotal = producto["precio_centavos"] * cantidad
            total += subtotal
            self.lista_carrito.insert(
                "", "end", iid=str(producto_id),
                values=(producto["nombre"], cantidad, mostrar_dinero(subtotal)),
            )
        self.total.configure(text=f"Total: {mostrar_dinero(total)}")

    def registrar(self) -> None:
        if not self.carrito:
            messagebox.showinfo("Carrito vacío", "Agrega productos antes de registrar la venta.", parent=self)
            return
        seleccion_cliente = self.cliente.current()
        cliente_id = self.clientes[seleccion_cliente - 1]["id"] if seleccion_cliente > 0 else None
        try:
            venta_id = self.tienda.registrar_venta(list(self.carrito.items()), cliente_id)
            messagebox.showinfo("Venta registrada", f"La venta #{venta_id} se guardó correctamente.", parent=self)
            self.vaciar()
            if self.al_cambiar:
                self.al_cambiar()
        except ValueError as error:
            messagebox.showerror("No se pudo registrar", str(error), parent=self)
