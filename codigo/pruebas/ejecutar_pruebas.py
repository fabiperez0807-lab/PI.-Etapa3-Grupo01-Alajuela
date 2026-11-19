"""Ejecuta los casos del plan de pruebas y guarda los resultados reales.

Uso (desde la carpeta codigo/):  python pruebas/ejecutar_pruebas.py
Trabaja sobre copias temporales de los datos: nunca modifica datos/.
Los datos de ejemplo de las pruebas son los de la Etapa 2 (12 productos).
"""
import ast
import contextlib
import csv
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import date

os.environ.setdefault("MPLBACKEND", "Agg")
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, RAIZ)

from modelo import persistencia, producto, venta, alerta, fecha  # noqa: E402
from controlador import entradas, reglas, inventario_ctrl, ventas_ctrl, reportes_ctrl, menu_ctrl  # noqa: E402
from vista import consola  # noqa: E402
import main as programa  # noqa: E402

DATOS = os.path.join(RAIZ, "datos")
PRUEBAS = os.path.join(DATOS, "pruebas")
HOY = "2026-10-19"
RESULTADOS, CASOS = [], []

# Observaciones sobre fallas detectadas durante la preparación de las pruebas.
NOTAS = {
    "CP-08": ("En la primera ejecución este caso salió «Fallido» por un error de la propia prueba: la simulación de entradas "
              "no imprimía el texto de cada pregunta, donde aparece «disponible: 2», y la verificación no lo encontraba. "
              "El sistema funcionaba bien; se corrigió la simulación (ahora muestra pregunta y respuesta, como una terminal)."),
    "CP-18": ("En la primera ejecución salió «Fallido» por un error de la prueba: buscaba el texto «8 *» pero la tabla "
              "imprime «8*» (el asterisco va pegado al stock). Se corrigió la verificación; el sistema era correcto."),
}


def caso(id_, descripcion, entrada, esperado):
    def decorador(func):
        def ejecutar():
            temporal = tempfile.mkdtemp()
            try:
                obtenido, ok = func(temporal)
            except Exception as e:  # un error inesperado también es un fallo
                obtenido, ok = f"Excepción: {type(e).__name__}: {e}", False
            finally:
                shutil.rmtree(temporal, ignore_errors=True)
                persistencia.configurar_ruta(DATOS)
            RESULTADOS.append({"id": id_, "descripcion": descripcion, "entrada": entrada,
                               "esperado": esperado, "obtenido": obtenido,
                               "estado": "Aprobado" if ok else "Fallido", "nota": NOTAS.get(id_, "")})
        CASOS.append(ejecutar)
        return func
    return decorador


def sistema(carpeta, origen=DATOS, copiar=True, hoy=HOY):
    """Reinicia el estado del modelo y carga los datos de una copia temporal."""
    if copiar:
        for nombre in ("inventario.csv", "ventas.csv"):
            shutil.copy(os.path.join(origen, nombre), carpeta)
    persistencia.configurar_ruta(carpeta)
    producto.reiniciar(); venta.reiniciar(); alerta.reiniciar()
    fecha.fijar_fecha(hoy)
    persistencia.asegurar_archivos()
    producto.cargar_catalogo()
    venta.cargar_ventas(reglas.TASA_IMPUESTO)


def con_entradas(entradas_simuladas, funcion):
    """Ejecuta una función del controlador con entradas escritas por «el usuario»."""
    it = iter(entradas_simuladas)
    original = consola.pedir_texto
    def simulado(mensaje):
        valor = next(it)
        print(f"{mensaje}{valor}")  # igual que en una terminal: pregunta + respuesta
        return valor
    consola.pedir_texto = simulado
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            funcion()
    finally:
        consola.pedir_texto = original
    return buf.getvalue()


def lineas_csv(carpeta, nombre):
    with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
        return sum(1 for _ in f) - 1


# ================================================================= casos
@caso("CP-01", "Creación automática de archivos inexistentes",
      "Carpeta vacía (sin inventario.csv ni ventas.csv); se inicia el sistema.",
      "Se crean ambos archivos solo con los encabezados correctos y se cargan 0 productos y 0 facturas.")
