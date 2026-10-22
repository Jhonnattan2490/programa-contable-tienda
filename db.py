"""Acceso SQLite para la aplicación de la tienda."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


class BaseDatos:
    """Administra el archivo SQLite y la creación inicial del esquema."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar()

    @contextmanager
    def conectar(self) -> Iterator[sqlite3.Connection]:
        """Entrega una conexión que confirma o revierte cada bloque."""
        conexion = sqlite3.connect(self.ruta, timeout=15)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            with conexion:
                yield conexion
        finally:
            conexion.close()

    def inicializar(self) -> None:
        """Crea las tablas necesarias y una categoría inicial."""
        with self.conectar() as conexion:
            conexion.executescript(
                """
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
                );
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL COLLATE NOCASE,
                    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
                    precio_centavos INTEGER NOT NULL CHECK(precio_centavos >= 0),
                    costo_promedio_centavos INTEGER CHECK(costo_promedio_centavos >= 0),
                    existencia INTEGER NOT NULL DEFAULT 0 CHECK(existencia >= 0),
                    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK(stock_minimo >= 0),
                    activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0, 1)),
                    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT NOT NULL DEFAULT '',
                    activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0, 1)),
                    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY,
                    fecha TEXT NOT NULL,
                    total_centavos INTEGER NOT NULL CHECK(total_centavos >= 0),
                    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS detalle_ventas (
                    id INTEGER PRIMARY KEY,
                    venta_id INTEGER NOT NULL REFERENCES ventas(id),
                    producto_id INTEGER NOT NULL REFERENCES productos(id),
                    nombre_producto TEXT NOT NULL,
                    cantidad INTEGER NOT NULL CHECK(cantidad > 0),
                    precio_unitario_centavos INTEGER NOT NULL
                        CHECK(precio_unitario_centavos >= 0),
                    costo_unitario_centavos INTEGER
                        CHECK(costo_unitario_centavos >= 0)
                );
                CREATE TABLE IF NOT EXISTS movimientos_inventario (
                    id INTEGER PRIMARY KEY,
                    producto_id INTEGER NOT NULL REFERENCES productos(id),
                    fecha TEXT NOT NULL,
                    cantidad INTEGER NOT NULL CHECK(cantidad != 0),
                    motivo TEXT NOT NULL,
                    venta_id INTEGER REFERENCES ventas(id),
                    costo_unitario_centavos INTEGER
                        CHECK(costo_unitario_centavos >= 0)
                );
                CREATE TABLE IF NOT EXISTS movimientos_caja (
                    id INTEGER PRIMARY KEY,
                    fecha TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso', 'Egreso')),
                    concepto TEXT NOT NULL,
                    monto_centavos INTEGER NOT NULL CHECK(monto_centavos > 0),
                    producto_id INTEGER REFERENCES productos(id),
                    venta_id INTEGER REFERENCES ventas(id)
                );
                CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
                CREATE INDEX IF NOT EXISTS idx_detalle_venta ON detalle_ventas(venta_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_caja_venta
                    ON movimientos_caja(venta_id) WHERE venta_id IS NOT NULL;
                """
            )
            for tabla, columna, definicion in (
                ("productos", "costo_promedio_centavos", "INTEGER CHECK(costo_promedio_centavos >= 0)"),
                ("detalle_ventas", "costo_unitario_centavos", "INTEGER CHECK(costo_unitario_centavos >= 0)"),
                ("movimientos_inventario", "costo_unitario_centavos", "INTEGER CHECK(costo_unitario_centavos >= 0)"),
            ):
                columnas = {
                    fila["name"] for fila in conexion.execute(f"PRAGMA table_info({tabla})")
                }
                if columna not in columnas:
                    conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            conexion.execute(
                "INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", ("General",)
            )
            conexion.execute(
                """INSERT OR IGNORE INTO movimientos_caja
                   (fecha, tipo, concepto, monto_centavos, venta_id)
                   SELECT fecha, 'Ingreso', 'Venta #' || id, total_centavos, id
                   FROM ventas WHERE total_centavos > 0"""
            )
