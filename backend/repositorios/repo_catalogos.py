"""
repositorios/repo_catalogos.py
================================
Todas las consultas SQL relacionadas con catálogos MDM y dimensiones Silver.
Todos los métodos son de sólo lectura.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

_CATALOGOS = {
    "variedades": {
        "sql_datos": """
            SELECT
                Nombre_Canonico AS nombre_canonico,
                Breeder         AS breeder,
                Es_Activa       AS es_activa,
                COUNT(*) OVER() AS total_rows
            FROM MDM.Catalogo_Variedades WITH (NOLOCK)
            ORDER BY Es_Activa DESC, Nombre_Canonico
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar variedades MDM",
    },
    "dim_variedades": {
        "sql_datos": """
            SELECT
                ID_Variedad        AS id_variedad,
                Nombre_Variedad    AS nombre_variedad,
                Breeder            AS breeder,
                Es_Activa          AS es_activa,
                Fecha_Creacion     AS fecha_creacion,
                Fecha_Modificacion AS fecha_modificacion,
                COUNT(*) OVER()    AS total_rows
            FROM Silver.Dim_Variedad WITH (NOLOCK)
            ORDER BY Es_Activa DESC, Nombre_Variedad
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar Dim_Variedad Silver",
    },
    # Nota: la entrada "geografia" del dict fue migrada a la función
    # `listar_geografia` aparte porque acepta filtros server-side
    # (texto, fundo, sector) y un WHERE dinámico. Las otras 3 tablas
    # siguen aquí porque su volumen (<300 filas) no justifica filtros.
    "personal": {
        "sql_datos": """
            SELECT
                DNI                 AS dni,
                Nombre_Completo     AS nombre_completo,
                Rol                 AS rol,
                Sexo                AS sexo,
                ID_Planilla         AS id_planilla,
                Pct_Asertividad     AS pct_asertividad,
                Dias_Ausentismo     AS dias_ausentismo,
                COUNT(*) OVER()     AS total_rows
            FROM Silver.Dim_Personal WITH (NOLOCK)
            ORDER BY Nombre_Completo
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar personal",
    },
}


_TTL_CATALOGOS = 3600   # 1 hora — datos estáticos
_TTL_CUARENTENA = 120   # 2 minutos — datos operativos


def _paginar(
    con,
    sql_datos: str,
    params: dict,
    pagina: int,
    tamano: int,
) -> dict:
    """
    Helper interno: ejecuta query paginada y retorna el envelope estándar.
    Extrae el total del campo 'total_rows' inyectado vía COUNT(*) OVER().
    """
    filas = con.execute(text(sql_datos), params).fetchall()
    
    total = 0
    datos = []
    if filas:
        total = filas[0]._mapping["total_rows"]
        # Convertimos a dict y removemos la columna técnica total_rows
        for fila in filas:
            d = dict(fila._mapping)
            d.pop("total_rows", None)
            datos.append(d)

    return {
        "total":  total,
        "pagina": pagina,
        "tamano": tamano,
        "datos":  datos,
    }


def _listar_catalogo(nombre_catalogo: str, pagina: int = 1, tamano: int = 20) -> dict:
    configuracion = _CATALOGOS[nombre_catalogo]
    desplazamiento = (pagina - 1) * tamano
    params = {"offset": desplazamiento, "tamano": tamano}
    try:
        with obtener_engine().connect() as con:
            return _paginar(
                con,
                sql_datos=configuracion["sql_datos"],
                params=params,
                pagina=pagina,
                tamano=tamano,
            )
    except SQLAlchemyError:
        log.exception(configuracion["mensaje_error"])
        raise ErrorBaseDatos()


def listar_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee MDM.Catalogo_Variedades (catálogo maestro MDM)."""
    return _listar_catalogo("variedades", pagina=pagina, tamano=tamano)


def listar_dim_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Variedad (dimensión DWH ya homologada)."""
    return _listar_catalogo("dim_variedades", pagina=pagina, tamano=tamano)


# ── Escritura sobre Silver.Dim_Variedad (solo admin) ───────────────────────────────

def insertar_dim_variedad(nombre_variedad: str, breeder: str | None) -> dict:
    """
    Inserta una nueva variedad en Silver.Dim_Variedad.
    Retorna el registro creado: {id_variedad, nombre_variedad, breeder}.
    Lanza ErrorBaseDatos si ya existe (UNIQUE constraint en Nombre_Variedad).
    """
    try:
        with obtener_engine().begin() as con:
            fila = con.execute(
                text("""
                    INSERT INTO Silver.Dim_Variedad
                        (Nombre_Variedad, Breeder, Es_Activa, Fecha_Creacion)
                    OUTPUT
                        INSERTED.ID_Variedad,
                        INSERTED.Nombre_Variedad,
                        INSERTED.Breeder,
                        INSERTED.Es_Activa,
                        INSERTED.Fecha_Creacion
                    VALUES (:nombre, :breeder, 1, GETDATE())
                """),
                {"nombre": nombre_variedad, "breeder": breeder},
            ).fetchone()
        return dict(fila._mapping)
    except SQLAlchemyError as exc:
        msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        if "UQ_DimVariedad_Nombre" in msg or "UNIQUE" in msg.upper():
            raise ValueError(f"Ya existe una variedad con el nombre '{nombre_variedad}'.")
        log.exception("Error al insertar dim variedad", extra={"nombre": nombre_variedad})
        raise ErrorBaseDatos()