def cp01(tmp):
    sistema(tmp, copiar=False)
    with open(os.path.join(tmp, "inventario.csv"), encoding="utf-8") as f:
        a = f.readline().strip()
    with open(os.path.join(tmp, "ventas.csv"), encoding="utf-8") as f:
        b = f.readline().strip()
    ok = (a == ",".join(persistencia.COLUMNAS_INVENTARIO) and b == ",".join(persistencia.COLUMNAS_VENTAS)
          and producto.cantidad_productos() == 0 and not venta.obtener_ventas())
    return f"Encabezados: «{a}» y «{b}». Productos: {producto.cantidad_productos()}, facturas: {len(venta.obtener_ventas())}.", ok


@caso("CP-02", "Carga inicial de los datos entregados (12 productos de la Etapa 2)",
      "datos/inventario.csv (12 productos) y datos/ventas.csv (40 facturas, 76 líneas); fecha del sistema 2026-10-19.",
      "Se cargan 12 productos y 40 facturas (76 líneas); el reporte de calidad indica 0 corregidos, 0 descartados y 0 marcados.")
def cp02(tmp):
    sistema(tmp)
    ri, rv = producto.obtener_reporte_calidad(), venta.obtener_reporte_calidad()
    ok = (producto.cantidad_productos() == 12 and len(venta.obtener_ventas()) == 40 and rv["cargados"] == 76
          and ri["corregidos"] == ri["descartados"] == ri["marcados"] == 0
          and rv["corregidos"] == rv["descartados"] == rv["marcados"] == 0)
    return (f"{producto.cantidad_productos()} productos, {len(venta.obtener_ventas())} facturas ({rv['cargados']} líneas). "
            f"Calidad inventario: {ri['corregidos']} corregidos, {ri['descartados']} descartados, {ri['marcados']} marcados."), ok


@caso("CP-03", "Validación de entradas (validadores heredados de la Etapa 2)",
      "Entero: «», «abc», «3.5», «-3», «0», « 12 ». Decimal: «nan», «inf», «abc», «0», «1250,50». Fecha: «2026-13-45», «2026-02-30», «31/12/2026», «hoy», «», «2026-12-31».",
      "Se rechazan los valores vacíos, con letras, decimales donde va un entero, negativos, cero, nan/inf y fechas imposibles o mal escritas. Se aceptan 12, 1250.5, la fecha vacía y 2026-12-31.")
def cp03(tmp):
    enteros = [entradas.validar_entero_positivo(t)[0] for t in ("", "abc", "3.5", "-3", "0")]
    decimales = [entradas.validar_flotante_positivo(t)[0] for t in ("nan", "inf", "abc", "0")]
    fechas = [entradas.validar_fecha_opcional(t)[0] for t in ("2026-13-45", "2026-02-30", "31/12/2026", "hoy")]
    ok12 = entradas.validar_entero_positivo(" 12 ")
    ok_dec = entradas.validar_flotante_positivo("1250,50")
    ok_fechas = (entradas.validar_fecha_opcional(""), entradas.validar_fecha_opcional("2026-12-31"))
    ok = (not any(enteros) and not any(decimales) and not any(fechas) and ok12 == (True, 12)
          and ok_dec == (True, 1250.5) and ok_fechas[0] == (True, "") and ok_fechas[1] == (True, "2026-12-31"))
    return (f"Rechazados: {len(enteros) - sum(enteros)}/5 enteros, {len(decimales) - sum(decimales)}/4 decimales, "
            f"{len(fechas) - sum(fechas)}/4 fechas. Aceptados: {ok12[1]}, {ok_dec[1]}, fecha vacía y «{ok_fechas[1][1]}»."), ok


@caso("CP-04", "Registrar producto con entradas inválidas y luego válidas",
      "Flujo de la opción 1: código repetido «lac001», código con espacio, stock «abc» y «0», precio de venta menor al de compra, fecha «31/12/2026»; luego datos correctos de PAP001.",
      "Se muestran 6 mensajes de error, se vuelve a preguntar cada dato y finalmente se registra PAP001 (categoría «Papelería», precio de venta 2200.50, stock 25).")
def cp04(tmp):
    sistema(tmp)
    salida = con_entradas(["lac001", "NUEVO 1", "pap001", "Cuaderno cuadriculado", "papelería", "abc", "0", "25", "10",
                           "1500", "1000", "2200,50", "31/12/2026", "2028-12-31"], inventario_ctrl.registrar_producto)
    p = producto.obtener_producto("PAP001")
    errores = salida.count("[ERROR]")
    ok = errores == 6 and p and p["categoria"] == "Papelería" and p["precio_venta"] == 2200.5 and p["stock"] == 25 \
        and "registrado correctamente" in salida
    return (f"{errores} mensajes de error. PAP001: «{p['nombre']}», categoría {p['categoria']}, stock {p['stock']}, "
            f"precio de venta {p['precio_venta']}, vence {p['fecha_vencimiento']}."), bool(ok)


