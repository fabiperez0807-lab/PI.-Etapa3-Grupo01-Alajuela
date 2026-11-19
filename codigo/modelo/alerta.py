"""Modelo: alertas en memoria (heredado de modelo.py, Etapa 2).

Cada alerta es un diccionario {codigo_producto, tipo_alerta, mensaje} con
tipo_alerta en: "stock_bajo", "vencimiento_proximo" o "dato_atipico".
Corrección: la función se llamaba «limpar_alertas» (error de digitación) y el
controlador llamaba a «limpiar_alertas».
"""
import copy

_alertas = []


def limpiar_alertas():
    _alertas.clear()


def agregar_alerta(codigo_producto, tipo_alerta, mensaje):
    _alertas.append({"codigo_producto": codigo_producto,
                     "tipo_alerta": tipo_alerta,
                     "mensaje": mensaje})


def obtener_alertas():
    return copy.deepcopy(_alertas)


def reiniciar():
    _alertas.clear()
