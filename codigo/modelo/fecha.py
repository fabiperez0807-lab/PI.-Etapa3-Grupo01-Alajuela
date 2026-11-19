"""Modelo: fecha del sistema.

Heredado de la Etapa 2: las alertas de vencimiento dependen de «hoy», por lo que
el programa acepta una fecha simulada (python main.py 2026-10-19).
Corrección respecto a la Etapa 2: el formato era "%y-%M-%d" (año de 2 dígitos y
minutos); el correcto es "%Y-%m-%d".
"""
from datetime import date, datetime

FORMATO_FECHA = "%Y-%m-%d"
_fecha_sistema = date.today()


def fijar_fecha(texto_fecha):
    """Fija la fecha del sistema. Lanza ValueError si el texto no es AAAA-MM-DD."""
    global _fecha_sistema
    _fecha_sistema = datetime.strptime(texto_fecha, FORMATO_FECHA).date()


def obtener_fecha():
    return _fecha_sistema


def fecha_hora_actual():
    """Fecha del sistema + hora real, con el formato que se guarda en ventas.csv."""
    return f"{_fecha_sistema.isoformat()} {datetime.now():%H:%M:%S}"
