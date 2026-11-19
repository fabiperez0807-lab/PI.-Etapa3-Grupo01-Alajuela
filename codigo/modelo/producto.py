"""Modelo: catálogo de productos (estado en memoria), limpieza, filtros y orden.

Evolución de modelo.py (Etapa 2): se conservan las funciones del catálogo
(buscar_producto, agregar_producto, incrementar_stock, ...) y se agregan la
carga/guardado en CSV, la limpieza de datos, el filtrado y el ordenamiento.
NO imprime nada ni pide datos al usuario.

Cada producto es un diccionario con las columnas de inventario.csv más
'marcas' (lista de motivos de revisión; no se guarda en el CSV).
"""
import copy
import os

from modelo import persistencia
from modelo.fecha import FORMATO_FECHA
from datetime import datetime

CAMPOS_ORDENAMIENTO = {"nombre": "nombre", "stock": "stock", "precio": "precio_venta"}
ESTADOS = ("disponible", "bajo", "agotado")
_NULOS = {"", "nan", "null", "none", "n/a", "na", "-"}

# Estado en memoria
_catalogo = []
_reporte_calidad = {}


# ------------------------------------------------------------ utilidades
def es_vacio(valor):
    return valor is None or str(valor).strip().lower() in _NULOS


def a_entero(valor):
    """Convierte a int o devuelve None si no es posible."""
    if es_vacio(valor):
        return None
    try:
        numero = float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None
    return int(numero) if numero == int(numero) else None


def a_decimal(valor):
    """Convierte a float o devuelve None si no es posible."""
    if es_vacio(valor):
        return None
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None


def fecha_valida(texto):
    try:
        datetime.strptime(texto, FORMATO_FECHA)
        return True
    except (ValueError, TypeError):
        return False


def normalizar_categoria(texto):
    return str(texto).strip().capitalize()


def estado_stock(producto):
    """'agotado' (stock <= 0), 'bajo' (stock <= mínimo) o 'disponible'."""
    if producto["stock"] <= 0:
        return "agotado"
    if producto["stock"] <= producto["stock_minimo"]:
        return "bajo"
    return "disponible"


# ------------------------------------------------------- catálogo (Etapa 2)
def buscar_producto(codigo):
    for producto in _catalogo:
        if producto["codigo"] == codigo:
            return producto
    return None


def existe_producto(codigo):
    return buscar_producto(codigo) is not None


def cantidad_productos():
    return len(_catalogo)


def agregar_producto(producto):
    if existe_producto(producto["codigo"]):
        raise ValueError("el código ya existe")
    nuevo = dict(producto)
    nuevo.setdefault("marcas", [])
    _catalogo.append(nuevo)


def obtener_catalogo():
    """Copia profunda: la vista nunca puede alterar los datos del modelo."""
    return copy.deepcopy(_catalogo)


def obtener_producto(codigo):
    """Copia del producto, o None si no existe.

    Corrección respecto a la versión entregada de la Etapa 2, que devolvía la
    función copy.deepcopy en lugar de la copia del producto.
    """
    producto = buscar_producto(codigo)
    return copy.deepcopy(producto) if producto is not None else None


def incrementar_stock(codigo, cantidad):
    producto = buscar_producto(codigo)
    producto["stock"] += cantidad
    return producto["stock"]


def descontar_stock(codigo, cantidad):
    """Descuenta unidades. Función que el controlador de la Etapa 2 llamaba pero
    que faltaba en el modelo entregado."""
    producto = buscar_producto(codigo)
    if producto is None or cantidad > producto["stock"]:
        raise ValueError("stock insuficiente o producto inexistente")
    producto["stock"] -= cantidad
    return producto["stock"]


def categorias():
    return sorted({p["categoria"] for p in _catalogo})


def reiniciar():
    _catalogo.clear()
    _reporte_calidad.clear()


# --------------------------------------------------------- persistencia (CSV)
def cargar_catalogo(duplicados="consolidar"):
    """Lee inventario.csv, limpia los datos y los deja en memoria.

    Evolución de cargar_catalogo_desde_csv (Etapa 2), que ignoraba en silencio
    las filas con errores: ahora se corrigen, descartan o marcan y se reporta.
    """
    filas = persistencia.cargar_inventario()
    productos, reporte = limpiar_inventario(filas, duplicados)
    reporte["advertencias"] = persistencia.advertencias()
    if reporte["corregidos"] or reporte["descartados"]:
        copia = persistencia.respaldar(persistencia.ruta_inventario())
        if copia:
            reporte["advertencias"].append(f"Se guardó una copia del archivo original como {os.path.basename(copia)} (en la carpeta de datos).")
    _catalogo.clear()
    _catalogo.extend(productos)
    _reporte_calidad.clear()
    _reporte_calidad.update(reporte)
    return copy.deepcopy(reporte)


def guardar_catalogo():
    persistencia.guardar_inventario(_catalogo)


def obtener_reporte_calidad():
    return copy.deepcopy(_reporte_calidad)


