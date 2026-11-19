"""Controlador: lógica de negocio de ventas y facturación (Etapa 2 + persistencia)."""
from modelo import producto, venta, persistencia
from modelo.fecha import obtener_fecha, fecha_hora_actual
from vista import consola
from controlador import entradas as ent
from controlador import reglas


def _armar_carrito():
    """Pide productos hasta que la persona deje el código vacío. Devuelve el carrito."""
    carrito = []
    consola.mostrar_mensaje("Escriba el código de cada producto. Deje el código vacío (ENTER) para terminar.")
    while True:
        codigo = consola.pedir_texto("Código del producto: ").strip().upper()
        if codigo == "":
            return carrito
        prod = producto.obtener_producto(codigo)
        if prod is None:
            consola.mostrar_error(f"No existe el producto {codigo}.")
            continue
        if prod["precio_venta"] <= 0:
            consola.mostrar_error(f"{prod['nombre']} tiene un precio de venta inválido; corríjalo antes de vender.")
            continue
        ya_en_carrito = sum(i["cantidad"] for i in carrito if i["codigo"] == codigo)
        disponible = prod["stock"] - ya_en_carrito
        if disponible <= 0:
            consola.mostrar_error(f"{prod['nombre']} no tiene stock disponible.")
            continue
        cantidad = ent.solicitar(f"Cantidad de {prod['nombre']} (disponible: {disponible}): ",
                                 ent.validar_entero_positivo)
        if not reglas.hay_stock_suficiente({"stock": disponible}, cantidad):
            consola.mostrar_error(f"Stock insuficiente: disponible {disponible}, solicitado {cantidad}.")
            continue
        for item in carrito:
            if item["codigo"] == codigo:
                item["cantidad"] += cantidad
                break
        else:
            carrito.append({"codigo": codigo, "cantidad": cantidad})


def realizar_venta():
    consola.mostrar_titulo("REALIZAR VENTA")
    carrito = _armar_carrito()
    if not carrito:
        consola.mostrar_aviso("Venta cancelada: no se agregaron productos.")
        return
    lineas, subtotal, total_impuestos, total_general = reglas.calcular_venta(carrito)
    consola.mostrar_resumen_venta(lineas, subtotal, total_impuestos, total_general)
    if not ent.solicitar_confirmacion("\n¿Confirmar la venta? (s/n): "):
        consola.mostrar_aviso("Venta cancelada. No se modificó el inventario.")
        return

    cambios = []
    for l in lineas:
        antes = producto.obtener_producto(l["codigo"])["stock"]
        despues = producto.descontar_stock(l["codigo"], l["cantidad"])
        cambios.append((l["codigo"], l["nombre"], antes, despues))
    nueva = {"numero_factura": venta.siguiente_numero_factura(), "fecha": fecha_hora_actual(),
             "productos_vendidos": [{"codigo": l["codigo"], "cantidad": l["cantidad"], "subtotal": l["subtotal"],
                                     "impuestos": l["impuestos"], "total": l["total"],
                                     "valida": True, "marcas": []} for l in lineas],
             "total_impuestos": total_impuestos, "total_general": total_general}
    venta.registrar_venta(nueva)
    try:
        venta.guardar_ventas()
        producto.guardar_catalogo()
    except persistencia.ErrorPersistencia as e:
        for codigo, _n, antes, despues in cambios:  # revierte la memoria
            producto.incrementar_stock(codigo, antes - despues)
        venta.quitar_ultima_venta()
        consola.mostrar_error(f"No se pudo guardar la venta; se canceló y el inventario no cambió. ({e})")
        return
    consola.mostrar_exito(f"Factura {nueva['numero_factura']} registrada. Total: {total_general:,.2f}")
    consola.mostrar_stock_actualizado(cambios)


def consultar_ventas_del_dia():
    hoy = obtener_fecha().isoformat()
    consola.mostrar_ventas(venta.ventas_del_dia(hoy), f"VENTAS DEL DÍA — {hoy}")
    if ent.solicitar_confirmacion("\n¿Desea ver también el historial completo? (s/n): "):
        consola.mostrar_ventas(venta.obtener_ventas(), "HISTORIAL COMPLETO DE VENTAS")