@caso("CP-05", "Persistencia entre ejecuciones (registrar, cerrar y volver a abrir)",
      "Se registra PAP001 «Piñata grande» desde el controlador, se reinicia por completo el estado en memoria y se vuelven a cargar los CSV.",
      "El producto aparece tras recargar, con tildes y ñ intactas, y inventario.csv tiene 13 filas.")
def cp05(tmp):
    sistema(tmp)
    con_entradas(["PAP001", "Piñata grande", "Juguetería", "4", "2", "2500", "3500", ""], inventario_ctrl.registrar_producto)
    producto.reiniciar()  # simula cerrar el programa
    producto.cargar_catalogo()
    p = producto.obtener_producto("PAP001")
    filas = lineas_csv(tmp, "inventario.csv")
    ok = p and p["nombre"] == "Piñata grande" and p["categoria"] == "Juguetería" and p["stock"] == 4 and filas == 13
    return f"Tras recargar: «{p['nombre']}», categoría {p['categoria']}, stock {p['stock']}. Filas en inventario.csv: {filas}.", bool(ok)


@caso("CP-06", "Actualizar stock con entradas inválidas y persistencia",
      "Opción 2: código «ZZZ» (no existe); luego «beb002» con cantidades «texto», «0», «-3» y finalmente «24».",
      "Se muestran 4 errores; BEB002 pasa de 6 a 30 unidades y el cambio queda guardado en inventario.csv.")
def cp06(tmp):
    sistema(tmp)
    salida = con_entradas(["ZZZ", "beb002", "texto", "0", "-3", "24"], inventario_ctrl.actualizar_stock)
    producto.reiniciar(); producto.cargar_catalogo()
    stock = producto.obtener_producto("BEB002")["stock"]
    errores = salida.count("[ERROR]")
    return f"{errores} errores. Stock de BEB002 tras recargar el archivo: {stock}.", errores == 4 and stock == 30


@caso("CP-07", "Venta exitosa con IVA, descuento de stock y persistencia (caso de la Etapa 2)",
      "Opción 3: 3 unidades de ENL001 (₡1 400 c/u) y 2 de LAC001 (₡1 100 c/u); confirmar con «s».",
      "Subtotal 6 400.00, IVA 13 % = 832.00, total 7 232.00. Factura F-0041. Stock ENL001 60→57 y LAC001 40→38. ventas.csv pasa de 76 a 78 líneas y todo persiste al recargar.")
def cp07(tmp):
    sistema(tmp)
    salida = con_entradas(["ENL001", "3", "lac001", "2", "", "s"], ventas_ctrl.realizar_venta)
    v = venta.obtener_ventas()[-1]
    stock = (producto.obtener_producto("ENL001")["stock"], producto.obtener_producto("LAC001")["stock"])
    lineas = lineas_csv(tmp, "ventas.csv")
    venta.reiniciar(); producto.reiniciar(); producto.cargar_catalogo(); venta.cargar_ventas(reglas.TASA_IMPUESTO)
    recarga = (producto.obtener_producto("ENL001")["stock"], len(venta.obtener_ventas()))
    sub = sum(l["subtotal"] for l in v["productos_vendidos"])
    ok = (v["numero_factura"] == "F-0041" and sub == 6400.0 and v["total_impuestos"] == 832.0 and v["total_general"] == 7232.0
          and stock == (57, 38) and lineas == 78 and recarga == (57, 41) and "Factura F-0041 registrada" in salida)
    return (f"Factura {v['numero_factura']}: subtotal {sub:.2f}, IVA {v['total_impuestos']:.2f}, total {v['total_general']:.2f}. "
            f"Stock ENL001/LAC001: {stock[0]}/{stock[1]}. Líneas en ventas.csv: {lineas}. Tras recargar: stock ENL001 {recarga[0]}, {recarga[1]} facturas."), ok


@caso("CP-08", "Ventas rechazadas o canceladas no modifican nada",
      "Producto inexistente «XXX999»; 10 unidades de BEB002 (stock 6); 4+4 unidades de BEB002 (dos veces); venta válida de 1 LAC001 con confirmación «n»; venta sin productos.",
      "Cada intento muestra su mensaje (no existe / stock insuficiente / cancelada) y al final el stock y las 76 líneas de ventas.csv siguen iguales.")