def cambiar_estado_dim_variedad(id_variedad: int, es_activa: bool) -> dict:
    """
    Activa o desactiva una variedad (soft-delete) en Silver.Dim_Variedad.
    Retorna el registro actualizado.
    Lanza ValueError si el ID no existe.
    """
    try:
        with obtener_engine().begin() as con:
            fila = con.execute(
                text("""
                    UPDATE Silver.Dim_Variedad
                    SET Es_Activa          = :activa,
                        Fecha_Modificacion = GETDATE()
                    OUTPUT
                        INSERTED.ID_Variedad,
                        INSERTED.Nombre_Variedad,
                        INSERTED.Breeder,
                        INSERTED.Es_Activa,
                        INSERTED.Fecha_Modificacion
                    WHERE ID_Variedad = :id
                """),
                {"id": id_variedad, "activa": 1 if es_activa else 0},
            ).fetchone()
        if fila is None:
            raise ValueError(f"No existe variedad con ID {id_variedad}.")
        return dict(fila._mapping)
    except ValueError:
        raise
    except SQLAlchemyError:
        log.exception("Error al cambiar estado dim variedad", extra={"id": id_variedad})
        raise ErrorBaseDatos()


def listar_geografia(
    pagina: int = 1,
    tamano: int = 50,
    texto: str | None = None,
    fundo: str | None = None,
    sector: str | None = None,
) -> dict:
    """
    Lee Silver.Dim_Geografia vigente con paginación y filtros server-side.

    Filtros opcionales:
        - texto: substring sobre fundo, sector, válvula, código SAP, cama.
          Usa `COLLATE Modern_Spanish_CI_AI` para que "garcia" matchee
          "García" (la collation default de las columnas es _CI_AS,
          accent-sensitive).
        - fundo: match exacto sobre fn.Fundo.
        - sector: match exacto sobre sc.Sector.

    Tabla con ~36k filas vigentes — la única catalogo del MDM que
    justifica filtros server-side. Las otras (variedades, personal)
    son <300 filas y se filtran client-side.
    """
    desplazamiento = (pagina - 1) * tamano
    # Normalizar strings vacíos a None para que la cláusula `:texto IS NULL`
    # del WHERE simétricamente desactive el filtro.
    texto_norm = texto.strip() if texto and texto.strip() else None
    fundo_norm = fundo.strip() if fundo and fundo.strip() else None
    sector_norm = sector.strip() if sector and sector.strip() else None

    sql = """
        SELECT
            fn.Fundo            AS fundo,
            sc.Sector           AS sector,
            md.Modulo           AS modulo,
            tr.Turno            AS turno,
            vl.Valvula          AS valvula,
            cm.Cama_Normalizada AS cama,
            g.Es_Test_Block     AS es_test_block,
            g.Codigo_SAP_Campo  AS codigo_sap_campo,
            g.Es_Vigente        AS es_vigente,
            COUNT(*) OVER()     AS total_rows
        FROM Silver.Dim_Geografia g WITH (NOLOCK)
        JOIN Silver.Dim_Fundo_Catalogo fn WITH (NOLOCK) ON g.ID_Fundo_Catalogo = fn.ID_Fundo_Catalogo
        JOIN Silver.Dim_Sector_Catalogo sc WITH (NOLOCK) ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
        JOIN Silver.Dim_Modulo_Catalogo md WITH (NOLOCK) ON g.ID_Modulo_Catalogo = md.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo tr WITH (NOLOCK) ON g.ID_Turno_Catalogo = tr.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo vl WITH (NOLOCK) ON g.ID_Valvula_Catalogo = vl.ID_Valvula_Catalogo
        JOIN Silver.Dim_Cama_Catalogo cm WITH (NOLOCK) ON g.ID_Cama_Catalogo = cm.ID_Cama_Catalogo
        WHERE g.Es_Vigente = 1
          AND (:texto IS NULL OR (
                fn.Fundo            COLLATE Modern_Spanish_CI_AI LIKE '%' + :texto + '%'
             OR sc.Sector           COLLATE Modern_Spanish_CI_AI LIKE '%' + :texto + '%'
             OR ISNULL(vl.Valvula, '')           COLLATE Modern_Spanish_CI_AI LIKE '%' + :texto + '%'
             OR ISNULL(g.Codigo_SAP_Campo, '')   COLLATE Modern_Spanish_CI_AI LIKE '%' + :texto + '%'
             OR ISNULL(cm.Cama_Normalizada, '')  COLLATE Modern_Spanish_CI_AI LIKE '%' + :texto + '%'
          ))
          AND (:fundo  IS NULL OR fn.Fundo  = :fundo)
          AND (:sector IS NULL OR sc.Sector = :sector)
        ORDER BY fn.Fundo, sc.Sector, md.Modulo, tr.Turno, vl.Valvula, cm.Cama_Normalizada
        OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
    """
    params = {
        "offset": desplazamiento,
        "tamano": tamano,
        "texto":  texto_norm,
        "fundo":  fundo_norm,
        "sector": sector_norm,
    }
    try:
        with obtener_engine().connect() as con:
            return _paginar(con, sql_datos=sql, params=params, pagina=pagina, tamano=tamano)
    except SQLAlchemyError:
        log.exception("Error al listar geografía", extra={
            "texto": texto_norm, "fundo": fundo_norm, "sector": sector_norm,
        })
        raise ErrorBaseDatos()


def listar_personal(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Personal con paginación server-side."""
    return _listar_catalogo("personal", pagina=pagina, tamano=tamano)
