"""Controlador: arranque del sistema y despacho del menú principal (heredado de
iniciar/procesar_opcion de controlador.py, Etapa 2)."""
from modelo import persistencia, producto, venta
from modelo.fecha import fijar_fecha, obtener_fecha
from vista import consola
from controlador import inventario_ctrl, ventas_ctrl, reportes_ctrl, reglas

ACCIONES = {"1": inventario_ctrl.registrar_producto,
            "2": inventario_ctrl.actualizar_stock,
            "3": ventas_ctrl.realizar_venta,
            "4": reportes_ctrl.generar_alertas,
            "5": inventario_ctrl.consultar_inventario,
            "6": ventas_ctrl.consultar_ventas_del_dia,
            "7": reportes_ctrl.consultar_calidad_datos,
            "8": reportes_ctrl.generar_reportes_graficos}


def iniciar(fecha_texto=None, ruta_datos=None):
    """Prepara el sistema. Devuelve True si se pudo iniciar."""
    if fecha_texto:
        try:
            fijar_fecha(fecha_texto)
        except ValueError:
            consola.mostrar_error(f"Fecha inválida: {fecha_texto}. Use el formato AAAA-MM-DD.")
            return False
    if ruta_datos:
        persistencia.configurar_ruta(ruta_datos)
    try:
        persistencia.asegurar_archivos()
        producto.cargar_catalogo()
        venta.cargar_ventas(reglas.TASA_IMPUESTO)
    except persistencia.ErrorPersistencia as e:
        consola.mostrar_error(f"No se pudieron cargar los datos: {e}")
        return False
    consola.mostrar_bienvenida(obtener_fecha().isoformat(), producto.cantidad_productos(),
                               len(venta.obtener_ventas()))
    return True


def procesar_opcion(opcion):
    """Ejecuta la opción elegida. Devuelve False cuando se debe salir."""
    if opcion == "0":
        consola.mostrar_mensaje("\nHasta pronto.")
        return False
    accion = ACCIONES.get(opcion)
    if accion is None:
        consola.mostrar_error("Opción no válida. Elija un número del menú.")
        return True
    try:
        accion()
    except persistencia.ErrorPersistencia as e:
        consola.mostrar_error(f"Error de archivo: {e}")
    consola.pausar()
    return True


def ejecutar():
    seguir = True
    while seguir:
        consola.mostrar_menu()
        try:
            opcion = consola.pedir_texto("\nSeleccione una opción: ").strip()
            seguir = procesar_opcion(opcion)
        except (EOFError, KeyboardInterrupt):
            consola.mostrar_mensaje("\n\nSesión terminada.")
            seguir = False