def cp08(tmp):
    sistema(tmp)
    antes = (producto.obtener_producto("BEB002")["stock"], producto.obtener_producto("LAC001")["stock"], len(venta.obtener_ventas()))
    s1 = con_entradas(["XXX999", "BEB002", "10", "", ""], ventas_ctrl.realizar_venta)
    s2 = con_entradas(["BEB002", "4", "BEB002", "4", "BEB002", "2", "", "n"], ventas_ctrl.realizar_venta)
    s3 = con_entradas(["LAC001", "1", "", "n"], ventas_ctrl.realizar_venta)
    s4 = con_entradas([""], ventas_ctrl.realizar_venta)
    despues = (producto.obtener_producto("BEB002")["stock"], producto.obtener_producto("LAC001")["stock"], len(venta.obtener_ventas()))
    ok = (antes == despues and "No existe el producto XXX999" in s1 and "Stock insuficiente" in s1
          and "disponible: 2" in s2 and "Venta cancelada" in s2 and "Venta cancelada" in s3 and "no se agregaron productos" in s4
          and lineas_csv(tmp, "ventas.csv") == 76)
    return (f"Mensajes: «No existe el producto XXX999», «Stock insuficiente: disponible 6, solicitado 10», «disponible: 2» (el carrito suma lo ya pedido), "
            f"«Venta cancelada». Stock y facturas antes {antes}, después {despues}."), ok


@caso("CP-09", "Alertas de stock bajo y vencimiento (caso de la Etapa 2)",
      "Inventario inicial con fecha del sistema 2026-10-19 (alerta de vencimiento a 7 días).",
      "6 alertas: stock bajo en LAC002, BEB002, ENL002 y GRA002; vencimiento próximo de LAC001 (4 días) y LAC003 (7 días).")
def cp09(tmp):
    sistema(tmp)
    a = reportes_ctrl.calcular_alertas()
    bajo = sorted(x["codigo_producto"] for x in a if x["tipo_alerta"] == "stock_bajo")
    venc = sorted(x["codigo_producto"] for x in a if x["tipo_alerta"] == "vencimiento_proximo")
    ok = len(a) == 6 and bajo == ["BEB002", "ENL002", "GRA002", "LAC002"] and venc == ["LAC001", "LAC003"]
    return f"{len(a)} alertas. Stock bajo: {bajo}. Vencimiento próximo: {venc}.", ok


@caso("CP-10", "Casos límite de las reglas de negocio",
      "Stock igual al mínimo (ENL002 14/14); vence en 7 días, en 8 días y ayer; cantidad igual al stock y una unidad más; stock sugerido de BEB002 y ENL002.",
      "Stock = mínimo es bajo. Vence en 7 días: sí alerta; en 8: no; ayer: sí. Cantidad = stock se permite y stock + 1 no. Sugerido: BEB002 18, ENL002 14.")
def cp10(tmp):
    sistema(tmp)
    hoy = date(2026, 10, 19)
    enl2 = producto.obtener_producto("ENL002")
    prod = lambda f: {"fecha_vencimiento": f}
    r = (reglas.es_stock_bajo(enl2), reglas.vence_pronto(prod("2026-10-26"), hoy), reglas.vence_pronto(prod("2026-10-27"), hoy),
         reglas.vence_pronto(prod("2026-10-18"), hoy), reglas.vence_pronto(prod(""), hoy),
         reglas.hay_stock_suficiente({"stock": 6}, 6), reglas.hay_stock_suficiente({"stock": 6}, 7),
         reglas.calcular_stock_sugerido(producto.obtener_producto("BEB002")), reglas.calcular_stock_sugerido(enl2))
    ok = r == (True, True, False, True, False, True, False, 18, 14)
    return (f"stock=mín→bajo {r[0]}; 7 días {r[1]}; 8 días {r[2]}; ayer {r[3]}; sin fecha {r[4]}; cantidad=stock {r[5]}; stock+1 {r[6]}; "
            f"sugerido BEB002 {r[7]}, ENL002 {r[8]}."), ok


@caso("CP-11", "Manejo de valores nulos o vacíos al cargar el inventario",
      "datos/pruebas/inventario.csv: BEB010 sin nombre, BEB011 sin categoría, GRA010 sin stock, GRA011 sin precio de compra.",
      "Se reemplazan por valores por defecto («SIN NOMBRE», «Sin categoría», stock 0, precio 0) y GRA011 queda marcado; todo se informa en el reporte.")
