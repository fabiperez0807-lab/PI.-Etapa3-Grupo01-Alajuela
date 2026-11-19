"""Modelo: lectura y escritura de archivos planos (CSV).

Este módulo es la única capa que toca archivos. No imprime nada en pantalla
y no conoce las reglas de negocio: solo lee y escribe filas (diccionarios).
"""
import csv
import os
import shutil

COLUMNAS_INVENTARIO = ["codigo", "nombre", "categoria", "stock", "stock_minimo",
                       "precio_compra", "precio_venta", "fecha_vencimiento"]
COLUMNAS_VENTAS = ["numero_factura", "fecha", "codigo_producto", "cantidad",
                   "subtotal", "impuestos", "total"]

_RUTA_POR_DEFECTO = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos"))
_ruta_datos = _RUTA_POR_DEFECTO
_advertencias = []


class ErrorPersistencia(Exception):
    """Se lanza cuando no se puede leer o escribir un archivo."""


def configurar_ruta(ruta):
    """Cambia la carpeta donde están inventario.csv y ventas.csv."""
    global _ruta_datos
    _ruta_datos = os.path.abspath(ruta)


def ruta_datos():
    return _ruta_datos


def ruta_inventario():
    return os.path.join(_ruta_datos, "inventario.csv")


def ruta_ventas():
    return os.path.join(_ruta_datos, "ventas.csv")


def advertencias():
    """Mensajes generados durante la última carga (por ejemplo, codificación)."""
    return list(_advertencias)


def _asegurar_archivo(ruta, columnas):
    """Crea el archivo con sus encabezados si no existe o está vacío."""
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        if not os.path.exists(ruta) or os.path.getsize(ruta) == 0:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=columnas).writeheader()
            _advertencias.append(f"Se creó el archivo {os.path.basename(ruta)} con sus encabezados.")
    except OSError as e:
        raise ErrorPersistencia(f"No se pudo crear {ruta}: {e}")


def asegurar_archivos():
    """Garantiza que existan inventario.csv y ventas.csv."""
    _asegurar_archivo(ruta_inventario(), COLUMNAS_INVENTARIO)
    _asegurar_archivo(ruta_ventas(), COLUMNAS_VENTAS)


def _leer(ruta, columnas):
    _asegurar_archivo(ruta, columnas)
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, newline="", encoding=codificacion) as f:
                filas = []
                for fila in csv.DictReader(f):
                    fila.pop(None, None)  # columnas sobrantes en filas mal formadas
                    filas.append({c: fila.get(c) for c in columnas})
            if codificacion == "latin-1":
                _advertencias.append(f"{os.path.basename(ruta)} no estaba en UTF-8; "
                                     "se leyó como latin-1 y se guardará en UTF-8.")
            return filas
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise ErrorPersistencia(f"No se pudo leer {ruta}: {e}")
    raise ErrorPersistencia(f"No se pudo decodificar {ruta}.")


def _formato(valor):
    if isinstance(valor, float):
        return str(int(valor)) if valor == int(valor) else f"{valor:.2f}"
    return "" if valor is None else valor


def _escribir(ruta, columnas, registros):
    """Escribe en un archivo temporal y lo reemplaza, para evitar corrupción."""
    temporal = ruta + ".tmp"
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(temporal, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
            escritor.writeheader()
            for r in registros:
                escritor.writerow({c: _formato(r.get(c)) for c in columnas})
        os.replace(temporal, ruta)
    except OSError as e:
        raise ErrorPersistencia(f"No se pudo guardar {ruta}: {e}")


def cargar_inventario():
    """Devuelve las filas crudas (texto) de inventario.csv."""
    _advertencias.clear()
    return _leer(ruta_inventario(), COLUMNAS_INVENTARIO)


def cargar_ventas():
    """Devuelve las filas crudas (texto) de ventas.csv."""
    return _leer(ruta_ventas(), COLUMNAS_VENTAS)


def guardar_inventario(productos):
    _escribir(ruta_inventario(), COLUMNAS_INVENTARIO, productos)


def guardar_ventas(ventas):
    _escribir(ruta_ventas(), COLUMNAS_VENTAS, ventas)


def respaldar(ruta):
    """Copia el archivo original a <archivo>.bak (solo la primera vez).

    Se usa cuando la limpieza corrige o descarta registros, para no perder el
    contenido original al guardar la versión depurada.
    """
    copia = ruta + ".bak"
    try:
        if os.path.exists(ruta) and not os.path.exists(copia):
            shutil.copy2(ruta, copia)
            return copia
    except OSError as e:
        raise ErrorPersistencia(f"No se pudo crear el respaldo de {ruta}: {e}")
    return None