# ---------------------------------------------------------------- limpieza
def limpiar_inventario(filas, duplicados="consolidar"):
    """Limpia las filas crudas del CSV. Devuelve (productos, reporte).

    duplicados: 'consolidar' suma el stock de los códigos repetidos;
                'notificar' conserva el primero y solo reporta la anomalía.
    El reporte cuenta registros (no cambios individuales).
    """
    reporte = {"leidos": len(filas), "cargados": 0, "corregidos": 0,
               "descartados": 0, "marcados": 0, "duplicados": 0, "detalle": []}
    por_codigo = {}
    corregidos = set()

    def nota(n, texto):
        reporte["detalle"].append(f"Fila {n}: {texto}")

    for i, fila in enumerate(filas):
        n = i + 2  # fila real en el archivo (1 = encabezado)
        if es_vacio(fila.get("codigo")):
            reporte["descartados"] += 1
            nota(n, "sin código de producto; se descartó.")
            continue
        p = {"codigo": str(fila["codigo"]).strip().upper(), "marcas": []}
        codigo = p["codigo"]

        if es_vacio(fila.get("nombre")):
            p["nombre"] = "SIN NOMBRE"
            corregidos.add(codigo)
            nota(n, f"{codigo} sin nombre; se usó 'SIN NOMBRE'.")
        else:
            p["nombre"] = str(fila["nombre"]).strip()

        if es_vacio(fila.get("categoria")):
            p["categoria"] = "Sin categoría"
            corregidos.add(codigo)
            nota(n, f"{codigo} sin categoría; se usó 'Sin categoría'.")
        else:
            p["categoria"] = normalizar_categoria(fila["categoria"])

        for campo in ("stock", "stock_minimo"):
            valor = a_entero(fila.get(campo))
            if valor is None:
                p[campo] = 0
                corregidos.add(codigo)
                nota(n, f"{codigo} {campo} vacío o inválido; se usó 0.")
            else:
                p[campo] = valor
                if valor < 0:
                    p["marcas"].append(f"{campo} negativo")
                    nota(n, f"{codigo} {campo} negativo ({valor}); marcado para revisión.")

        for campo in ("precio_compra", "precio_venta"):
            valor = a_decimal(fila.get(campo))
            if valor is None:
                p[campo] = 0.0
                corregidos.add(codigo)
                p["marcas"].append(f"{campo} faltante")
                nota(n, f"{codigo} {campo} vacío o inválido; se usó 0 y se marcó.")
            else:
                p[campo] = valor
                if valor < 0:
                    p["marcas"].append(f"{campo} negativo")
                    nota(n, f"{codigo} {campo} negativo; marcado para revisión.")

        if p["precio_venta"] < p["precio_compra"]:
            p["marcas"].append("precio de venta menor al de compra")
            nota(n, f"{codigo} precio de venta menor al de compra; marcado para revisión.")

        fecha = "" if es_vacio(fila.get("fecha_vencimiento")) else str(fila["fecha_vencimiento"]).strip()
        if fecha and not fecha_valida(fecha):
            nota(n, f"{codigo} fecha de vencimiento inválida ('{fecha}'); se dejó vacía.")
            p["marcas"].append("fecha de vencimiento inválida")
            corregidos.add(codigo)
            fecha = ""
        p["fecha_vencimiento"] = fecha

        if codigo in por_codigo:
            existente = por_codigo[codigo]
            reporte["duplicados"] += 1
            reporte["descartados"] += 1
            if duplicados == "consolidar":
                existente["stock"] += p["stock"]
                corregidos.add(codigo)
                nota(n, f"{codigo} duplicado; se consolidó el stock (+{p['stock']}).")
            else:
                nota(n, f"{codigo} duplicado; se conservó el primer registro (anomalía notificada).")
            continue
        por_codigo[codigo] = p

    productos = list(por_codigo.values())
    reporte["cargados"] = len(productos)
    reporte["corregidos"] = len(corregidos)
    reporte["marcados"] = sum(1 for p in productos if p["marcas"])
    return productos, reporte


# ----------------------------------------------- filtro y ordenamiento
def filtrar(productos, categoria=None, precio_min=None, precio_max=None, estado=None):
    """Filtra por categoría, rango de precio de venta y/o estado de stock."""
    resultado = []
    for p in productos:
        if categoria and p["categoria"].lower() != str(categoria).strip().lower():
            continue
        if precio_min is not None and p["precio_venta"] < precio_min:
            continue
        if precio_max is not None and p["precio_venta"] > precio_max:
            continue
        if estado and estado_stock(p) != estado:
            continue
        resultado.append(p)
    return resultado


def ordenar(productos, campo="nombre", descendente=False):
    """Ordena por 'nombre', 'stock' o 'precio'."""
    if campo not in CAMPOS_ORDENAMIENTO:
        raise ValueError(f"Campo de ordenamiento no válido: {campo}")
    clave = CAMPOS_ORDENAMIENTO[campo]
    if clave == "nombre":
        return sorted(productos, key=lambda p: p["nombre"].lower(), reverse=descendente)
    return sorted(productos, key=lambda p: p[clave], reverse=descendente)


def consultar(categoria=None, precio_min=None, precio_max=None, estado=None,
              orden=None, descendente=False):
    """Copia del catálogo filtrada y (opcionalmente) ordenada."""
    productos = filtrar(obtener_catalogo(), categoria, precio_min, precio_max, estado)
    return ordenar(productos, orden, descendente) if orden else productos
