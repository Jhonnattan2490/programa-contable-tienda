"""Pruebas de las operaciones principales de la tienda."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import sqlite3

from db import BaseDatos
from modelos import Tienda, convertir_a_centavos, mostrar_dinero


class TiendaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directorio = tempfile.TemporaryDirectory()
        self.tienda = Tienda(BaseDatos(Path(self.directorio.name) / "prueba.db"))
        self.categoria_id = self.tienda.listar_categorias()[0]["id"]

    def tearDown(self) -> None:
        self.directorio.cleanup()

    def crear_producto(self, stock: int = 10) -> int:
        self.tienda.crear_producto("Arroz", self.categoria_id, "1250,50", stock, 2)
        return self.tienda.listar_productos()[0]["id"]

    def test_conversion_y_formato_de_dinero(self) -> None:
        self.assertEqual(convertir_a_centavos("1250,50"), 125050)
        self.assertEqual(mostrar_dinero(125050), "$ 1.250,50")
        with self.assertRaises(ValueError):
            convertir_a_centavos("-1")

    def test_venta_descuenta_inventario_y_conserva_detalle(self) -> None:
        producto_id = self.crear_producto()
        venta_id = self.tienda.registrar_venta([(producto_id, 2)])
        self.assertEqual(self.tienda.listar_productos()[0]["existencia"], 8)
        self.assertEqual(self.tienda.listar_ventas()[0]["total_centavos"], 250100)
        detalle = self.tienda.detalle_venta(venta_id)
        self.assertEqual(detalle[0]["subtotal_centavos"], 250100)

    def test_venta_sin_existencias_no_guarda_ni_descuenta(self) -> None:
        producto_id = self.crear_producto(stock=1)
        with self.assertRaisesRegex(ValueError, "No hay suficientes"):
            self.tienda.registrar_venta([(producto_id, 2)])
        self.assertEqual(self.tienda.listar_productos()[0]["existencia"], 1)
        self.assertEqual(self.tienda.listar_ventas(), [])

    def test_ajustes_de_stock_y_alertas(self) -> None:
        producto_id = self.crear_producto(stock=2)
        self.tienda.ajustar_existencia(producto_id, -1, "Merma")
        self.assertEqual(self.tienda.productos_bajo_stock()[0]["existencia"], 1)
        with self.assertRaisesRegex(ValueError, "No hay suficientes"):
            self.tienda.ajustar_existencia(producto_id, -2, "Salida")

    def test_cuentas_calcula_promedio_utilidad_y_corte_mensual(self) -> None:
        self.tienda.crear_producto("Cafe", self.categoria_id, "10", 2, 1, "4")
        producto_id = next(
            item["id"] for item in self.tienda.listar_productos() if item["nombre"] == "Cafe"
        )
        self.tienda.registrar_compra(producto_id, 2, "8")
        self.tienda.registrar_venta([(producto_id, 3)])
        self.tienda.registrar_gasto("Transporte", "2,50")

        cuenta = next(
            item for item in self.tienda.resumen_cuentas_productos()
            if item["id"] == producto_id
        )
        self.assertEqual(cuenta["costo_promedio_centavos"], 600)
        self.assertEqual(cuenta["invertido_centavos"], 2400)
        self.assertEqual(cuenta["recuperado_centavos"], 3000)
        self.assertEqual(cuenta["costo_vendido_centavos"], 1800)
        self.assertEqual(cuenta["utilidad_centavos"], 1200)
        self.assertEqual(cuenta["inventario_centavos"], 600)

        mes = datetime.now().strftime("%Y-%m")
        corte = self.tienda.resumen_corte_mensual(mes)
        self.assertEqual(corte["entradas_centavos"], 3000)
        self.assertEqual(corte["salidas_centavos"], 2650)
        self.assertEqual(corte["saldo_centavos"], 350)

    def test_ventas_historicas_no_se_duplican_al_reabrir_base(self) -> None:
        producto_id = self.crear_producto()
        self.tienda.registrar_venta([(producto_id, 1)])
        self.tienda.db.inicializar()
        mes = datetime.now().strftime("%Y-%m")
        self.assertEqual(self.tienda.resumen_corte_mensual(mes)["entradas_centavos"], 125050)

    def test_migra_base_anterior_sin_perder_ventas(self) -> None:
        ruta = Path(self.directorio.name) / "anterior.db"
        with sqlite3.connect(ruta) as conexion:
            conexion.executescript(
                """
                CREATE TABLE categorias (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
                CREATE TABLE productos (
                    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, categoria_id INTEGER NOT NULL,
                    precio_centavos INTEGER NOT NULL, existencia INTEGER NOT NULL,
                    stock_minimo INTEGER NOT NULL, activo INTEGER NOT NULL,
                    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE clientes (
                    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, telefono TEXT NOT NULL DEFAULT '',
                    activo INTEGER NOT NULL DEFAULT 1,
                    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE ventas (
                    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL,
                    total_centavos INTEGER NOT NULL, cliente_id INTEGER
                );
                CREATE TABLE detalle_ventas (
                    id INTEGER PRIMARY KEY, venta_id INTEGER NOT NULL, producto_id INTEGER NOT NULL,
                    nombre_producto TEXT NOT NULL, cantidad INTEGER NOT NULL,
                    precio_unitario_centavos INTEGER NOT NULL
                );
                CREATE TABLE movimientos_inventario (
                    id INTEGER PRIMARY KEY, producto_id INTEGER NOT NULL, fecha TEXT NOT NULL,
                    cantidad INTEGER NOT NULL, motivo TEXT NOT NULL, venta_id INTEGER
                );
                INSERT INTO categorias VALUES (1, 'General');
                INSERT INTO productos
                    (id, nombre, categoria_id, precio_centavos, existencia, stock_minimo, activo)
                    VALUES (1, 'Arroz', 1, 500, 2, 1, 1);
                INSERT INTO ventas VALUES (1, '2026-10-10T10:00:00', 500, NULL);
                INSERT INTO detalle_ventas
                    VALUES (1, 1, 1, 'Arroz', 1, 500);
                """
            )

        tienda_migrada = Tienda(BaseDatos(ruta))
        mes = "2026-10"
        cuenta = tienda_migrada.resumen_cuentas_productos()[0]
        self.assertEqual(cuenta["unidades_sin_costo"], 1)
        self.assertEqual(tienda_migrada.resumen_corte_mensual(mes)["entradas_centavos"], 500)


if __name__ == "__main__":
    unittest.main()
