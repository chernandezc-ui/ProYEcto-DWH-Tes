"""
sembrar_reglas.py
=================
Carga en Config.Parametros_Pipeline las reglas de negocio configurables que
falten, a partir de config/reglas_semilla.json.

  - Un parametro solo se inserta si no existe.
  - Nunca modifica ni borra nada existente (respeta lo editado en la base).

Uso (desde ETL/):
    py tools/sembrar_reglas.py
    py tools/sembrar_reglas.py --verificar     # solo comprueba, no escribe
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.conexion import obtener_engine
from config import reglas


def main() -> int:
    parser = argparse.ArgumentParser(description='Siembra las reglas de negocio configurables.')
    parser.add_argument('--verificar', action='store_true', help='Solo verificar completitud.')
    args = parser.parse_args()

    engine = obtener_engine()
    try:
        if not args.verificar:
            insertados = reglas.sembrar(engine)
            print(f"Sembrado: {insertados} parametros nuevos en Config.Parametros_Pipeline.")
        reglas.verificar_completitud(engine)
        print("Reglas completas y coherentes.")
        return 0
    except reglas.ErrorConfiguracion as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
