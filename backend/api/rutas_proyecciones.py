from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from dominio.proyecciones import ErrorValidacionProyeccion
from nucleo.auth import require_rol
from schemas.proyecciones.peticion import PeticionEjecutarProyeccion
from schemas.proyecciones.respuesta import RespuestaProyeccion
import servicios.servicio_proyecciones as servicio

enrutador_proyecciones = APIRouter(prefix="/v1/proyecciones", tags=["Proyecciones"])

@enrutador_proyecciones.get("/fechas", dependencies=[Depends(require_rol("viewer"))])
async def fechas_disponibles():
    fechas = await servicio.obtener_fechas_disponibles()
    return {"fechas": fechas}

@enrutador_proyecciones.get("/combinaciones/{id_tiempo}", dependencies=[Depends(require_rol("viewer"))])
async def combinaciones_disponibles(id_tiempo: int):
    import asyncio
    import repositorios.repo_proyecciones as repo
    df = await asyncio.to_thread(repo.obtener_combinaciones_disponibles, id_tiempo)
    return df.to_dict(orient="records") if not df.empty else []

@enrutador_proyecciones.get("/integridad/{id_tiempo}", dependencies=[Depends(require_rol("viewer"))])
async def integridad_datos(id_tiempo: int, modulo: Optional[int] = None, variedad: Optional[str] = None, condicion: Optional[str] = None):
    import asyncio
    import repositorios.repo_proyecciones as repo
    res = await asyncio.to_thread(repo.verificar_integridad_datos, id_tiempo, modulo, variedad, condicion)
    return res

@enrutador_proyecciones.get("/matriz", dependencies=[Depends(require_rol("viewer"))])
async def cargar_matriz():
    return await servicio.obtener_matriz_proyeccion()

@enrutador_proyecciones.post("/matriz", dependencies=[Depends(require_rol("analista_mdm"))])
async def guardar_matriz(matriz: Dict[str, Dict[str, Any]]):
    try:
        return await servicio.guardar_matriz_proyeccion(matriz)
    except ErrorValidacionProyeccion as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@enrutador_proyecciones.post("/ejecutar", response_model=RespuestaProyeccion, dependencies=[Depends(require_rol("analista_mdm"))])
async def ejecutar(peticion: PeticionEjecutarProyeccion):
    try:
        resultado = await servicio.ejecutar_proyeccion(
            id_tiempo=peticion.id_tiempo,
            matriz_inputs=peticion.matriz_inputs,
            margen_pesimista=peticion.margen_pesimista,
            margen_optimista=peticion.margen_optimista,
            modulo=peticion.modulo,
            variedad=peticion.variedad,
            condicion=peticion.condicion,
            fundo=peticion.fundo
        )
        
        df_semanal = resultado["df_semanal"]
        filas = []
        if not df_semanal.empty:
            for _, r in df_semanal.iterrows():
                filas.append({
                    "semana": int(r["semana"]),
                    "semana_label": str(r["semana_label"]),
                    "fecha_semana": str(r["fecha_semana"]),
                    "kg_proyectados": float(r["kg_base"]),
                    "kg_pesimista": float(r["kg_pesimista"]),
                    "kg_optimista": float(r["kg_optimista"]),
                    "kg_anterior": 0.0,
                    "pct_variacion": 0.0,
                    "tendencia": "Estable"
                })
        
        df_detalle_dict = resultado["df_detalle"].to_dict(orient="records") if not resultado["df_detalle"].empty else []
        
        return RespuestaProyeccion(
            df_semanal=filas,
            kpis=resultado["kpis"],
            df_detalle=df_detalle_dict
        )
    except ErrorValidacionProyeccion as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
