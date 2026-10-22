# Gestión de la tienda

Aplicación de escritorio en español para administrar productos, existencias,
ventas, historial, reportes básicos y clientes. Está hecha con Tkinter y SQLite,
sin dependencias de ejecución externas. La base de datos `tienda.db` se crea
automáticamente junto al script; al ejecutar un `.exe` empaquetado se crea junto
al ejecutable.

La pestaña **Cuentas** muestra las ventas por producto, el valor conocido del
inventario, la ganancia bruta y el corte mensual de entradas y salidas. Al crear
productos o usar **Registrar compra**, registra el costo unitario de compra para
calcular el costo promedio y la utilidad de las ventas posteriores. En productos
que ya estaban creados, usa **Asignar costo inicial** para valorar las unidades
actuales; no se estiman costos de ventas históricas que no fueron guardados. Las
compras de inventario y los gastos registrados en Cuentas aparecen como salidas
del corte mensual; las ventas aparecen como entradas.

## Requisitos y ejecución

- Python 3.10 o superior.
- Tkinter instalado. En Windows normalmente viene incluido con Python; si el
  instalador de Python ofrece la opción **tcl/tk and IDLE**, déjala seleccionada.

Abre una terminal en esta carpeta y ejecuta:

```text
python main.py
```

## Crear un ejecutable de un solo archivo en Windows

1. Instala Python para Windows y marca la opción para agregarlo al `PATH`.
2. Abre CMD o PowerShell en la carpeta del proyecto.
3. Instala PyInstaller:

   ```text
   py -m pip install pyinstaller
   ```

4. Empaqueta la aplicación:

   ```text
   py -m PyInstaller --noconfirm --clean --onefile --windowed --name Tienda main.py
   ```

5. El archivo `dist\Tienda.exe` es el ejecutable. Cópialo a una carpeta donde la
   usuaria pueda guardar archivos. Al abrirlo por primera vez, aparecerá
   `tienda.db` junto al `.exe`; conviene hacer copias de seguridad de ese archivo.

Para empezar de nuevo, cierra la aplicación y guarda una copia de seguridad
antes de mover o reemplazar `tienda.db`. Los datos se guardan localmente y no se
sincronizan con otros equipos.

Al actualizar una instalación existente, conserva `tienda.db`: la aplicación
agrega automáticamente las tablas y campos nuevos sin borrar ventas ni productos.
Haz una copia de seguridad del archivo antes de instalar una actualización.

## Pruebas de la lógica

```text
python -m unittest discover -s tests -v
```
