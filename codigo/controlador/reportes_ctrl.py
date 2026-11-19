"""Controlador: alertas, calidad de datos y reportes gráficos."""
import os

from modelo import producto, venta, alerta
from modelo.fecha import obtener_fecha
from vista import consola, graficos
from controlador import entradas as ent
from controlador import reglas

CARPETA_GRAFICOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reportes_graficos")


def calcular_alertas():
    """Recalcula las alertas del inventario y las deja en el modelo."""
    hoy = obtener_fecha()
    alerta.limpiar_alertas()
    for p in producto.obtener_catalogo():
        if reglas.es_stock_bajo(p):
            sugerido = reglas.calcular_stock_sugerido(p)
            alerta.agregar_alerta(p["codigo"], "stock_bajo",
                                  f"{p['nombre']}: stock {p['stock']} (mín. {p['stock_minimo']}). Reponer ~{sugerido}.")
        dias = reglas.dias_para_vencer(p, hoy)
        if dias is not None and dias <= reglas.DIAS_ALERTA_VENCIMIENTO:
            texto = f"venció hace {-dias} día(s)" if dias < 0 else f"vence en {dias} día(s)"
            alerta.agregar_alerta(p["codigo"], "vencimiento_proximo", f"{p['nombre']}: {texto}.")
        if p["marcas"]:
            alerta.agregar_alerta(p["codigo"], "dato_atipico", f"{p['nombre']}: {', '.join(p['marcas'])}.")
    return alerta.obtener_alertas()


def generar_alertas():
    consola.mostrar_alertas(calcular_alertas(), obtener_fecha().isoformat())


def consultar_calidad_datos():
    consola.mostrar_calidad(producto.obtener_reporte_calidad(), venta.obtener_reporte_calidad())


def productos_criticos():
    """Productos agotados o bajo el mínimo, del más crítico al menos crítico."""
    criticos = [p for p in producto.obtener_catalogo() if reglas.es_stock_bajo(p)]
    return sorted(criticos, key=lambda p: p["stock"] - p["stock_minimo"])


def generar_graficos(carpeta, mostrar=False):
    """Genera los gráficos y devuelve las rutas de los .png creados."""
    ventas = venta.obtener_ventas()
    por_categoria = venta.ventas_por_categoria(ventas, producto.obtener_catalogo())
    criticos = [(p["nombre"], p["stock"], p["stock_minimo"]) for p in productos_criticos()]
    generados = [
        graficos.grafico_ventas_por_categoria(por_categoria, os.path.join(carpeta, "ventas_por_categoria.png"), mostrar),
        graficos.grafico_stock_critico(criticos, os.path.join(carpeta, "stock_critico.png"), mostrar),
        graficos.grafico_pastel_categorias(por_categoria, os.path.join(carpeta, "distribucion_categorias.png"), mostrar),
        graficos.grafico_ventas_por_hora(venta.ventas_por_hora(ventas), os.path.join(carpeta, "ventas_por_hora.png"), mostrar),
    ]
    return [g for g in generados if g]


def generar_reportes_graficos():
    consola.mostrar_titulo("REPORTES GRÁFICOS")
    mostrar = ent.solicitar_confirmacion("¿Mostrar los gráficos en pantalla? (s/n): ")
    consola.mostrar_rutas_graficos(generar_graficos(CARPETA_GRAFICOS, mostrar))
