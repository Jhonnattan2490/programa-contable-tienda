"""Registro sencillo de clientes."""

import tkinter as tk
from tkinter import messagebox, ttk

from modelos import Tienda


class ClientesFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda, al_cambiar=None) -> None:
        super().__init__(parent, padding=12)
        self.tienda = tienda
        self.al_cambiar = al_cambiar
        self.cliente_id: int | None = None
        formulario = ttk.LabelFrame(self, text="Datos del cliente", padding=10)
        formulario.pack(fill="x", pady=(0, 10))
        ttk.Label(formulario, text="Nombre").grid(row=0, column=0, sticky="w")
        self.nombre = ttk.Entry(formulario, width=35)
        self.nombre.grid(row=1, column=0, padx=(0, 10))
        ttk.Label(formulario, text="Teléfono (opcional)").grid(row=0, column=1, sticky="w")
        self.telefono = ttk.Entry(formulario, width=25)
        self.telefono.grid(row=1, column=1, padx=10)
        ttk.Button(formulario, text="Guardar", command=self.guardar).grid(row=1, column=2, padx=4)
        ttk.Button(formulario, text="Limpiar", command=self.limpiar).grid(row=1, column=3)
        ttk.Button(self, text="Desactivar cliente", command=self.desactivar).pack(
            anchor="e", pady=(0, 6)
        )
        self.tabla = ttk.Treeview(
            self, columns=("nombre", "telefono"), show="headings", height=16
        )
        self.tabla.heading("nombre", text="Nombre")
        self.tabla.heading("telefono", text="Teléfono")
        self.tabla.column("nombre", width=300)
        self.tabla.column("telefono", width=200)
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._seleccionar)
        self.refrescar()

    def refrescar(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for cliente in self.tienda.listar_clientes():
            self.tabla.insert(
                "", "end", iid=str(cliente["id"]),
                values=(cliente["nombre"], cliente["telefono"]),
            )

    def _seleccionar(self, _evento=None) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        self.cliente_id = int(seleccion[0])
        nombre, telefono = self.tabla.item(seleccion[0], "values")
        self.nombre.delete(0, "end")
        self.nombre.insert(0, nombre)
        self.telefono.delete(0, "end")
        self.telefono.insert(0, telefono)

    def guardar(self) -> None:
        try:
            self.tienda.guardar_cliente(self.nombre.get(), self.telefono.get(), self.cliente_id)
            self.limpiar()
            self.refrescar()
            if self.al_cambiar:
                self.al_cambiar()
        except ValueError as error:
            messagebox.showerror("Revisa los datos", str(error), parent=self)

    def desactivar(self) -> None:
        if self.cliente_id is None:
            messagebox.showinfo("Selecciona un cliente", "Elige un cliente de la lista.", parent=self)
            return
        if messagebox.askyesno(
            "Desactivar cliente", "¿Quieres que deje de aparecer en las ventas?", parent=self
        ):
            try:
                self.tienda.desactivar_cliente(self.cliente_id)
                self.limpiar()
                self.refrescar()
                if self.al_cambiar:
                    self.al_cambiar()
            except ValueError as error:
                messagebox.showerror("No se pudo desactivar", str(error), parent=self)

    def limpiar(self) -> None:
        self.cliente_id = None
        self.nombre.delete(0, "end")
        self.telefono.delete(0, "end")
        self.tabla.selection_remove(self.tabla.selection())
