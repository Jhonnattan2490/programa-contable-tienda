"""Reglas del negocio para productos, inventario, ventas y clientes."""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import sqlite3
from typing import Iterable

from db import BaseDatos


def convertir_a_centavos(valor: str | int | float | Decimal) -> int:
    """Convierte un importe escrito con punto o coma decimal a centavos."""
    texto = str(valor).strip().replace(",", ".")
    try:
        importe = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError("Escribe un precio válido, por ejemplo 1250,50.") from error
    if not importe.is_finite() or importe < 0:
        raise ValueError("El precio debe ser un número igual o mayor que cero.")
    return int((importe * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def mostrar_dinero(centavos: int) -> str:
    """Muestra centavos con separadores habituales en español."""
    unidades, decimales = divmod(centavos, 100)
    entero = f"{unidades:,}".replace(",", ".")
    return f"$ {entero},{decimales:02d}"


class Tienda:
    """Operaciones de negocio; mantiene cada venta en una transacción SQLite."""

    def __init__(self, base_datos: BaseDatos) -> None:
        self.db = base_datos

    @staticmethod
    def _filas(filas: Iterable[sqlite3.Row]) -> list[dict]:
        return [dict(fila) for fila in filas]

    def listar_categorias(self) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                "SELECT id, nombre FROM categorias ORDER BY nombre"
            ).fetchall()
        return self._filas(filas)

    def crear_categoria(self, nombre: str) -> None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("Escribe el nombre de la categoría.")
        try:
            with self.db.conectar() as conexion:
                conexion.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        except sqlite3.IntegrityError as error:
            raise ValueError("Ya existe una categoría con ese nombre.") from error

    def listar_productos(self, busqueda: str = "", incluir_inactivos: bool = False) -> list[dict]:
        consulta = """
            SELECT p.id, p.nombre, p.categoria_id, c.nombre AS categoria,
                   p.precio_centavos, p.costo_promedio_centavos,
                   p.existencia, p.stock_minimo
            FROM productos p JOIN categorias c ON c.id = p.categoria_id
            WHERE (? OR p.activo = 1) AND p.nombre LIKE ?
            ORDER BY p.nombre
        """
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                consulta, (incluir_inactivos, f"%{busqueda.strip()}%")
            ).fetchall()
        return self._filas(filas)

    def crear_producto(
        self, nombre: str, categoria_id: int, precio: str, existencia: int, stock_minimo: int,
        costo_unitario: str | None = None,
    ) -> None:
        nombre = nombre.strip()
        precio_centavos = convertir_a_centavos(precio)
        costo_centavos = (
            convertir_a_centavos(costo_unitario) if costo_unitario else None
        )
        if not nombre:
            raise ValueError("Escribe el nombre del producto.")
        if existencia < 0 or stock_minimo < 0:
            raise ValueError("Las existencias y el stock mínimo no pueden ser negativos.")
        with self.db.conectar() as conexion:
            cursor = conexion.execute(
                """INSERT INTO productos
                   (nombre, categoria_id, precio_centavos, costo_promedio_centavos,
                    existencia, stock_minimo)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nombre, categoria_id, precio_centavos, costo_centavos, existencia, stock_minimo),
            )
            if existencia:
                conexion.execute(
                    """INSERT INTO movimientos_inventario
                       (producto_id, fecha, cantidad, motivo, costo_unitario_centavos)
                       VALUES (?, ?, ?, ?, ?)""",
                    (cursor.lastrowid, datetime.now().isoformat(timespec="seconds"),
                     existencia, "Existencia inicial", costo_centavos),
                )
                if costo_centavos:
                    conexion.execute(
                        """INSERT INTO movimientos_caja
                           (fecha, tipo, concepto, monto_centavos, producto_id)
                           VALUES (?, 'Egreso', ?, ?, ?)""",
                        (datetime.now().isoformat(timespec="seconds"),
                         f"Compra inicial: {nombre}", existencia * costo_centavos,
                         cursor.lastrowid),
                    )

    def establecer_costo_inicial(self, producto_id: int, costo_unitario: str) -> None:
        costo_centavos = convertir_a_centavos(costo_unitario)
        with self.db.conectar() as conexion:
            producto = conexion.execute(
                "SELECT existencia, costo_promedio_centavos FROM productos WHERE id = ?",
                (producto_id,),
            ).fetchone()
            if producto is None:
                raise ValueError("No se encontró el producto seleccionado.")
            if producto["costo_promedio_centavos"] is not None:
                raise ValueError("El producto ya tiene un costo registrado.")
            conexion.execute(
                "UPDATE productos SET costo_promedio_centavos = ? WHERE id = ?",
                (costo_centavos, producto_id),
            )
            if producto["existencia"]:
                conexion.execute(
                    """INSERT INTO movimientos_inventario
                       (producto_id, fecha, cantidad, motivo, costo_unitario_centavos)
                       VALUES (?, ?, ?, ?, ?)""",
                    (producto_id, datetime.now().isoformat(timespec="seconds"),
                     producto["existencia"], "Valoración inicial", costo_centavos),
                )

    def registrar_compra(
        self, producto_id: int, cantidad: int, costo_unitario: str
    ) -> None:
        if not isinstance(cantidad, int) or cantidad <= 0:
            raise ValueError("La cantidad comprada debe ser un entero mayor que cero.")
        costo_centavos = convertir_a_centavos(costo_unitario)
        if costo_centavos <= 0:
            raise ValueError("El costo unitario debe ser mayor que cero.")
        fecha = datetime.now().isoformat(timespec="seconds")
        with self.db.conectar() as conexion:
            producto = conexion.execute(
                """SELECT nombre, existencia, costo_promedio_centavos
                   FROM productos WHERE id = ? AND activo = 1""",
                (producto_id,),
            ).fetchone()
            if producto is None:
                raise ValueError("No se encontró el producto seleccionado.")
            existencia = producto["existencia"]
            costo_anterior = producto["costo_promedio_centavos"]
            if existencia and costo_anterior is None:
                raise ValueError("Registra primero el costo inicial del inventario actual.")
            nueva_existencia = existencia + cantidad
            nuevo_costo = (
                costo_centavos if not existencia else
                (existencia * costo_anterior + cantidad * costo_centavos + nueva_existencia // 2)
                // nueva_existencia
            )
            total_compra = cantidad * costo_centavos
            conexion.execute(
                """UPDATE productos SET existencia = ?, costo_promedio_centavos = ?
                   WHERE id = ?""",
                (nueva_existencia, nuevo_costo, producto_id),
            )
            conexion.execute(
                """INSERT INTO movimientos_inventario
                   (producto_id, fecha, cantidad, motivo, costo_unitario_centavos)
                   VALUES (?, ?, ?, ?, ?)""",
                (producto_id, fecha, cantidad, "Compra de inventario", costo_centavos),
            )
            conexion.execute(
                """INSERT INTO movimientos_caja
                   (fecha, tipo, concepto, monto_centavos, producto_id)
                   VALUES (?, 'Egreso', ?, ?, ?)""",
                (fecha, f"Compra de inventario: {producto['nombre']}", total_compra, producto_id),
            )

    def registrar_gasto(self, concepto: str, monto: str) -> None:
        concepto = concepto.strip()
        monto_centavos = convertir_a_centavos(monto)
        if not concepto:
            raise ValueError("Escribe el concepto del gasto.")
        if monto_centavos <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        with self.db.conectar() as conexion:
            conexion.execute(
                """INSERT INTO movimientos_caja
                   (fecha, tipo, concepto, monto_centavos)
                   VALUES (?, 'Egreso', ?, ?)""",
                (datetime.now().isoformat(timespec="seconds"), concepto, monto_centavos),
            )

    def actualizar_producto(
        self, producto_id: int, nombre: str, categoria_id: int, precio: str, stock_minimo: int
    ) -> None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("Escribe el nombre del producto.")
        if stock_minimo < 0:
            raise ValueError("El stock mínimo no puede ser negativo.")
        with self.db.conectar() as conexion:
            cursor = conexion.execute(
                """UPDATE productos SET nombre = ?, categoria_id = ?,
                   precio_centavos = ?, stock_minimo = ?
                   WHERE id = ? AND activo = 1""",
                (nombre, categoria_id, convertir_a_centavos(precio), stock_minimo, producto_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("No se encontró el producto seleccionado.")

    def desactivar_producto(self, producto_id: int) -> None:
        with self.db.conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE productos SET activo = 0 WHERE id = ? AND activo = 1",
                (producto_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("No se encontró el producto seleccionado.")

    def ajustar_existencia(self, producto_id: int, cambio: int, motivo: str) -> None:
        if cambio == 0:
            raise ValueError("La cantidad del ajuste debe ser mayor que cero.")
        with self.db.conectar() as conexion:
            producto = conexion.execute(
                "SELECT existencia FROM productos WHERE id = ? AND activo = 1",
                (producto_id,),
            ).fetchone()
            if producto is None:
                raise ValueError("No se encontró el producto seleccionado.")
            if producto["existencia"] + cambio < 0:
                raise ValueError("No hay suficientes unidades para registrar esa salida.")
            conexion.execute(
                "UPDATE productos SET existencia = existencia + ? WHERE id = ?",
                (cambio, producto_id),
            )
            conexion.execute(
                """INSERT INTO movimientos_inventario
                   (producto_id, fecha, cantidad, motivo) VALUES (?, ?, ?, ?)""",
                (producto_id, datetime.now().isoformat(timespec="seconds"), cambio,
                 motivo.strip() or "Ajuste manual"),
            )

    def listar_clientes(self, incluir_inactivos: bool = False) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT id, nombre, telefono FROM clientes
                   WHERE ? OR activo = 1 ORDER BY nombre""",
                (incluir_inactivos,),
            ).fetchall()
        return self._filas(filas)

    def guardar_cliente(self, nombre: str, telefono: str = "", cliente_id: int | None = None) -> None:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("Escribe el nombre del cliente.")
        with self.db.conectar() as conexion:
            if cliente_id is None:
                conexion.execute(
                    "INSERT INTO clientes (nombre, telefono) VALUES (?, ?)",
                    (nombre, telefono.strip()),
                )
            else:
                cursor = conexion.execute(
                    """UPDATE clientes SET nombre = ?, telefono = ?
                       WHERE id = ? AND activo = 1""",
                    (nombre, telefono.strip(), cliente_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("No se encontró el cliente seleccionado.")

    def desactivar_cliente(self, cliente_id: int) -> None:
        with self.db.conectar() as conexion:
            cursor = conexion.execute(
                "UPDATE clientes SET activo = 0 WHERE id = ? AND activo = 1",
                (cliente_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("No se encontró el cliente seleccionado.")

    def registrar_venta(
        self, articulos: list[tuple[int, int]], cliente_id: int | None = None
    ) -> int:
        """Registra los artículos a precio de base de datos y descuenta el stock."""
        cantidades: dict[int, int] = {}
        for producto_id, cantidad in articulos:
            if not isinstance(cantidad, int) or cantidad <= 0:
                raise ValueError("Todas las cantidades deben ser números enteros mayores que cero.")
            cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad
        if not cantidades:
            raise ValueError("Agrega al menos un producto a la venta.")

        fecha = datetime.now().isoformat(timespec="seconds")
        with self.db.conectar() as conexion:
            conexion.execute("BEGIN IMMEDIATE")
            lineas = []
            total = 0
            for producto_id, cantidad in cantidades.items():
                producto = conexion.execute(
                    """SELECT nombre, precio_centavos, existencia,
                              costo_promedio_centavos FROM productos
                       WHERE id = ? AND activo = 1""",
                    (producto_id,),
                ).fetchone()
                if producto is None:
                    raise ValueError("Uno de los productos ya no está disponible.")
                if producto["existencia"] < cantidad:
                    raise ValueError(
                        f"No hay suficientes unidades de «{producto['nombre']}»."
                    )
                lineas.append((producto_id, producto["nombre"], cantidad,
                               producto["precio_centavos"],
                               producto["costo_promedio_centavos"]))
                total += cantidad * producto["precio_centavos"]

            if cliente_id is not None:
                cliente = conexion.execute(
                    "SELECT id FROM clientes WHERE id = ? AND activo = 1",
                    (cliente_id,),
                ).fetchone()
                if cliente is None:
                    raise ValueError("El cliente seleccionado ya no está disponible.")

            cursor = conexion.execute(
                "INSERT INTO ventas (fecha, total_centavos, cliente_id) VALUES (?, ?, ?)",
                (fecha, total, cliente_id),
            )
            venta_id = int(cursor.lastrowid)
            for producto_id, nombre, cantidad, precio, costo in lineas:
                conexion.execute(
                    """INSERT INTO detalle_ventas
                       (venta_id, producto_id, nombre_producto, cantidad,
                        precio_unitario_centavos, costo_unitario_centavos)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (venta_id, producto_id, nombre, cantidad, precio, costo),
                )
                conexion.execute(
                    "UPDATE productos SET existencia = existencia - ? WHERE id = ?",
                    (cantidad, producto_id),
                )
                conexion.execute(
                    """INSERT INTO movimientos_inventario
                       (producto_id, fecha, cantidad, motivo, venta_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (producto_id, fecha, -cantidad, "Venta", venta_id),
                )
            if total:
                conexion.execute(
                    """INSERT INTO movimientos_caja
                       (fecha, tipo, concepto, monto_centavos, venta_id)
                       VALUES (?, 'Ingreso', ?, ?, ?)""",
                    (fecha, f"Venta #{venta_id}", total, venta_id),
                )
        return venta_id

    def resumen_cuentas_productos(self) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT p.id, p.nombre, p.existencia, p.costo_promedio_centavos,
                          p.existencia * COALESCE(p.costo_promedio_centavos, 0)
                              AS inventario_centavos,
                          COALESCE(c.invertido_centavos, 0) AS invertido_centavos,
                          COALESCE(v.recuperado_centavos, 0) AS recuperado_centavos,
                          COALESCE(v.costo_vendido_centavos, 0) AS costo_vendido_centavos,
                          COALESCE(v.recuperado_centavos, 0)
                              - COALESCE(v.costo_vendido_centavos, 0) AS utilidad_centavos,
                          COALESCE(v.unidades_sin_costo, 0) AS unidades_sin_costo
                   FROM productos p
                   LEFT JOIN (
                       SELECT producto_id, SUM(cantidad * costo_unitario_centavos)
                                  AS invertido_centavos
                       FROM movimientos_inventario
                       WHERE cantidad > 0 AND costo_unitario_centavos IS NOT NULL
                       GROUP BY producto_id
                   ) c ON c.producto_id = p.id
                   LEFT JOIN (
                       SELECT producto_id,
                              SUM(cantidad * precio_unitario_centavos)
                                  AS recuperado_centavos,
                              SUM(CASE WHEN costo_unitario_centavos IS NULL THEN 0
                                  ELSE cantidad * costo_unitario_centavos END)
                                  AS costo_vendido_centavos,
                              SUM(CASE WHEN costo_unitario_centavos IS NULL
                                  THEN cantidad ELSE 0 END) AS unidades_sin_costo
                       FROM detalle_ventas GROUP BY producto_id
                   ) v ON v.producto_id = p.id
                   ORDER BY p.nombre"""
            ).fetchall()
        return self._filas(filas)

    def resumen_corte_mensual(self, mes: str) -> dict:
        with self.db.conectar() as conexion:
            fila = conexion.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN tipo = 'Ingreso' THEN monto_centavos END), 0)
                           AS entradas_centavos,
                       COALESCE(SUM(CASE WHEN tipo = 'Egreso' THEN monto_centavos END), 0)
                           AS salidas_centavos,
                       COUNT(*) AS movimientos
                   FROM movimientos_caja WHERE substr(fecha, 1, 7) = ?""",
                (mes,),
            ).fetchone()
        resumen = dict(fila)
        resumen["saldo_centavos"] = (
            resumen["entradas_centavos"] - resumen["salidas_centavos"]
        )
        return resumen

    def listar_movimientos_caja(self, mes: str) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT fecha, tipo, concepto, monto_centavos
                   FROM movimientos_caja WHERE substr(fecha, 1, 7) = ?
                   ORDER BY fecha DESC, id DESC""",
                (mes,),
            ).fetchall()
        return self._filas(filas)

    def listar_ventas(self, limite: int = 500) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT v.id, v.fecha, v.total_centavos,
                          COALESCE(c.nombre, 'Venta sin cliente') AS cliente,
                          COUNT(d.id) AS productos
                   FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id
                   JOIN detalle_ventas d ON d.venta_id = v.id
                   GROUP BY v.id ORDER BY v.id DESC LIMIT ?""",
                (limite,),
            ).fetchall()
        return self._filas(filas)

    def detalle_venta(self, venta_id: int) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT nombre_producto, cantidad, precio_unitario_centavos,
                          cantidad * precio_unitario_centavos AS subtotal_centavos
                   FROM detalle_ventas WHERE venta_id = ? ORDER BY id""",
                (venta_id,),
            ).fetchall()
        return self._filas(filas)

    def resumen_hoy(self) -> dict:
        hoy = datetime.now().date().isoformat()
        with self.db.conectar() as conexion:
            fila = conexion.execute(
                """SELECT COUNT(*) AS cantidad, COALESCE(SUM(total_centavos), 0) AS total
                   FROM ventas WHERE substr(fecha, 1, 10) = ?""",
                (hoy,),
            ).fetchone()
        return dict(fila)

    def productos_bajo_stock(self) -> list[dict]:
        with self.db.conectar() as conexion:
            filas = conexion.execute(
                """SELECT nombre, existencia, stock_minimo
                   FROM productos
                   WHERE activo = 1 AND existencia <= stock_minimo
                   ORDER BY existencia, nombre"""
            ).fetchall()
        return self._filas(filas)
