"""Resumen de ventas del día y productos que necesitan reposición."""

import tkinter as tk
from tkinter import ttk

from modelos import Tienda, mostrar_dinero


class ReportesFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda) -> None:
        super().__init__(parent, padding=16)
        self.tienda = tienda
        self.resumen = ttk.Label(self, font=("", 15, "bold"))
        self.resumen.pack(anchor="w", pady=(0, 16))
        ttk.Label(self, text="Productos en su stock mínimo o por debajo",
                  font=("", 12, "bold")).pack(anchor="w", pady=(0, 6))
        self.tabla = ttk.Treeview(
            self, columns=("nombre", "existencia", "minimo"), show="headings", height=14
        )
        for columna, titulo, ancho in (
            ("nombre", "Producto", 300), ("existencia", "Unidades disponibles", 160),
            ("minimo", "Stock mínimo", 150),
        ):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho)
        self.tabla.pack(fill="both", expand=True)
        ttk.Button(self, text="Actualizar reporte", command=self.refrescar).pack(
            anchor="e", pady=8
        )
        self.refrescar()

    def refrescar(self) -> None:
        resumen = self.tienda.resumen_hoy()
        self.resumen.configure(
            text=(f"Resumen de hoy: {resumen['cantidad']} ventas  |  "
                  f"Total vendido: {mostrar_dinero(resumen['total'])}")
        )
        self.tabla.delete(*self.tabla.get_children())
        for producto in self.tienda.productos_bajo_stock():
            self.tabla.insert(
                "", "end",
                values=(producto["nombre"], producto["existencia"], producto["stock_minimo"]),
            )
