"""Pantalla de catálogo y control de existencias."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from modelos import Tienda, mostrar_dinero


class ProductosFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda, al_cambiar=None) -> None:
        super().__init__(parent, padding=12)
        self.tienda = tienda
        self.al_cambiar = al_cambiar
        self.producto_id: int | None = None
        self.categorias: list[dict] = []
        self._crear_interfaz()
        self.refrescar()

    def _crear_interfaz(self) -> None:
        formulario = ttk.LabelFrame(self, text="Datos del producto", padding=10)
        formulario.pack(fill="x", pady=(0, 10))
        ttk.Label(formulario, text="Nombre").grid(row=0, column=0, sticky="w")
        self.nombre = ttk.Entry(formulario, width=28)
        self.nombre.grid(row=1, column=0, padx=(0, 8), sticky="ew")
        ttk.Label(formulario, text="Categoría").grid(row=0, column=1, sticky="w")
        self.categoria = ttk.Combobox(formulario, state="readonly", width=19)
        self.categoria.grid(row=1, column=1, padx=8, sticky="ew")
        ttk.Button(formulario, text="Nueva categoría", command=self.nueva_categoria).grid(
            row=1, column=2, padx=4
        )
        ttk.Label(formulario, text="Precio").grid(row=0, column=3, sticky="w")
        self.precio = ttk.Entry(formulario, width=13)
        self.precio.grid(row=1, column=3, padx=8, sticky="ew")
        ttk.Label(formulario, text="Stock mínimo").grid(row=0, column=4, sticky="w")
        self.minimo = ttk.Entry(formulario, width=10)
        self.minimo.grid(row=1, column=4, padx=8, sticky="ew")
        ttk.Label(formulario, text="Existencia inicial").grid(row=0, column=5, sticky="w")
        self.existencia = ttk.Entry(formulario, width=12)
        self.existencia.grid(row=1, column=5, padx=8, sticky="ew")
        ttk.Button(formulario, text="Guardar producto", command=self.guardar).grid(
            row=1, column=6, padx=4
        )
        ttk.Button(formulario, text="Limpiar", command=self.limpiar).grid(row=1, column=7)
        ttk.Label(formulario, text="Costo unitario inicial (opcional)").grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        self.costo = ttk.Entry(formulario, width=16)
        self.costo.grid(row=3, column=0, sticky="w")

        busqueda = ttk.Frame(self)
        busqueda.pack(fill="x", pady=(0, 8))
        ttk.Label(busqueda, text="Buscar producto:").pack(side="left")
        self.filtro = ttk.Entry(busqueda, width=32)
        self.filtro.pack(side="left", padx=8)
        self.filtro.bind("<KeyRelease>", lambda _evento: self._cargar_productos())
        ttk.Button(busqueda, text="Ajustar existencias", command=self.ajustar).pack(side="right")
        ttk.Button(busqueda, text="Registrar compra", command=self.registrar_compra).pack(
            side="right", padx=6
        )
        ttk.Button(busqueda, text="Asignar costo inicial", command=self.asignar_costo).pack(
            side="right", padx=6
        )
        ttk.Button(busqueda, text="Desactivar producto", command=self.desactivar).pack(
            side="right", padx=6
        )

        columnas = ("nombre", "categoria", "precio", "existencia", "minimo")
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings", height=16)
        encabezados = ("Producto", "Categoría", "Precio", "Existencia", "Stock mínimo")
        anchos = (250, 170, 130, 110, 120)
        for columna, titulo, ancho in zip(columnas, encabezados, anchos):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho, anchor="w")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._seleccionar)
        self.existencia.configure(state="normal")

    def refrescar(self) -> None:
        self.categorias = self.tienda.listar_categorias()
        self.categoria["values"] = [item["nombre"] for item in self.categorias]
        if self.categorias and not self.categoria.get():
            self.categoria.current(0)
        self._cargar_productos()

    def _cargar_productos(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for producto in self.tienda.listar_productos(self.filtro.get()):
            self.tabla.insert(
                "", "end", iid=str(producto["id"]),
                values=(producto["nombre"], producto["categoria"],
                        mostrar_dinero(producto["precio_centavos"]),
                        producto["existencia"], producto["stock_minimo"]),
            )

    def _seleccionar(self, _evento=None) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        self.producto_id = int(seleccion[0])
        producto = next(
            item for item in self.tienda.listar_productos(incluir_inactivos=True)
            if item["id"] == self.producto_id
        )
        self.nombre.delete(0, "end")
        self.nombre.insert(0, producto["nombre"])
        self.categoria.set(producto["categoria"])
        self.precio.delete(0, "end")
        self.precio.insert(
            0,
            f"{producto['precio_centavos'] // 100}."
            f"{producto['precio_centavos'] % 100:02d}",
        )
        self.minimo.delete(0, "end")
        self.minimo.insert(0, str(producto["stock_minimo"]))
        self.existencia.delete(0, "end")
        self.existencia.insert(0, str(producto["existencia"]))
        self.existencia.configure(state="disabled")
        self.costo.configure(state="normal")
        self.costo.delete(0, "end")
        if producto["costo_promedio_centavos"] is not None:
            centavos = producto["costo_promedio_centavos"]
            self.costo.insert(0, f"{centavos // 100}.{centavos % 100:02d}")
            self.costo.configure(state="disabled")

    def guardar(self) -> None:
        try:
            categoria = next(item for item in self.categorias if item["nombre"] == self.categoria.get())
            minimo = int(self.minimo.get() or "0")
            if self.producto_id is None:
                existencia = int(self.existencia.get() or "0")
                self.tienda.crear_producto(
                    self.nombre.get(), categoria["id"], self.precio.get(), existencia, minimo,
                    self.costo.get() or None,
                )
            else:
                self.tienda.actualizar_producto(
                    self.producto_id, self.nombre.get(), categoria["id"],
                    self.precio.get(), minimo,
                )
            self.limpiar()
            self.refrescar()
            self._notificar()
        except (ValueError, StopIteration) as error:
            messagebox.showerror("Revisa los datos", str(error) or "Elige una categoría.", parent=self)

    def nueva_categoria(self) -> None:
        nombre = simpledialog.askstring("Nueva categoría", "Nombre de la categoría:", parent=self)
        if nombre is None:
            return
        try:
            self.tienda.crear_categoria(nombre)
            self.refrescar()
            self.categoria.set(nombre.strip())
        except ValueError as error:
            messagebox.showerror("No se pudo crear", str(error), parent=self)

    def ajustar(self) -> None:
        if self.producto_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista.", parent=self)
            return
        cantidad = simpledialog.askinteger(
            "Ajustar existencias", "Unidades a agregar (usa un número negativo para salida):",
            parent=self, minvalue=-1_000_000, maxvalue=1_000_000,
        )
        if cantidad is None:
            return
        try:
            self.tienda.ajustar_existencia(self.producto_id, cantidad, "Ajuste manual")
            self.refrescar()
            self._notificar()
        except ValueError as error:
            messagebox.showerror("No se pudo ajustar", str(error), parent=self)

    def asignar_costo(self) -> None:
        if self.producto_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista.", parent=self)
            return
        try:
            self.tienda.establecer_costo_inicial(self.producto_id, self.costo.get())
            self.costo.configure(state="disabled")
            self.refrescar()
            self._notificar()
        except ValueError as error:
            messagebox.showerror("No se pudo asignar el costo", str(error), parent=self)

    def registrar_compra(self) -> None:
        if self.producto_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista.", parent=self)
            return
        cantidad = simpledialog.askinteger(
            "Registrar compra", "Unidades compradas:", parent=self, minvalue=1,
            maxvalue=1_000_000,
        )
        if cantidad is None:
            return
        costo = simpledialog.askstring(
            "Registrar compra", "Costo de compra por unidad:", parent=self
        )
        if costo is None:
            return
        try:
            self.tienda.registrar_compra(self.producto_id, cantidad, costo)
            self.refrescar()
            self._notificar()
        except ValueError as error:
            messagebox.showerror("No se pudo registrar la compra", str(error), parent=self)

    def desactivar(self) -> None:
        if self.producto_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la lista.", parent=self)
            return
        if messagebox.askyesno(
            "Desactivar producto", "Dejará de aparecer en nuevas ventas. ¿Continuar?", parent=self
        ):
            try:
                self.tienda.desactivar_producto(self.producto_id)
                self.limpiar()
                self.refrescar()
                self._notificar()
            except ValueError as error:
                messagebox.showerror("No se pudo desactivar", str(error), parent=self)

    def limpiar(self) -> None:
        self.producto_id = None
        for campo in (self.nombre, self.precio, self.minimo, self.existencia, self.costo):
            campo.configure(state="normal")
            campo.delete(0, "end")
        self.tabla.selection_remove(self.tabla.selection())

    def _notificar(self) -> None:
        if self.al_cambiar:
            self.al_cambiar()
