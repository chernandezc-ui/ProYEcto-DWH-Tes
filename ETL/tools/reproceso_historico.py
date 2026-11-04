"""
reproceso_historico.py
======================
Fase 4 del Plan de Estabilización.

Propósito:
    Resetear el estado de registros en Bronce para que el ETL los
    reprocese y llene los datos que estaban faltando (VPD, Radiacion,
    BrotesProd, BrotesVeg, Organo, Color).

Modo de uso:
    python reproceso_historico.py [--dry-run] [--tabla TABLA]

Tablas disponibles:
    - Fisiologia                (para que BrotesProd_Raw/BrotesVeg_Raw se llenen)
    - Peladas                   (para columnas estructuradas)

Nota: El reset SOLO aplica a registros en estado PROCESADO.
      Registros RECHAZADOS se mantienen intactos.
      El ETL los reprocesará en la próxima corrida vía runner.py.
"""
import sys
import argparse
import logging

sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("Reproceso")

# Mapa tabla_bronce -> (columna_pk, columna_estado)
TABLAS_REPROCESO = {
    "Fisiologia": {
        "tabla_bronce": "Bronce.Fisiologia",
        "pk": "ID_Fisiologia",
        "justificacion": "Fix: BrotesProd_Raw y BrotesVeg_Raw ahora se mapean desde el Excel"
    },
    "Peladas": {
        "tabla_bronce": "Bronce.Peladas",
        "pk": "ID_Peladas",
        "justificacion": "Fix: Columnas de conteo estructuradas ahora se persisten correctamente"
    },
}


def contar_registros(conn, tabla: str) -> int:
    resultado = conn.execute(text(
        f"SELECT COUNT(*) FROM {tabla} WHERE Estado_Carga = 'PROCESADO'"
    ))
    return resultado.scalar()


def resetear_tabla(conn, config: dict, dry_run: bool) -> int:
    tabla = config["tabla_bronce"]
    count = contar_registros(conn, tabla)
    if count == 0:
        log.info(f"[SKIP] {tabla}: sin registros PROCESADO para resetear.")
        return 0

    log.info(f"[INFO] {tabla}: {count} registros PROCESADO encontrados.")
    if dry_run:
        log.info(f"[DRY-RUN] {tabla}: NO se ejecutó el reset.")
        return count

    conn.execute(text(
        f"UPDATE {tabla} SET Estado_Carga = 'CARGADO' WHERE Estado_Carga = 'PROCESADO'"
    ))
    log.info(f"[OK] {tabla}: {count} registros reseteados a CARGADO.")
    return count


def main():
    parser = argparse.ArgumentParser(description="Reproceso histórico ETL - Fase 35")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo muestra qué se haría, sin ejecutar cambios.")
    parser.add_argument("--tabla", type=str, default=None,
                        help=f"Tabla específica a resetear. Opciones: {', '.join(TABLAS_REPROCESO.keys())}")
    args = parser.parse_args()

    engine = obtener_engine()
    tablas = TABLAS_REPROCESO
    if args.tabla:
        if args.tabla not in TABLAS_REPROCESO:
            log.error(f"Tabla desconocida: {args.tabla}. Opciones: {list(TABLAS_REPROCESO.keys())}")
            sys.exit(1)
        tablas = {args.tabla: TABLAS_REPROCESO[args.tabla]}

    total_reseteados = 0
    with engine.begin() as conn:
        for nombre, config in tablas.items():
            log.info(f"\n--- {nombre} ---")
            log.info(f"Justificacion: {config['justificacion']}")
            reseteados = resetear_tabla(conn, config, args.dry_run)
            total_reseteados += reseteados

    modo = "DRY-RUN" if args.dry_run else "EJECUTADO"
    log.info(f"\n=== Reproceso [{modo}] completado: {total_reseteados} registros total ===")
    if not args.dry_run:
        log.info("Proximos pasos: Iniciar el runner.py o lanzar una corrida ETL manual.")


if __name__ == "__main__":
    main()
