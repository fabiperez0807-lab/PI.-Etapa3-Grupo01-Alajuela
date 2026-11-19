"""Modelo: ventas (estado en memoria), limpieza del historial y análisis.

Evolución de modelo.py (Etapa 2). En memoria, cada venta es un diccionario:
    {numero_factura, fecha, productos_vendidos: [líneas], total_impuestos, total_general}
y cada línea: {codigo, cantidad, subtotal, impuestos, total, valida, marcas}.
En ventas.csv se guarda una fila por línea. NO imprime ni pide datos.
"""
import copy
import os
from datetime import datetime

from modelo import persistencia

TOLERANCIA = 0.01
_FORMATOS_FECHA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")

_ventas = []
_reporte_calidad = {}


def _vacio(valor):
    return valor is None or str(valor).strip().lower() in ("", "nan", "null", "none", "n/a", "na", "-")


def _decimal(valor):
    if _vacio(valor):
        return None
    try:
        return float(str(valor).strip().replace(",", "."))
    except ValueError:
        return None


def parsear_fecha(texto):
    """Devuelve un datetime o None si el formato no es válido."""
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(str(texto).strip(), formato)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------- limpieza
def limpiar_ventas(filas, tasa_impuesto):
    """Limpia las filas crudas de ventas.csv. Devuelve (lineas, reporte).

    Las líneas con cantidad no positiva o sin importes quedan con valida=False:
    se conservan (para revisión), pero no entran en totales ni gráficos.
    """
    reporte = {"leidos": len(filas), "cargados": 0, "corregidos": 0,
               "descartados": 0, "marcados": 0, "detalle": []}
    lineas, corregidas, marcadas = [], set(), set()

    for i, fila in enumerate(filas):
        n = i + 2
        if _vacio(fila.get("numero_factura")) or _vacio(fila.get("codigo_producto")):
            reporte["descartados"] += 1
            reporte["detalle"].append(f"Fila {n}: sin número de factura o código de producto; se descartó.")
            continue
        cantidad = _decimal(fila.get("cantidad"))
        if cantidad is None or cantidad != int(cantidad):
            reporte["descartados"] += 1
            reporte["detalle"].append(f"Fila {n}: cantidad vacía o inválida; se descartó.")
            continue

        v = {"numero_factura": str(fila["numero_factura"]).strip(),
             "codigo": str(fila["codigo_producto"]).strip().upper(),
             "cantidad": int(cantidad), "marcas": [], "valida": True}

        fecha = "" if _vacio(fila.get("fecha")) else str(fila["fecha"]).strip()
        if not fecha or parsear_fecha(fecha) is None:
            v["marcas"].append("fecha faltante o inválida")
            reporte["detalle"].append(f"Fila {n}: fecha faltante o inválida; marcada.")
            marcadas.add(i)
            fecha = ""
        v["fecha"] = fecha

        if v["cantidad"] <= 0:
            v["marcas"].append("cantidad no positiva")
            v["valida"] = False
            marcadas.add(i)
            reporte["detalle"].append(f"Fila {n}: cantidad no positiva ({v['cantidad']}); "
                                      "marcada y excluida de los totales.")

        original = tuple(_decimal(fila.get(c)) for c in ("subtotal", "impuestos", "total"))
        sub, imp, tot = original
        if sub is None and tot is not None:
            sub = round(tot / (1 + tasa_impuesto), 2)
        if sub is not None and imp is None:
            imp = round(sub * tasa_impuesto, 2)
        if sub is not None and tot is None:
            tot = round(sub + imp, 2)
        if sub is None:
            v["marcas"].append("sin importes")
            v["valida"] = False
            marcadas.add(i)
            reporte["detalle"].append(f"Fila {n}: sin subtotal, impuestos ni total; marcada y excluida.")
            sub = imp = tot = 0.0
        elif None in original:
            corregidas.add(i)
            reporte["detalle"].append(f"Fila {n}: importe faltante; se recalculó.")
        elif abs(sub + imp - tot) > TOLERANCIA:
            tot = round(sub + imp, 2)
            corregidas.add(i)
            reporte["detalle"].append(f"Fila {n}: el total no coincidía con subtotal + impuestos; se corrigió.")
        v["subtotal"], v["impuestos"], v["total"] = sub, imp, tot
        lineas.append(v)

    reporte["cargados"] = len(lineas)
    reporte["corregidos"] = len(corregidas)
    reporte["marcados"] = len(marcadas)
    return lineas, reporte


