"""Historial de ventas y detalle por transacción."""

import tkinter as tk
from tkinter import messagebox, ttk

from modelos import Tienda, mostrar_dinero


class HistorialFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda) -> None:
        super().__init__(parent, padding=12)
        self.tienda = tienda
        ttk.Label(self, text="Ventas registradas", font=("", 14, "bold")).pack(anchor="w")
        ttk.Button(self, text="Actualizar", command=self.refrescar).pack(anchor="e", pady=6)
        self.tabla = ttk.Treeview(
            self, columns=("fecha", "cliente", "productos", "total"),
            show="headings", height=14,
        )
        for columna, titulo, ancho in (
            ("fecha", "Fecha", 190), ("cliente", "Cliente", 240),
            ("productos", "Líneas", 100), ("total", "Total", 150),
        ):
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(columna, width=ancho)
        self.tabla.pack(fill="both", expand=True)
        ttk.Button(self, text="Ver detalle de la venta", command=self.ver_detalle).pack(
            anchor="e", pady=8
        )
        self.refrescar()

    def refrescar(self) -> None:
        self.tabla.delete(*self.tabla.get_children())
        for venta in self.tienda.listar_ventas():
            self.tabla.insert(
                "", "end", iid=str(venta["id"]),
                values=(venta["fecha"], venta["cliente"], venta["productos"],
                        mostrar_dinero(venta["total_centavos"])),
            )

    def ver_detalle(self) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Selecciona una venta", "Elige una venta de la lista.", parent=self)
            return
        venta_id = int(seleccion[0])
        ventana = tk.Toplevel(self)
        ventana.title(f"Detalle de la venta #{venta_id}")
        ventana.transient(self.winfo_toplevel())
        ventana.grab_set()
        tabla = ttk.Treeview(
            ventana, columns=("producto", "cantidad", "precio", "subtotal"),
            show="headings", height=10,
        )
        for columna, titulo in (
            ("producto", "Producto"), ("cantidad", "Cantidad"),
            ("precio", "Precio unitario"), ("subtotal", "Subtotal"),
        ):
            tabla.heading(columna, text=titulo)
        tabla.pack(fill="both", expand=True, padx=12, pady=12)
        detalle = self.tienda.detalle_venta(venta_id)
        total = 0
        for linea in detalle:
            total += linea["subtotal_centavos"]
            tabla.insert(
                "", "end",
                values=(linea["nombre_producto"], linea["cantidad"],
                        mostrar_dinero(linea["precio_unitario_centavos"]),
                        mostrar_dinero(linea["subtotal_centavos"])),
            )
        ttk.Label(ventana, text=f"Total: {mostrar_dinero(total)}",
                  font=("", 12, "bold")).pack(anchor="e", padx=12, pady=(0, 12))
