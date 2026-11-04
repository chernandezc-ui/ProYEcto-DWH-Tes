"""
api/rutas_ingesta.py
========================
Router /api/v1/ingesta — Carga y Validación de CSV con Polars
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import io
import re
from typing import Annotated
from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from nucleo.conexion import obtener_engine
from nucleo.etl_catalogo import es_tabla_consultable
from servicios.servicio_ingesta import validar_csv_polars

enrutador_ingesta = APIRouter(prefix="/v1/ingesta", tags=["Ingesta"])

@enrutador_ingesta.post(
    "/validar",
    summary="Valida un archivo CSV contra las reglas de la tabla destino",
    description="Lee el CSV en memoria con Polars y devuelve un diagnóstico (filas válidas vs errores). No inserta en Base de Datos.",
    dependencies=[Depends(require_rol("analista_mdm"))], # Asumiendo que se necesita este rol
)
async def validar_archivo(
    archivo: UploadFile = File(...),
    tabla_destino: str = Form(...),
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)] = None,
):
    if not archivo.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .csv")
        
    resultado = await validar_csv_polars(archivo, tabla_destino)
    
    if not resultado.get("valido"):
        raise HTTPException(status_code=400, detail=resultado.get("error_general", "Error al procesar el archivo"))
        
    return resultado

@enrutador_ingesta.get(
    "/descargar/{tabla}",
    summary="Descargar los datos actuales de una tabla en formato CSV",
    description="Obtiene todos los registros de la tabla especificada y los retorna como un archivo CSV para facilitar ajustes manuales.",
    dependencies=[Depends(require_rol("analista_mdm"))], 
)
async def descargar_tabla(
    tabla: str,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)] = None,
):
    # Sanitizar el nombre de la tabla para evitar SQL Injection (ej. Schema.Tabla)
    if not re.match(r"^[a-zA-Z0-9_.]+$", tabla):
        raise HTTPException(status_code=400, detail="Nombre de tabla inválido")

    # Whitelist desde el catálogo ETL: impide exportar esquemas sensibles
    # (Seguridad.Usuarios, Auditoria, Control…) vía este endpoint (V-03 / IDOR).
    if not es_tabla_consultable(tabla):
        raise HTTPException(status_code=403, detail="La tabla no está disponible para exportación.")

    engine = obtener_engine()
    try:
        import polars as pl
        query = f"SELECT * FROM {tabla}"
        df = pl.read_database(query=query, connection=engine)
        
        # Convertir el DataFrame a un CSV en memoria
        stream = io.BytesIO()
        df.write_csv(stream)
        stream.seek(0)
        
        return StreamingResponse(
            stream,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={tabla}_export.csv",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        # Detalle solo a logs, no al cliente (V-07).
        import logging
        logging.getLogger("ACP_Backend").error(f"Error al exportar tabla {tabla}: {e}")
        raise HTTPException(status_code=500, detail="Error al exportar la tabla.")