def cp11(tmp):
    sistema(tmp, origen=PRUEBAS)
    g = producto.obtener_producto
    ok = (g("BEB010")["nombre"] == "SIN NOMBRE" and g("BEB011")["categoria"] == "Sin categoría" and g("GRA010")["stock"] == 0
          and g("GRA011")["precio_compra"] == 0.0 and "precio_compra faltante" in g("GRA011")["marcas"])
    return (f"BEB010 → «{g('BEB010')['nombre']}»; BEB011 → «{g('BEB011')['categoria']}»; GRA010 stock → {g('GRA010')['stock']}; "
            f"GRA011 precio_compra → {g('GRA011')['precio_compra']:.0f} con marcas {g('GRA011')['marcas']}."), ok


@caso("CP-12", "Detección y consolidación de duplicados por código",
      "datos/pruebas/inventario.csv: LAC001 aparece dos veces (stock 40 y 10).",
      "Queda un solo LAC001 con stock 50 y el reporte cuenta 1 duplicado. Con la opción «notificar» se conserva el primero (stock 40).")
def cp12(tmp):
    sistema(tmp, origen=PRUEBAS)
    consolidado = producto.obtener_producto("LAC001")["stock"]
    cantidad = sum(1 for p in producto.obtener_catalogo() if p["codigo"] == "LAC001")
    dup = producto.obtener_reporte_calidad()["duplicados"]
    producto.cargar_catalogo(duplicados="notificar")
    notifica = producto.obtener_producto("LAC001")["stock"]
    return (f"Consolidar: 1 registro LAC001 con stock {consolidado}; duplicados reportados: {dup}. Notificar: stock {notifica}.",
            consolidado == 50 and cantidad == 1 and dup == 1 and notifica == 40)


@caso("CP-13", "Validación de valores atípicos",
      "datos/pruebas: ENL010 con precio de venta (1200) menor al de compra (1500); ENL011 con stock -5; venta con cantidad -2.",
      "ENL010 y ENL011 quedan marcados para revisión (no se borran); la línea de venta con cantidad -2 queda excluida de los totales y genera una alerta «dato_atipico».")
def cp13(tmp):
    sistema(tmp, origen=PRUEBAS)
    e10, e11 = producto.obtener_producto("ENL010"), producto.obtener_producto("ENL011")
    neg = [l for v in venta.obtener_ventas() for l in v["productos_vendidos"] if l["cantidad"] < 0]
    atipicas = [x["codigo_producto"] for x in reportes_ctrl.calcular_alertas() if x["tipo_alerta"] == "dato_atipico"]
    ok = ("precio de venta menor al de compra" in e10["marcas"] and "stock negativo" in e11["marcas"]
          and neg and not neg[0]["valida"] and "ENL010" in atipicas and "ENL011" in atipicas)
    return f"ENL010: {e10['marcas']}. ENL011: {e11['marcas']}. Línea con cantidad {neg[0]['cantidad']}: válida={neg[0]['valida']}. Alertas dato_atipico: {sorted(atipicas)}.", bool(ok)


@caso("CP-14", "Reporte de calidad de datos (conteos)",
      "Carga de datos/pruebas (12 filas de inventario, 10 de ventas).",
      "Inventario: 12 leídos, 10 cargados, 7 corregidos, 2 descartados, 4 marcados, 1 duplicado. Ventas: 10 leídas, 8 cargadas, 2 corregidas, 2 descartadas, 3 marcadas.")
def cp14(tmp):
    sistema(tmp, origen=PRUEBAS)
    ri, rv = producto.obtener_reporte_calidad(), venta.obtener_reporte_calidad()
    a = (ri["leidos"], ri["cargados"], ri["corregidos"], ri["descartados"], ri["marcados"], ri["duplicados"])
    b = (rv["leidos"], rv["cargados"], rv["corregidos"], rv["descartados"], rv["marcados"])
    return (f"Inventario: {a[0]} leídos, {a[1]} cargados, {a[2]} corregidos, {a[3]} descartados, {a[4]} marcados, {a[5]} duplicado(s). "
            f"Ventas: {b[0]} leídas, {b[1]} cargadas, {b[2]} corregidas, {b[3]} descartadas, {b[4]} marcadas."), a == (12, 10, 7, 2, 4, 1) and b == (10, 8, 2, 2, 3)


