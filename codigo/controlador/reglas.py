"""Controlador: reglas de negocio (heredadas de controlador.py, Etapa 2).

Constantes y funciones puras de cálculo; no imprimen ni leen archivos.
"""
from datetime import datetime

from modelo import producto
from modelo.fecha import FORMATO_FECHA

TASA_IMPUESTO = 0.13           # IVA de 13 %
DIAS_ALERTA_VENCIMIENTO = 7    # se alerta si faltan 0 a 7 días (o ya venció)


def es_stock_bajo(prod):
    """Stock bajo = stock menor o igual al mínimo (incluye agotado)."""
    return producto.estado_stock(prod) != "disponible"


def dias_para_vencer(prod, fecha_actual):
    """Días hasta el vencimiento (negativo si ya venció); None si no aplica."""
    if not prod.get("fecha_vencimiento"):
        return None
    vence = datetime.strptime(prod["fecha_vencimiento"], FORMATO_FECHA).date()
    return (vence - fecha_actual).days


def vence_pronto(prod, fecha_actual):
    dias = dias_para_vencer(prod, fecha_actual)
    return dias is not None and dias <= DIAS_ALERTA_VENCIMIENTO


def hay_stock_suficiente(prod, cantidad):
    return cantidad <= prod["stock"]


def calcular_stock_sugerido(prod):
    """Unidades sugeridas para volver al doble del mínimo."""
    return max(prod["stock_minimo"] * 2 - prod["stock"], 0)


def calcular_venta(carrito):
    """carrito = lista de {'codigo', 'cantidad'}.

    Devuelve (lineas, subtotal, total_impuestos, total_general). Cada línea trae
    nombre, precio unitario, subtotal, impuestos y total.
    """
    lineas = []
    for item in carrito:
        prod = producto.obtener_producto(item["codigo"])
        subtotal = round(prod["precio_venta"] * item["cantidad"], 2)
        impuestos = round(subtotal * TASA_IMPUESTO, 2)
        lineas.append({"codigo": prod["codigo"], "nombre": prod["nombre"], "cantidad": item["cantidad"],
                       "precio_unitario": prod["precio_venta"], "subtotal": subtotal,
                       "impuestos": impuestos, "total": round(subtotal + impuestos, 2)})
    subtotal = round(sum(l["subtotal"] for l in lineas), 2)
    total_impuestos = round(sum(l["impuestos"] for l in lineas), 2)
    return lineas, subtotal, total_impuestos, round(subtotal + total_impuestos, 2)
