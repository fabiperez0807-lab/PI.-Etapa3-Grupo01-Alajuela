"""Vista: gráficos con matplotlib.

Recibe datos ya calculados; no lee archivos ni modifica información.
Cada función guarda un .png (si se indica una ruta) y/o lo muestra en pantalla.
"""
import os
import matplotlib.pyplot as plt

AZUL, NARANJA, VERDE, ROJO, GRIS = "#2E75B6", "#ED7D31", "#70AD47", "#C0392B", "#7F7F7F"
PALETA = ["#2E75B6", "#ED7D31", "#70AD47", "#FFC000", "#7B5EA7", "#C0392B", "#17A2B8", "#7F7F7F"]


def _colones(valor, _pos=None):
    return f"₡{valor:,.0f}"


def _finalizar(fig, ruta, mostrar):
    fig.tight_layout()
    if ruta:
        os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
        fig.savefig(ruta, dpi=150)
    if mostrar:
        plt.show()
    plt.close(fig)
    return ruta


def grafico_ventas_por_categoria(totales, ruta=None, mostrar=False):
    """Barras: ventas totales (con IVA) por categoría."""
    if not totales:
        return None
    fig, ax = plt.subplots(figsize=(9, 5.5))
    categorias, valores = list(totales.keys()), list(totales.values())
    barras = ax.bar(categorias, valores, color=PALETA[:len(categorias)],
                    label="Ventas totales")
    for barra, valor in zip(barras, valores):
        ax.annotate(_colones(valor), (barra.get_x() + barra.get_width() / 2, valor),
                    ha="center", va="bottom", fontsize=9, xytext=(0, 3),
                    textcoords="offset points")
    ax.set_title("Ventas totales por categoría de producto", fontweight="bold")
    ax.set_xlabel("Categoría")
    ax.set_ylabel("Total de ventas (₡, IVA incluido)")
    ax.yaxis.set_major_formatter(_colones)
    ax.set_ylim(0, max(valores) * 1.12)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return _finalizar(fig, ruta, mostrar)


def grafico_stock_critico(criticos, ruta=None, mostrar=False):
    """Barras horizontales: stock actual vs. stock mínimo.

    criticos: lista de tuplas (nombre, stock, stock_minimo).
    """
    if not criticos:
        return None
    nombres = [c[0] for c in criticos]
    stock = [c[1] for c in criticos]
    minimo = [c[2] for c in criticos]
    posiciones = range(len(criticos))
    alto = 0.38
    fig, ax = plt.subplots(figsize=(9, max(4, 0.7 * len(criticos) + 2)))
    ax.barh([p + alto / 2 for p in posiciones], stock, alto, color=ROJO, label="Stock actual")
    ax.barh([p - alto / 2 for p in posiciones], minimo, alto, color=AZUL, label="Stock mínimo")
    for p, valor in zip(posiciones, stock):
        ax.text(valor + 0.2, p + alto / 2, str(valor), va="center", fontsize=9)
    for p, valor in zip(posiciones, minimo):
        ax.text(valor + 0.2, p - alto / 2, str(valor), va="center", fontsize=9)
    ax.set_yticks(list(posiciones))
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_title("Productos con existencias críticas: stock actual vs. stock mínimo",
                 fontweight="bold")
    ax.set_xlabel("Unidades")
    ax.set_ylabel("Producto")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right")
    return _finalizar(fig, ruta, mostrar)


def grafico_pastel_categorias(totales, ruta=None, mostrar=False):
    """Circular: distribución porcentual de las ventas por categoría."""
    if not totales:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.pie(list(totales.values()), labels=None, colors=PALETA[:len(totales)],
           autopct="%1.1f%%", startangle=90, pctdistance=0.78,
           wedgeprops={"edgecolor": "white"})
    ax.legend(list(totales.keys()), title="Categoría", loc="center left",
              bbox_to_anchor=(1, 0.5))
    ax.set_title("Distribución porcentual de las ventas por categoría", fontweight="bold")
    return _finalizar(fig, ruta, mostrar)


def grafico_ventas_por_hora(conteo, ruta=None, mostrar=False):
    """Histograma de frecuencia: líneas de venta por hora del día."""
    horas = [h for h in conteo if conteo[h] > 0]
    if not horas:
        return None
    rango = list(range(min(horas), max(horas) + 1))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(rango, [conteo[h] for h in rango], color=VERDE, label="Líneas de venta")
    ax.set_title("Frecuencia de ventas por hora del día", fontweight="bold")
    ax.set_xlabel("Hora del día (24 h)")
    ax.set_ylabel("Cantidad de líneas de venta")
    ax.set_xticks(rango)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    return _finalizar(fig, ruta, mostrar)