@caso("CP-15", "Respaldo del archivo original cuando la limpieza lo modifica",
      "Se carga datos/pruebas (con errores) dos veces y se registra un producto (el CSV se reescribe depurado).",
      "Se crea inventario.csv.bak idéntico al original; la segunda carga no lo sobrescribe y el CSV depurado queda distinto del respaldo.")
def cp15(tmp):
    sistema(tmp, origen=PRUEBAS)
    original = open(os.path.join(PRUEBAS, "inventario.csv"), "rb").read()
    bak = os.path.join(tmp, "inventario.csv.bak")
    existe = os.path.exists(bak)
    con_entradas(["PAP002", "Regla 30cm", "Papelería", "5", "2", "300", "500", ""], inventario_ctrl.registrar_producto)
    producto.cargar_catalogo()  # segunda carga: no debe tocar el respaldo
    igual = existe and open(bak, "rb").read() == original
    depurado = open(os.path.join(tmp, "inventario.csv"), "rb").read() != original
    return f"inventario.csv.bak existe: {existe}; idéntico al original tras 2 cargas: {igual}; CSV depurado distinto: {depurado}.", bool(existe and igual and depurado)


@caso("CP-16", "Filtrado por categoría, rango de precio y estado de stock",
      "Inventario inicial: categoría «Lácteos»; precio de venta entre 1000 y 1500; estado «bajo»; estado «agotado»; «Enlatados» + «bajo».",
      "Lácteos: 3. Rango 1000-1500: 6 productos. Bajo: LAC002, BEB002, ENL002 y GRA002. Agotado: ninguno. Enlatados y bajo: ENL002.")
def cp16(tmp):
    sistema(tmp)
    lac = producto.consultar(categoria="lácteos")
    rango = producto.consultar(precio_min=1000, precio_max=1500)
    bajo = sorted(p["codigo"] for p in producto.consultar(estado="bajo"))
    ago = producto.consultar(estado="agotado")
    comb = [p["codigo"] for p in producto.consultar(categoria="Enlatados", estado="bajo")]
    ok = len(lac) == 3 and len(rango) == 6 and all(1000 <= p["precio_venta"] <= 1500 for p in rango) \
        and bajo == ["BEB002", "ENL002", "GRA002", "LAC002"] and ago == [] and comb == ["ENL002"]
    return f"Lácteos: {len(lac)}. Rango 1000-1500: {len(rango)}. Bajo: {bajo}. Agotado: {len(ago)}. Enlatados+bajo: {comb}.", ok


@caso("CP-17", "Ordenamiento por nombre, stock y precio (asc/desc)",
      "Inventario inicial ordenado por nombre asc, stock desc, precio asc y precio desc; campo inválido «color».",
      "Nombre ascendente (primero «Agua purificada 600ml»); stock descendente empieza en BEB001 (120); precio ascendente empieza en BEB001 (600) y termina en LAC003 (3 600); un campo inválido se rechaza.")
def cp17(tmp):
    sistema(tmp)
    nombres = [p["nombre"].lower() for p in producto.consultar(orden="nombre")]
    stock = producto.consultar(orden="stock", descendente=True)
    asc = producto.consultar(orden="precio")
    desc = producto.consultar(orden="precio", descendente=True)
    try:
        producto.consultar(orden="color"); rechazo = False
    except ValueError:
        rechazo = True
    ok = (nombres == sorted(nombres) and nombres[0] == "agua purificada 600ml" and stock[0]["codigo"] == "BEB001"
          and asc[0]["codigo"] == "BEB001" and asc[-1]["codigo"] == "LAC003" and desc[0]["codigo"] == "LAC003" and rechazo)
    return (f"Primer nombre «{nombres[0]}». Mayor stock {stock[0]['codigo']} ({stock[0]['stock']}). Precio: de {asc[0]['codigo']} ({asc[0]['precio_venta']:.0f}) "
            f"a {asc[-1]['codigo']} ({asc[-1]['precio_venta']:.0f}). Campo inválido rechazado: {rechazo}."), ok


@caso("CP-18", "Consulta de inventario con filtros desde el menú (opción 5)",
      "Entradas: filtrar «s», categoría «Lácteos», sin precios ni estado, ordenar por «precio» en «desc».",
      "Se listan los 3 lácteos del más caro al más barato: LAC003, LAC001, LAC002; LAC002 aparece con * (stock bajo).")
