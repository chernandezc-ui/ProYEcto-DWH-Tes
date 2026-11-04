"""
api/rutas_catalogos.py
======================
Router /api/v1/catalogos — Catálogos MDM y Silver de solo lectura.

Seguridad: viewer+ en todos los endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from nucleo.auth import require_rol
from schemas.catalogos.peticion import PeticionCrearDimVariedad
from schemas.catalogos.respuesta import (
    RespuestaDimVariedad,
    RespuestaGeografia,
    RespuestaOperacionVariedad,
    RespuestaPaginadaCatalogo,
    RespuestaPersonal,
    RespuestaVariedad,
)
from servicios.servicio_catalogos import (
    cambiar_estado_dim_variedad,
    crear_dim_variedad,
    listar_dim_variedades,
    listar_geografia,
    listar_personal,
    listar_variedades,
)

enrutador_catalogos = APIRouter(prefix="/v1/catalogos", tags=["Catálogos"])


def _construir_respuesta_paginada(resultado: dict, schema_fila) -> RespuestaPaginadaCatalogo:
    return RespuestaPaginadaCatalogo(
        total=resultado["total"],
        pagina=resultado["pagina"],
        tamano=resultado["tamano"],
        datos=[schema_fila(**fila) for fila in resultado["datos"]],
    )


@enrutador_catalogos.get(
    "/variedades",
    summary="Catálogo MDM de variedades (MDM.Catalogo_Variedades)",
    dependencies=[Depends(require_rol("viewer"))],
)
async def obtener_variedades(
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=10000),
) -> RespuestaPaginadaCatalogo:
    resultado = await listar_variedades(pagina=pagina, tamano=tamano)
    return _construir_respuesta_paginada(resultado, RespuestaVariedad)


@enrutador_catalogos.get(
    "/variedades/dim",
    summary="Dimensión DWH de variedades (Silver.Dim_Variedad)",
    description="Retorna todas las variedades ya homologadas en la dimensión Silver del DWH.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def obtener_dim_variedades(
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=10000),
) -> RespuestaPaginadaCatalogo:
    resultado = await listar_dim_variedades(pagina=pagina, tamano=tamano)
    return _construir_respuesta_paginada(resultado, RespuestaDimVariedad)


@enrutador_catalogos.post(
    "/variedades/dim",
    summary="Crear variedad en Silver.Dim_Variedad (solo admin)",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_rol("admin"))],
)
async def crear_variedad_dim(
    peticion: PeticionCrearDimVariedad,
) -> RespuestaOperacionVariedad:
    """Crea una nueva variedad activa en Silver.Dim_Variedad."""
    try:
        dato = await crear_dim_variedad(
            nombre_variedad=peticion.nombre_variedad,
            breeder=peticion.breeder,
        )
        return RespuestaOperacionVariedad(
            ok=True,
            mensaje=f"Variedad '{peticion.nombre_variedad}' creada con ID {dato['ID_Variedad']}.",
            dato=dato,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@enrutador_catalogos.patch(
    "/variedades/dim/{id_variedad}/desactivar",
    summary="Desactivar variedad (soft-delete) — solo admin",
    dependencies=[Depends(require_rol("admin"))],
)
async def desactivar_variedad_dim(id_variedad: int) -> RespuestaOperacionVariedad:
    """Marca Es_Activa=0 en Silver.Dim_Variedad. El registro se conserva para trazabilidad."""
    try:
        dato = await cambiar_estado_dim_variedad(id_variedad=id_variedad, es_activa=False)
        return RespuestaOperacionVariedad(
            ok=True,
            mensaje=f"Variedad ID {id_variedad} desactivada correctamente.",
            dato=dato,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@enrutador_catalogos.patch(
    "/variedades/dim/{id_variedad}/reactivar",
    summary="Reactivar variedad — solo admin",
    dependencies=[Depends(require_rol("admin"))],
)
async def reactivar_variedad_dim(id_variedad: int) -> RespuestaOperacionVariedad:
    """Restaura Es_Activa=1 en Silver.Dim_Variedad."""
    try:
        dato = await cambiar_estado_dim_variedad(id_variedad=id_variedad, es_activa=True)
        return RespuestaOperacionVariedad(
            ok=True,
            mensaje=f"Variedad ID {id_variedad} reactivada correctamente.",
            dato=dato,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@enrutador_catalogos.get(
    "/geografia",
    summary="Lista la geografía vigente (filtros server-side)",
    dependencies=[Depends(require_rol("viewer"))],
)
async def obtener_geografia(
    pagina: int = Query(default=1, ge=1),
    # Tope reducido a 200 — antes 10000 generaba payloads de ~36k filas
    # innecesariamente. Filtros server-side hacen viable la página de 50.
    tamano: int = Query(default=50, ge=1, le=200),
    texto: str | None = Query(
        default=None,
        min_length=1,
        max_length=80,
        description="Substring sobre fundo, sector, válvula, código SAP, cama (accent-insensitive).",
    ),
    fundo: str | None = Query(default=None, max_length=80),
    sector: str | None = Query(default=None, max_length=80),
) -> RespuestaPaginadaCatalogo:
    resultado = await listar_geografia(
        pagina=pagina,
        tamano=tamano,
        texto=texto,
        fundo=fundo,
        sector=sector,
    )
    return _construir_respuesta_paginada(resultado, RespuestaGeografia)


@enrutador_catalogos.get(
    "/personal",
    summary="Lista el catálogo de personal",
    dependencies=[Depends(require_rol("viewer"))],
)
async def obtener_personal(
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=10000),
) -> RespuestaPaginadaCatalogo:
    resultado = await listar_personal(pagina=pagina, tamano=tamano)
    return _construir_respuesta_paginada(resultado, RespuestaPersonal)