def construir_ventas(lineas):
    """Agrupa las líneas por factura y calcula los totales (solo líneas válidas)."""
    facturas = {}
    for linea in lineas:
        v = facturas.setdefault(linea["numero_factura"], {
            "numero_factura": linea["numero_factura"], "fecha": linea["fecha"], "productos_vendidos": []})
        if not v["fecha"] and linea["fecha"]:
            v["fecha"] = linea["fecha"]
        v["productos_vendidos"].append({k: linea[k] for k in
                                        ("codigo", "cantidad", "subtotal", "impuestos", "total", "valida", "marcas")})
    for v in facturas.values():
        validas = [l for l in v["productos_vendidos"] if l["valida"]]
        v["total_impuestos"] = round(sum(l["impuestos"] for l in validas), 2)
        v["total_general"] = round(sum(l["total"] for l in validas), 2)
    return list(facturas.values())


def aplanar_ventas(ventas):
    """Convierte las ventas en filas (una por línea) para ventas.csv."""
    filas = []
    for v in ventas:
        for l in v["productos_vendidos"]:
            filas.append({"numero_factura": v["numero_factura"], "fecha": v["fecha"],
                          "codigo_producto": l["codigo"], "cantidad": l["cantidad"],
                          "subtotal": l["subtotal"], "impuestos": l["impuestos"], "total": l["total"]})
    return filas


# --------------------------------------------------------- estado y archivo
def cargar_ventas(tasa_impuesto):
    """Lee ventas.csv, lo limpia y deja las ventas en memoria."""
    filas = persistencia.cargar_ventas()
    lineas, reporte = limpiar_ventas(filas, tasa_impuesto)
    reporte["advertencias"] = []
    if reporte["corregidos"] or reporte["descartados"]:
        copia = persistencia.respaldar(persistencia.ruta_ventas())
        if copia:
            reporte["advertencias"].append(f"Se guardó una copia del archivo original como {os.path.basename(copia)} (en la carpeta de datos).")
    _ventas.clear()
    _ventas.extend(construir_ventas(lineas))
    _reporte_calidad.clear()
    _reporte_calidad.update(reporte)
    return copy.deepcopy(reporte)


def guardar_ventas():
    persistencia.guardar_ventas(aplanar_ventas(_ventas))


def obtener_reporte_calidad():
    return copy.deepcopy(_reporte_calidad)


def siguiente_numero_factura():
    """Próximo número con formato F-0001.

    Se calcula a partir del mayor número existente (la versión de la Etapa 2
    usaba la cantidad de ventas + 1, que se repetiría al haber datos guardados).
    """
    mayor = 0
    for v in _ventas:
        partes = v["numero_factura"].split("-")
        if len(partes) == 2 and partes[0].upper() == "F" and partes[1].isdigit():
            mayor = max(mayor, int(partes[1]))
    return f"F-{mayor + 1:04d}"


def registrar_venta(venta):
    _ventas.append(copy.deepcopy(venta))


def quitar_ultima_venta():
    """Revierte la última venta (si no se pudo guardar en el archivo)."""
    if _ventas:
        _ventas.pop()


def obtener_ventas():
    return copy.deepcopy(_ventas)


def ventas_del_dia(fecha_iso):
    """Ventas cuya fecha (sin la hora) coincide con fecha_iso (AAAA-MM-DD)."""
    return [v for v in obtener_ventas() if v["fecha"][:10] == fecha_iso]


def reiniciar():
    _ventas.clear()
    _reporte_calidad.clear()


# ----------------------------------------------------------------- análisis
def ventas_por_categoria(ventas, catalogo):
    """Suma el total de las líneas válidas por categoría de producto."""
    categoria_de = {p["codigo"]: p["categoria"] for p in catalogo}
    totales = {}
    for v in ventas:
        for l in v["productos_vendidos"]:
            if not l["valida"]:
                continue
            cat = categoria_de.get(l["codigo"], "Producto desconocido")
            totales[cat] = round(totales.get(cat, 0) + l["total"], 2)
    return dict(sorted(totales.items(), key=lambda par: par[1], reverse=True))


def ventas_por_hora(ventas):
    """Cuenta las líneas válidas por hora del día (0-23)."""
    conteo = {h: 0 for h in range(24)}
    for v in ventas:
        f = parsear_fecha(v["fecha"]) if v["fecha"] and len(v["fecha"]) > 10 else None
        if f is None:
            continue
        conteo[f.hour] += sum(1 for l in v["productos_vendidos"] if l["valida"])
    return conteo
