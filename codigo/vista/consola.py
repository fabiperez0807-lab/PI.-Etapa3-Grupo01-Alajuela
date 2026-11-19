"""Vista: toda la entrada y salida por consola (heredada de vista1.py, Etapa 2).

Solo muestra información y recoge lo que escribe la persona usuaria. No importa
el modelo ni modifica datos: recibe diccionarios y listas ya preparados.
"""

ANCHO = 78


def pedir_texto(mensaje):
    return input(mensaje)


def mostrar_mensaje(texto):
    print(texto)


def mostrar_exito(texto):
    print(f"[OK] {texto}")


def mostrar_error(texto):
    print(f"[ERROR] {texto}")


def mostrar_aviso(texto):
    print(f"[!] {texto}")


def mostrar_titulo(texto):
    print("\n" + "=" * ANCHO)
    print(texto.center(ANCHO))
    print("=" * ANCHO)


def mostrar_bienvenida(fecha_texto, cantidad_productos, cantidad_facturas):
    mostrar_titulo("DISTRIBUIDORA INDUSTRIAL DEL PACÍFICO S.A.")
    print("Sistema de inventario y ventas".center(ANCHO))
    print(f"Fecha del sistema: {fecha_texto}".center(ANCHO))
    print(f"Datos cargados: {cantidad_productos} productos y {cantidad_facturas} facturas "
          "(opción 7: reporte de calidad)".center(ANCHO))


def mostrar_menu():
    mostrar_titulo("MENÚ PRINCIPAL")
    print("  1. Registrar producto")
    print("  2. Actualizar stock")
    print("  3. Realizar venta")
    print("  4. Generar alertas")
    print("  5. Consultar inventario (filtrar y ordenar)")
    print("  6. Consultar ventas")
    print("  7. Reporte de calidad de datos")
    print("  8. Generar reportes gráficos")
    print("  0. Salir")


def mostrar_inventario(filas):
    """filas: productos con las claves extra 'stock_bajo' (bool) y 'marcas'."""
    mostrar_titulo("INVENTARIO")
    if not filas:
        print("No hay productos que coincidan.")
        return
    print(f"{'Código':<8}{'Nombre':<26}{'Categoría':<11}{'Stock':>6}{'Mín':>5}"
          f"{'P.Venta':>10} {'Vence':<11}")
    print("-" * ANCHO)
    for p in filas:
        nombre = p["nombre"][:24] + ("!" if p["marcas"] else "")
        alerta = "*" if p["stock_bajo"] else " "
        print(f"{p['codigo']:<8}{nombre:<26}{p['categoria'][:10]:<11}{p['stock']:>5}{alerta}"
              f"{p['stock_minimo']:>5}{p['precio_venta']:>10,.2f} {p['fecha_vencimiento'] or '-':<11}")
    print("-" * ANCHO)
    print(f"{len(filas)} producto(s).  * = stock bajo   ! = marcado para revisión (opción 7)")


def mostrar_resumen_venta(lineas, subtotal, total_impuestos, total_general):
    mostrar_titulo("RESUMEN DE LA VENTA")
    print(f"{'Código':<8}{'Producto':<28}{'Cant.':>6}{'P.Unit.':>10}{'Subtotal':>12}")
    print("-" * ANCHO)
    for l in lineas:
        print(f"{l['codigo']:<8}{l['nombre'][:27]:<28}{l['cantidad']:>6}"
              f"{l['precio_unitario']:>10,.2f}{l['subtotal']:>12,.2f}")
    print("-" * ANCHO)
    print(f"{'Subtotal:':>52}{subtotal:>12,.2f}")
    print(f"{'Impuesto (13 %):':>52}{total_impuestos:>12,.2f}")
    print(f"{'TOTAL A PAGAR:':>52}{total_general:>12,.2f}")


def mostrar_stock_actualizado(cambios):
    """cambios: lista de (código, nombre, stock_anterior, stock_nuevo)."""
    print("\nStock actualizado:")
    for codigo, nombre, antes, despues in cambios:
        print(f"  {codigo} {nombre}: {antes} -> {despues}")


def mostrar_ventas(ventas, titulo):
    mostrar_titulo(titulo)
    if not ventas:
        print("No hay ventas registradas.")
        return
    print(f"{'Factura':<10}{'Fecha y hora':<21}{'Líneas':>7}{'Impuestos':>15}{'Total':>16}")
    print("-" * ANCHO)
    for v in ventas:
        nota = " !" if any(not l["valida"] for l in v["productos_vendidos"]) else ""
        print(f"{v['numero_factura']:<10}{(v['fecha'] or '-'):<21}{len(v['productos_vendidos']):>7}"
              f"{v['total_impuestos']:>15,.2f}{v['total_general']:>16,.2f}{nota}")
    print("-" * ANCHO)
    print(f"{'TOTAL VENDIDO:':<38}{sum(v['total_impuestos'] for v in ventas):>15,.2f}"
          f"{sum(v['total_general'] for v in ventas):>16,.2f}")
    print(f"{len(ventas)} factura(s).  ! = tiene líneas marcadas que no se suman (opción 7)")


def mostrar_alertas(alertas, fecha_texto):
    mostrar_titulo(f"ALERTAS DEL INVENTARIO — {fecha_texto}")
    if not alertas:
        print("No hay alertas.")
        return
    print(f"{'Código':<8}{'Tipo':<21}Mensaje")
    print("-" * ANCHO)
    for a in alertas:
        print(f"{a['codigo_producto']:<8}{a['tipo_alerta']:<21}{a['mensaje']}")
    print("-" * ANCHO)
    print(f"{len(alertas)} alerta(s).")


def mostrar_calidad(inventario, ventas):
    mostrar_titulo("REPORTE DE CALIDAD DE DATOS (carga inicial)")
    for nombre, r in (("Inventario", inventario), ("Ventas", ventas)):
        print(f"\n{nombre}:")
        print(f"   Registros leídos:      {r['leidos']}")
        print(f"   Registros cargados:    {r['cargados']}")
        print(f"   Registros corregidos:  {r['corregidos']}")
        print(f"   Registros descartados: {r['descartados']}")
        print(f"   Registros marcados:    {r['marcados']}")
        if "duplicados" in r:
            print(f"   Duplicados detectados: {r['duplicados']}")
        for aviso in r.get("advertencias", []):
            print(f"   Aviso: {aviso}")
        if r["detalle"]:
            print("   Detalle:")
            for linea in r["detalle"]:
                print(f"      - {linea}")


def mostrar_rutas_graficos(rutas):
    if not rutas:
        print("No hay datos suficientes para generar gráficos.")
        return
    print("\nGráficos guardados en:")
    for ruta in rutas:
        print(f"   {ruta}")


def pausar():
    input("\nPresione ENTER para volver al menú...")
