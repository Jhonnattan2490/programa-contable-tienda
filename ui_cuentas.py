"""Corte mensual de caja y resumen financiero del inventario."""

from datetime import date, datetime
import tkinter as tk
from tkinter import messagebox, ttk

from modelos import Tienda, mostrar_dinero


class CuentasFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, tienda: Tienda) -> None:
        super().__init__(parent, padding=12)
        self.tienda = tienda
        self.mes = tk.StringVar(value=date.today().strftime("%Y-%m"))
        selector = ttk.Frame(self)
        selector.pack(fill="x", pady=(0, 8))
        ttk.Label(selector, text="Mes (AAAA-MM):").pack(side="left")
        ttk.Entry(selector, textvariable=self.mes, width=10).pack(side="left", padx=8)
        ttk.Button(selector, text="Actualizar", command=self.refrescar).pack(side="left")
        self.resumen = ttk.Label(self, font=("", 14, "bold"))
        self.resumen.pack(anchor="w", pady=(0, 8))

        pestañas = ttk.Notebook(self)
        pestañas.pack(fill="both", expand=True)
        corte = ttk.Frame(pestañas, padding=8)
        cuentas = ttk.Frame(pestañas, padding=8)
        pestañas.add(corte, text="Corte mensual")
        pestañas.add(cuentas, text="Cuentas por producto")

        gasto = ttk.LabelFrame(corte, text="Registrar salida", padding=8)
        gasto.pack(fill="x", pady=(0, 8))
        ttk.Label(gasto, text="Concepto").pack(side="left")
        self.concepto = ttk.Entry(gasto, width=42)
        self.concepto.pack(side="left", padx=8)
        ttk.Label(gasto, text="Valor").pack(side="left")
        self.monto = ttk.Entry(gasto, width=14)
        self.monto.pack(side="left", padx=8)
        ttk.Button(gasto, text="Registrar gasto", command=self.registrar_gasto).pack(
            side="left"
        )

        self.movimientos = ttk.Treeview(
            corte, columns=("fecha", "tipo", "concepto", "monto"),
            show="headings", height=14,
        )
        for columna, titulo, ancho in (
            ("fecha", "Fecha", 155), ("tipo", "Tipo", 100),
            ("concepto", "Concepto", 490), ("monto", "Valor", 140),
        ):
            self.movimientos.heading(columna, text=titulo)
            self.movimientos.column(columna, width=ancho, anchor="w")
        self.movimientos.pack(fill="both", expand=True)

        ttk.Label(
            cuentas,
            text="La ganancia bruta conocida excluye ventas antiguas sin costo histórico.",
        ).pack(anchor="w", pady=(0, 6))
        self.productos = ttk.Treeview(
            cuentas,
            columns=("nombre", "invertido", "ventas", "costo", "ganancia", "stock", "pendiente"),
            show="headings", height=17,
        )
        for columna, titulo, ancho in (
            ("nombre", "Producto", 175), ("invertido", "Invertido", 120),
            ("ventas", "Vendido", 120), ("costo", "Costo vendido", 125),
            ("ganancia", "Ganancia bruta", 135),
            ("stock", "Valor en stock", 125), ("pendiente", "Unid. sin costo", 115),
        ):
            self.productos.heading(columna, text=titulo)
            self.productos.column(columna, width=ancho, anchor="w")
        self.productos.pack(fill="both", expand=True)
        self.refrescar()

    def refrescar(self) -> None:
        mes = self.mes.get().strip()
        try:
            fecha = datetime.strptime(f"{mes}-01", "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Mes inválido", "Escribe el mes con formato AAAA-MM.", parent=self)
            return
        mes = fecha.strftime("%Y-%m")
        self.mes.set(mes)
        resumen = self.tienda.resumen_corte_mensual(mes)
        self.resumen.configure(
            text=(f"Entradas: {mostrar_dinero(resumen['entradas_centavos'])}  |  "
                  f"Salidas: {mostrar_dinero(resumen['salidas_centavos'])}  |  "
                  f"Saldo: {mostrar_dinero(resumen['saldo_centavos'])}")
        )
        self.movimientos.delete(*self.movimientos.get_children())
        for movimiento in self.tienda.listar_movimientos_caja(mes):
            self.movimientos.insert(
                "", "end",
                values=(movimiento["fecha"], movimiento["tipo"], movimiento["concepto"],
                        mostrar_dinero(movimiento["monto_centavos"])),
            )
        self.productos.delete(*self.productos.get_children())
        for producto in self.tienda.resumen_cuentas_productos():
            ganancia = (
                "Incompleta" if producto["unidades_sin_costo"]
                else mostrar_dinero(producto["utilidad_centavos"])
            )
            invertido = mostrar_dinero(producto["invertido_centavos"])
            inventario = mostrar_dinero(producto["inventario_centavos"])
            if producto["existencia"] and producto["costo_promedio_centavos"] is None:
                invertido = "Sin costo"
                inventario = "Sin costo"
            self.productos.insert(
                "", "end",
                values=(
                    producto["nombre"], invertido,
                    mostrar_dinero(producto["recuperado_centavos"]),
                    mostrar_dinero(producto["costo_vendido_centavos"]), ganancia,
                    inventario,
                    producto["unidades_sin_costo"],
                ),
            )

    def registrar_gasto(self) -> None:
        try:
            self.tienda.registrar_gasto(self.concepto.get(), self.monto.get())
            self.concepto.delete(0, "end")
            self.monto.delete(0, "end")
            self.refrescar()
        except ValueError as error:
            messagebox.showerror("No se pudo registrar el gasto", str(error), parent=self)