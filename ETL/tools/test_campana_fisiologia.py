"""Carga manual de fisiología; solo se ejecuta como CLI, nunca al importar."""

import sys
from pathlib import Path


def main():
    import logging

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from silver.facts.fact_fisiologia import cargar_fact_fisiologia
    from config.conexion import obtener_engine

    logging.basicConfig(level=logging.INFO)
    resumen = cargar_fact_fisiologia(obtener_engine())
    print("\n--- RESUMEN FINAL ---")
    print(resumen)
    if resumen.get('cuarentena'):
        print("\n--- MUESTRA CUARENTENA ---")
        for item in resumen['cuarentena'][:5]:
            print(item)


if __name__ == '__main__':
    main()
