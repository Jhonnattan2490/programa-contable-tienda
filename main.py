"""Inicio de la aplicación de escritorio para la tienda."""

from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from db import BaseDatos
from modelos import Tienda
from ui_cuentas import CuentasFrame
from ui_clientes import ClientesFrame
from ui_historial import HistorialFrame
from ui_productos import ProductosFrame
from ui_reportes import ReportesFrame
from ui_ventas import VentasFrame


def carpeta_aplicacion() -> Path:
    """Devuelve dónde guardar la base de datos junto a la app."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class Aplicacion(tk.Tk):
    """Ventana principal que reúne las pantallas y los datos compartidos."""

    def __init__(self) -> None:
        """Configura la ventana, abre la base de datos y crea las pestañas."""
        super().__init__()
        self.title("Tienda - Gestión")
        self.geometry("1050x700")
        self.minsize(850, 580)
        self.tienda = Tienda(BaseDatos(carpeta_aplicacion() / "tienda.db"))
        self._crear_interfaz()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _crear_interfaz(self) -> None:
        """Construye la ventana principal y agrega una pestaña por módulo."""
        ttk.Label(
            self, text="Gestión de la tienda", font=("", 18, "bold"), padding=(12, 12)
        ).pack(anchor="w")
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.vistas = [
            ProductosFrame(self.pestanas, self.tienda, self.refrescar),
            VentasFrame(self.pestanas, self.tienda, self.refrescar),
            HistorialFrame(self.pestanas, self.tienda),
            ReportesFrame(self.pestanas, self.tienda),
            CuentasFrame(self.pestanas, self.tienda),
            ClientesFrame(self.pestanas, self.tienda, self.refrescar),
        ]
        for vista, titulo in zip(
            self.vistas, ("Productos e inventario", "Registrar venta", "Historial",
                          "Reportes", "Cuentas", "Clientes")
        ):
            self.pestanas.add(vista, text=titulo)

    def refrescar(self) -> None:
        """Actualiza los datos visibles en todas las pantallas."""
        for vista in self.vistas:
            vista.refrescar()

    def _cerrar(self) -> None:
        """Pide confirmación antes de cerrar la aplicación."""
        if messagebox.askyesno("Salir", "¿Deseas cerrar la aplicación?", parent=self):
            self.destroy()


def main() -> None:
    """Inicia la ventana y muestra un aviso si ocurre un error de arranque."""
    try:
        Aplicacion().mainloop()
    except (OSError, RuntimeError) as error:
        messagebox.showerror("No se pudo iniciar la tienda", str(error))


if __name__ == "__main__":
    main()
