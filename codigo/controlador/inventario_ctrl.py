"""Controlador: lógica de negocio del inventario (registrar, actualizar, consultar).

Evolución de controlador.py (Etapa 2). Orquesta vista y modelo; no imprime,
no usa input() y no toca archivos (delega en el modelo).
"""
from modelo import producto, persistencia
from vista import consola
from controlador import entradas as ent
from controlador import reglas


def _guardar():
    try:
        producto.guardar_catalogo()
    except persistencia.ErrorPersistencia as e:
        consola.mostrar_error(f"El cambio quedó en memoria pero no se pudo guardar en el archivo: {e}")


def registrar_producto():
    consola.mostrar_titulo("REGISTRAR PRODUCTO")
    consola.mostrar_mensaje("(Escriba los datos solicitados. Cada dato se valida.)")
    while True:
        codigo = ent.solicitar("Código del producto: ", ent.validar_texto_obligatorio).upper()
        if " " in codigo:
            consola.mostrar_error("El código no puede contener espacios.")
        elif producto.existe_producto(codigo):
            consola.mostrar_error(f"Ya existe un producto con el código {codigo}.")
        else:
            break
    nombre = ent.solicitar("Nombre: ", ent.validar_texto_obligatorio)
    categoria = producto.normalizar_categoria(ent.solicitar("Categoría: ", ent.validar_texto_obligatorio))
    stock = ent.solicitar("Stock inicial: ", ent.validar_entero_positivo)
    stock_minimo = ent.solicitar("Stock mínimo: ", ent.validar_entero_positivo)
    precio_compra = ent.solicitar("Precio de compra: ", ent.validar_flotante_positivo)
    while True:
        precio_venta = ent.solicitar("Precio de venta: ", ent.validar_flotante_positivo)
        if precio_venta < precio_compra:
            consola.mostrar_error("El precio de venta no puede ser menor al precio de compra.")
        else:
            break
    fecha = ent.solicitar("Fecha de vencimiento AAAA-MM-DD (ENTER si no aplica): ", ent.validar_fecha_opcional)
    producto.agregar_producto({"codigo": codigo, "nombre": nombre, "categoria": categoria, "stock": stock,
                               "stock_minimo": stock_minimo, "precio_compra": precio_compra,
                               "precio_venta": precio_venta, "fecha_vencimiento": fecha})
    _guardar()
    consola.mostrar_exito(f"Producto {codigo} registrado correctamente.")


def actualizar_stock():
    consola.mostrar_titulo("ACTUALIZAR STOCK (reabastecimiento)")
    while True:
        codigo = ent.solicitar("Código del producto: ", ent.validar_texto_obligatorio).upper()
        prod = producto.obtener_producto(codigo)
        if prod is None:
            consola.mostrar_error(f"No existe el producto {codigo}.")
        else:
            break
    consola.mostrar_mensaje(f"{prod['nombre']} — stock actual: {prod['stock']} (mínimo {prod['stock_minimo']}).")
    cantidad = ent.solicitar("Unidades que ingresan: ", ent.validar_entero_positivo)
    nuevo = producto.incrementar_stock(codigo, cantidad)
    _guardar()
    consola.mostrar_exito(f"Stock de {prod['nombre']} actualizado: {prod['stock']} -> {nuevo}.")


def consultar_inventario():
    filas_filtro = {"categoria": None, "precio_min": None, "precio_max": None,
                    "estado": None, "orden": None, "descendente": False}
    if ent.solicitar_confirmacion("¿Desea filtrar u ordenar el inventario? (s/n): "):
        consola.mostrar_mensaje("(ENTER en cualquier pregunta = no aplicar ese criterio)")
        cat = ent.solicitar(f"Categoría ({', '.join(producto.categorias())}): ", ent.validar_texto_opcional)
        filas_filtro["categoria"] = cat or None
        filas_filtro["precio_min"] = ent.solicitar("Precio de venta mínimo: ", ent.validar_decimal_opcional)
        filas_filtro["precio_max"] = ent.solicitar("Precio de venta máximo: ", ent.validar_decimal_opcional)
        filas_filtro["estado"] = ent.solicitar("Estado (disponible/bajo/agotado): ", ent.validar_estado_opcional)
        filas_filtro["orden"] = ent.solicitar("Ordenar por (nombre/stock/precio): ", ent.validar_orden_opcional)
        if filas_filtro["orden"]:
            filas_filtro["descendente"] = ent.solicitar("Orden (asc/desc): ", ent.validar_direccion_opcional)
    filas = producto.consultar(**filas_filtro)
    for fila in filas:
        fila["stock_bajo"] = reglas.es_stock_bajo(fila)
    consola.mostrar_inventario(filas)
