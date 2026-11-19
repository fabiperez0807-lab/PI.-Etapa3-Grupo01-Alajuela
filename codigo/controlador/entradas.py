"""Controlador: validación de entradas y solicitud de datos.

Heredado de la Etapa 2 (validar_texto_obligatorio, validar_entero_positivo,
validar_flotante_positivo, validar_fecha_opcional, solicitar, solicitar_confirmacion),
con validadores nuevos para los filtros de consulta. Cada validador recibe el
texto escrito y devuelve (es_valido, valor_convertido_o_mensaje_de_error).
"""
import math
from datetime import datetime

from modelo.fecha import FORMATO_FECHA
from modelo import producto
from vista import consola


def validar_texto_obligatorio(texto):
    texto = texto.strip()
    if not texto:
        return False, "Este dato es obligatorio."
    return True, texto


def validar_texto_opcional(texto):
    return True, texto.strip()


def validar_entero_positivo(texto):
    try:
        valor = int(texto.strip())
    except ValueError:
        return False, "Debe ingresar un número entero (sin decimales ni letras)."
    if valor <= 0:
        return False, "El valor debe ser mayor que cero."
    return True, valor


def validar_flotante_positivo(texto):
    try:
        valor = float(texto.strip().replace(",", "."))
    except ValueError:
        return False, "Debe ingresar un número válido (por ejemplo 1250.50)."
    if math.isnan(valor) or math.isinf(valor):
        return False, "Debe ingresar un número válido (por ejemplo 1250.50)."
    if valor <= 0:
        return False, "El valor debe ser mayor que cero."
    return True, valor


def validar_fecha_opcional(texto):
    texto = texto.strip()
    if texto == "":
        return True, ""
    try:
        datetime.strptime(texto, FORMATO_FECHA)
    except ValueError:
        return False, "Fecha inválida. Use el formato AAAA-MM-DD (por ejemplo 2026-12-31) o deje vacío."
    return True, texto


def validar_decimal_opcional(texto):
    texto = texto.strip()
    if texto == "":
        return True, None
    ok, valor = validar_flotante_positivo(texto)
    return (ok, valor)


def validar_estado_opcional(texto):
    texto = texto.strip().lower()
    if texto == "":
        return True, None
    if texto not in producto.ESTADOS:
        return False, "Estado no válido. Use: disponible, bajo o agotado (o deje vacío)."
    return True, texto


def validar_orden_opcional(texto):
    texto = texto.strip().lower()
    if texto == "":
        return True, None
    if texto not in producto.CAMPOS_ORDENAMIENTO:
        return False, "Campo no válido. Use: nombre, stock o precio (o deje vacío)."
    return True, texto


def validar_direccion_opcional(texto):
    texto = texto.strip().lower()
    if texto in ("", "asc"):
        return True, False
    if texto == "desc":
        return True, True
    return False, "Escriba asc (ascendente) o desc (descendente)."


def solicitar(mensaje, validador):
    """Repite la pregunta hasta que el dato sea válido."""
    while True:
        texto = consola.pedir_texto(mensaje)
        es_valido, resultado = validador(texto)
        if es_valido:
            return resultado
        consola.mostrar_error(resultado)


def solicitar_confirmacion(mensaje):
    """Pregunta s/n y devuelve True si la persona usuaria responde sí."""
    while True:
        respuesta = consola.pedir_texto(mensaje).strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        consola.mostrar_error("Responda con 's' (sí) o 'n' (no).")