def cp18(tmp):
    sistema(tmp)
    s = con_entradas(["s", "Lácteos", "", "", "", "precio", "desc"], inventario_ctrl.consultar_inventario)
    orden = [c for c in ("LAC003", "LAC001", "LAC002") if c in s]
    pos = [s.index(c) for c in orden]
    ok = pos == sorted(pos) and "3 producto(s)" in s and "BEB001" not in s and "8*" in s
    return f"Salida con 3 productos en el orden {orden}; BEB001 no aparece; stock bajo marcado con *.", ok


@caso("CP-19", "Ventas totales por categoría (base del gráfico)",
      "Ventas iniciales; se compara el cálculo del sistema con una suma independiente leída directamente de ventas.csv.",
      "La suma por categoría coincide con la suma manual y el total general coincide con la suma de la columna total.")
def cp19(tmp):
    sistema(tmp)
    sis = venta.ventas_por_categoria(venta.obtener_ventas(), producto.obtener_catalogo())
    cat = {p["codigo"]: p["categoria"] for p in producto.obtener_catalogo()}
    manual, total = {}, 0.0
    with open(os.path.join(DATOS, "ventas.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            c = cat[fila["codigo_producto"]]
            manual[c] = round(manual.get(c, 0) + float(fila["total"]), 2)
            total += float(fila["total"])
    ok = len(sis) == len(manual) and all(abs(sis[c] - manual[c]) < 0.01 for c in manual) and abs(sum(sis.values()) - total) < 0.05
    return f"{len(sis)} categorías. Mayor: {next(iter(sis))} (₡{next(iter(sis.values())):,.2f}). Total general ₡{sum(sis.values()):,.2f} (suma manual ₡{total:,.2f}).", ok


@caso("CP-20", "Ventas del día con fecha simulada",
      "Fecha del sistema 2026-10-19: se consultan las ventas del día antes y después de vender; y las del 2026-10-18.",
      "Antes: 0 ventas. Después de una venta confirmada: 1 venta (F-0041, total 1 243.00). Las ventas del 2026-10-18 coinciden con el conteo independiente del CSV.")
def cp20(tmp):
    sistema(tmp)
    antes = len(venta.ventas_del_dia("2026-10-19"))
    con_entradas(["GRA001", "1", "", "s"], ventas_ctrl.realizar_venta)
    hoy = venta.ventas_del_dia("2026-10-19")
    ayer = len(venta.ventas_del_dia("2026-10-18"))
    with open(os.path.join(DATOS, "ventas.csv"), encoding="utf-8") as f:
        esperado_ayer = len({r["numero_factura"] for r in csv.DictReader(f) if r["fecha"].startswith("2026-10-18")})
    salida = con_entradas(["n"], ventas_ctrl.consultar_ventas_del_dia)
    ok = antes == 0 and len(hoy) == 1 and hoy[0]["total_general"] == 1356.0 and ayer == esperado_ayer and "VENTAS DEL DÍA — 2026-10-19" in salida
    return f"Antes {antes}; después {len(hoy)} ({hoy[0]['numero_factura']}, total {hoy[0]['total_general']:,.2f}). Ventas del 2026-10-18: {ayer} (esperadas {esperado_ayer}).", ok


@caso("CP-21", "Generación de gráficos con matplotlib",
      "Opción 8 «Generar reportes gráficos» con los datos iniciales, sin mostrar en pantalla.",
      "Se crean 4 archivos .png no vacíos: ventas por categoría, stock crítico, distribución por categoría y ventas por hora.")
def cp21(tmp):
    sistema(tmp)
    rutas = reportes_ctrl.generar_graficos(os.path.join(tmp, "g"), mostrar=False)
    tam = [os.path.getsize(r) for r in rutas]
    return f"{len(rutas)} archivos: " + ", ".join(f"{os.path.basename(r)} ({t // 1024} KB)" for r, t in zip(rutas, tam)), len(rutas) == 4 and all(t > 5000 for t in tam)


@caso("CP-22", "Codificación UTF-8 y archivo en otra codificación",
      "Se escribe un inventario.csv en latin-1 con «Piñata» y «Café» y se carga el sistema.",
      "Se leen correctamente los caracteres especiales, se emite una advertencia y al guardar el archivo queda en UTF-8.")
def cp22(tmp):
    with open(os.path.join(tmp, "inventario.csv"), "w", encoding="latin-1", newline="") as f:
        f.write(",".join(persistencia.COLUMNAS_INVENTARIO) + "\nK001,Piñata,Juguetes,5,2,2500,3500,\nK002,Café,Bebidas,9,3,1000,1500,\n")
    sistema(tmp, copiar=False)
    adv = producto.obtener_reporte_calidad()["advertencias"]
    producto.guardar_catalogo()
    texto = open(os.path.join(tmp, "inventario.csv"), encoding="utf-8").read()
    ok = producto.obtener_producto("K001")["nombre"] == "Piñata" and any("latin-1" in a for a in adv) and "Piñata" in texto and "Café" in texto
    return f"Leído: «{producto.obtener_producto('K001')['nombre']}», «{producto.obtener_producto('K002')['nombre']}». Advertencia emitida: {any('latin-1' in a for a in adv)}. Guardado en UTF-8 sin pérdida: {'Piñata' in texto}.", ok


@caso("CP-23", "Arranque con fecha y carpeta de datos por argumento",
      "Argumentos «2026-10-19 --datos <carpeta>», fecha inválida «2026-13-45» y «19/10/2026».",
      "Los argumentos se interpretan bien; con fecha válida el sistema inicia (True) y con fecha inválida no inicia (False) y muestra un error.")
def cp23(tmp):
    for n in ("inventario.csv", "ventas.csv"):
        shutil.copy(os.path.join(DATOS, n), tmp)
    a = programa.leer_argumentos(["2026-10-19", "--datos", tmp])
    b = programa.leer_argumentos([])
    producto.reiniciar(); venta.reiniciar()
    with contextlib.redirect_stdout(io.StringIO()):
        valido = menu_ctrl.iniciar("2026-10-19", tmp)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        inv1, inv2 = menu_ctrl.iniciar("2026-13-45", tmp), menu_ctrl.iniciar("19/10/2026", tmp)
    ok = a == ("2026-10-19", tmp) and b == (None, None) and valido is True and inv1 is False and inv2 is False and buf.getvalue().count("[ERROR]") == 2
    return f"Argumentos leídos: {a[0]} y carpeta indicada; sin argumentos: {b}. Inicio con fecha válida: {valido}; fechas inválidas: {inv1}, {inv2}.", ok


@caso("CP-24", "Separación de responsabilidades MVC (inspección automática del código fuente)",
      "Se analiza con el módulo ast el código de modelo/, vista/ y controlador/ en busca de print(), input(), open() e importaciones cruzadas.",
      "Modelo: sin print/input y sin importar vista ni controlador. Vista: sin importar modelo ni controlador. Controlador: sin print/input/open ni uso del módulo csv.")
def cp24(tmp):
    def analizar(carpeta):
        res = {}
        for nombre in sorted(os.listdir(os.path.join(RAIZ, carpeta))):
            if not nombre.endswith(".py") or nombre == "__init__.py":
                continue
            arbol = ast.parse(open(os.path.join(RAIZ, carpeta, nombre), encoding="utf-8").read())
            llamadas = {n.func.id for n in ast.walk(arbol) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            mods = set()
            for n in ast.walk(arbol):
                if isinstance(n, ast.Import):
                    mods |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.module:
                    mods.add(n.module.split(".")[0])
            res[nombre] = (llamadas, mods)
        return res
    fallos = []
    for n, (ll, m) in analizar("modelo").items():
        if ll & {"print", "input"} or m & {"vista", "controlador"}:
            fallos.append(f"modelo/{n}")
    for n, (ll, m) in analizar("vista").items():
        if m & {"modelo", "controlador"}:
            fallos.append(f"vista/{n}")
    for n, (ll, m) in analizar("controlador").items():
        if ll & {"print", "input", "open"} or "csv" in m:
            fallos.append(f"controlador/{n}")
    total = sum(len(analizar(c)) for c in ("modelo", "vista", "controlador"))
    return f"{total} módulos analizados. Violaciones encontradas: {fallos if fallos else 'ninguna'}.", not fallos


def main():
    for ejecutar in CASOS:
        ejecutar()
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(RESULTADOS, f, ensure_ascii=False, indent=2)
    for r in RESULTADOS:
        print(f"{r['id']} [{r['estado']}] {r['descripcion']}\n      → {r['obtenido']}")
    print(f"\n{sum(1 for r in RESULTADOS if r['estado'] == 'Aprobado')}/{len(RESULTADOS)} casos aprobados.")


if __name__ == "__main__":
    main()
