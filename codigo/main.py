"""Punto de entrada: menú principal y bucle de ejecución.

Uso:  python main.py [AAAA-MM-DD] [--datos CARPETA]
  AAAA-MM-DD   fecha simulada del sistema (por defecto, la fecha de hoy).
  --datos      carpeta con inventario.csv y ventas.csv (por defecto, datos/).
"""
import sys

from controlador import menu_ctrl


def leer_argumentos(argumentos):
    ruta, restantes = None, list(argumentos)
    if "--datos" in restantes:
        i = restantes.index("--datos")
        ruta = restantes[i + 1] if i + 1 < len(restantes) else None
        del restantes[i:i + 2]
    return (restantes[0] if restantes else None), ruta


def main():
    fecha_texto, ruta = leer_argumentos(sys.argv[1:])
    if menu_ctrl.iniciar(fecha_texto, ruta):
        menu_ctrl.ejecutar()


if __name__ == "__main__":
    main()
