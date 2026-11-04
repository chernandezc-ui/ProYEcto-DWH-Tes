"""
dim_geografia.py
================
Sincroniza Silver.Dim_Geografia desde MDM.Catalogo_Geografia.

Incluye normalizacion de Modulo_Raw usando MDM.Regla_Modulo_Raw:
  - 9.1 -> Modulo 9, SubModulo 1, Tipo_Conduccion SUELO
  - 9.2 -> Modulo 9, SubModulo 2, Tipo_Conduccion MACETA
  - VI  -> Test Block
"""

from __future__ import annotations

from datetime import date
import re
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.texto import limpiar_numerico_texto, titulo, normalizar_espacio


def _tabla_existe(engine: Engine, esquema: str, tabla: str) -> bool:
    with engine.connect() as conexion:
        valor = conexion.execute(
            text(
                """
                SELECT CASE WHEN OBJECT_ID(:objeto, 'U') IS NULL THEN 0 ELSE 1 END
                """
            ),
            {"objeto": f"{esquema}.{tabla}"},
        ).scalar_one()
    return bool(valor)


def _columna_existe(engine: Engine, esquema: str, tabla: str, columna: str) -> bool:
    with engine.connect() as conexion:
        valor = conexion.execute(
            text(
                """
                SELECT CASE
                    WHEN COL_LENGTH(:objeto, :columna) IS NULL THEN 0
                    ELSE 1
                END
                """
            ),
            {"objeto": f"{esquema}.{tabla}", "columna": columna},
        ).scalar_one()
    return bool(valor)


def _es_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    return str(valor).strip() in ("", "None", "nan")


def _normalizar_texto(valor: Any, usar_titulo: bool = False) -> str | None:
    if _es_nulo(valor):
        return None
    texto = normalizar_espacio(str(valor))
    if texto is None:
        return None
    return titulo(texto) if usar_titulo else texto


def _normalizar_codigo(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    return limpiar_numerico_texto(_normalizar_texto(valor))


def _normalizar_entero(valor: Any) -> int | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    if texto.lower() in ("true", "verdadero", "si", "yes"):
        return 1
    if texto.lower() in ("false", "falso", "no"):
        return 0
    return int(float(texto))


def _parsear_modulo_operativo(modulo_raw: Any) -> int | None:
    token = _normalizar_texto(modulo_raw)
    if token is None:
        return None
    if re.fullmatch(r"[+-]?\d+", token):
        return int(token)
    return None


def _cargar_catalogo_geografia(engine: Engine) -> pd.DataFrame:
    existe_regla = _tabla_existe(engine, "MDM", "Regla_Modulo_Raw")
    usa_submodulo_catalogo = _columna_existe(engine, "MDM", "Catalogo_Geografia", "SubModulo")
    usa_tipo_catalogo = _columna_existe(engine, "MDM", "Catalogo_Geografia", "Tipo_Conduccion")

    expr_submodulo = "c.SubModulo" if usa_submodulo_catalogo else "CAST(NULL AS INT)"
    expr_tipo = "c.Tipo_Conduccion" if usa_tipo_catalogo else "CAST(NULL AS NVARCHAR(50))"

    if existe_regla:
        join_regla = """
            LEFT JOIN MDM.Regla_Modulo_Raw r
                ON r.Es_Activa = 1
               AND UPPER(LTRIM(RTRIM(r.Modulo_Raw))) = UPPER(LTRIM(RTRIM(CONVERT(NVARCHAR(100), c.Modulo))))
        """
        expr_modulo_regla = "r.Modulo_Int"
        expr_submodulo_regla = "r.SubModulo_Int"
        expr_tipo_regla = "r.Tipo_Conduccion"
        expr_test_regla = "ISNULL(r.Es_Test_Block, 0)"
    else:
        join_regla = ""
        expr_modulo_regla = "CAST(NULL AS INT)"
        expr_submodulo_regla = "CAST(NULL AS INT)"
        expr_tipo_regla = "CAST(NULL AS NVARCHAR(50))"
        expr_test_regla = "CAST(0 AS BIT)"

    consulta = f"""
        SELECT
            c.Fundo,
            c.Sector,
            c.Modulo AS Modulo_Raw,
            c.Turno,
            c.Valvula,
            c.Cama,
            c.Codigo_SAP_Campo,
            ISNULL(c.Es_Test_Block, 0) AS Es_Test_Block_Catalogo,
            {expr_submodulo} AS SubModulo_Catalogo,
            {expr_tipo} AS Tipo_Conduccion_Catalogo,
            {expr_modulo_regla} AS Modulo_Regla,
            {expr_submodulo_regla} AS SubModulo_Regla,
            {expr_tipo_regla} AS Tipo_Conduccion_Regla,
            {expr_test_regla} AS Es_Test_Block_Regla
        FROM MDM.Catalogo_Geografia c
        {join_regla}
        WHERE c.Es_Activa = 1
    """

    with engine.connect() as conexion:
        resultado = conexion.execute(text(consulta))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _cargar_dim_vigente(engine: Engine) -> tuple[pd.DataFrame, bool, bool]:
    usa_submodulo_dim = _columna_existe(engine, "Silver", "Dim_Geografia", "SubModulo")
    usa_tipo_dim = _columna_existe(engine, "Silver", "Dim_Geografia", "Tipo_Conduccion")

    expr_submodulo = "g.SubModulo" if usa_submodulo_dim else "CAST(NULL AS INT)"
    expr_tipo = "g.Tipo_Conduccion" if usa_tipo_dim else "CAST(NULL AS NVARCHAR(50))"

    consulta = f"""
        SELECT
            g.ID_Geografia,
            g.Fundo,
            g.Sector,
            g.Modulo,
            g.Turno,
            g.Valvula,
            g.Cama,
            g.Codigo_SAP_Campo,
            ISNULL(g.Es_Test_Block, 0) AS Es_Test_Block,
            {expr_submodulo} AS SubModulo,
            {expr_tipo} AS Tipo_Conduccion
        FROM Silver.Dim_Geografia g
        WHERE ISNULL(g.Es_Vigente, 1) = 1
    """

    with engine.connect() as conexion:
        resultado = conexion.execute(text(consulta))
        df = pd.DataFrame(resultado.fetchall(), columns=resultado.keys())
    return df, usa_submodulo_dim, usa_tipo_dim


def _normalizar_catalogo_fila(fila: pd.Series) -> dict[str, Any]:
    modulo_por_regla = _normalizar_entero(fila.get("Modulo_Regla"))
    submodulo_catalogo = _normalizar_entero(fila.get("SubModulo_Catalogo"))
    submodulo_regla = _normalizar_entero(fila.get("SubModulo_Regla"))
    es_test_catalogo = _normalizar_entero(fila.get("Es_Test_Block_Catalogo")) or 0
    es_test_regla = _normalizar_entero(fila.get("Es_Test_Block_Regla")) or 0

    modulo_int = modulo_por_regla if modulo_por_regla is not None else _parsear_modulo_operativo(fila.get("Modulo_Raw"))
    submodulo_int = submodulo_catalogo if submodulo_catalogo is not None else submodulo_regla
    tipo_conduccion = _normalizar_texto(fila.get("Tipo_Conduccion_Catalogo"))
    if tipo_conduccion is None:
        tipo_conduccion = _normalizar_texto(fila.get("Tipo_Conduccion_Regla"))

    registro = {
        "Fundo": _normalizar_texto(fila.get("Fundo"), usar_titulo=True),
        "Sector": _normalizar_texto(fila.get("Sector"), usar_titulo=True),
        "Modulo": modulo_int,
        "SubModulo": submodulo_int,
        "Turno": _normalizar_entero(fila.get("Turno")),
        "Valvula": _normalizar_codigo(fila.get("Valvula")),
        "Cama": _normalizar_codigo(fila.get("Cama")),
        "Codigo_SAP_Campo": _normalizar_texto(fila.get("Codigo_SAP_Campo")),
        "Tipo_Conduccion": _normalizar_texto(tipo_conduccion),
        "Es_Test_Block": 1 if (es_test_catalogo == 1 or es_test_regla == 1) else 0,
    }
    if registro["Es_Test_Block"] == 1 and registro["Modulo"] is None:
        # Evita descartar test block cuando el modulo raw es no numerico (ej. VI)
        registro["Modulo"] = -1
    return registro


def _normalizar_dim_fila(fila: pd.Series) -> dict[str, Any]:
    return {
        "ID_Geografia": int(fila["ID_Geografia"]),
        "Fundo": _normalizar_texto(fila.get("Fundo"), usar_titulo=True),
        "Sector": _normalizar_texto(fila.get("Sector"), usar_titulo=True),
        "Modulo": _normalizar_entero(fila.get("Modulo")),
        "SubModulo": _normalizar_entero(fila.get("SubModulo")),
        "Turno": _normalizar_entero(fila.get("Turno")),
        "Valvula": _normalizar_codigo(fila.get("Valvula")),
        "Cama": _normalizar_codigo(fila.get("Cama")),
        "Codigo_SAP_Campo": _normalizar_texto(fila.get("Codigo_SAP_Campo")),
        "Tipo_Conduccion": _normalizar_texto(fila.get("Tipo_Conduccion")),
        "Es_Test_Block": _normalizar_entero(fila.get("Es_Test_Block")) or 0,
    }


def _clave_natural(fila: dict[str, Any]) -> tuple:
    return (
        (fila.get("Fundo") or "").lower(),
        (fila.get("Sector") or "").lower(),
        fila.get("Modulo"),
        fila.get("SubModulo"),
        fila.get("Turno"),
        (fila.get("Valvula") or "").lower(),
        (fila.get("Cama") or "").lower(),
    )


def _hay_cambio(existente: dict[str, Any], actual: dict[str, Any], usa_tipo_dim: bool) -> bool:
    if (existente.get("Codigo_SAP_Campo") or None) != (actual.get("Codigo_SAP_Campo") or None):
        return True
    if int(existente.get("Es_Test_Block", 0)) != int(actual.get("Es_Test_Block", 0)):
        return True
    if usa_tipo_dim and (existente.get("Tipo_Conduccion") or None) != (actual.get("Tipo_Conduccion") or None):
        return True
    return False


def _cerrar_registro(conexion, id_geografia: int) -> None:
    conexion.execute(
        text(
            """
            UPDATE Silver.Dim_Geografia
            SET Fecha_Fin_Vigencia = :fecha_fin,
                Es_Vigente = 0
            WHERE ID_Geografia = :id_geografia
            """
        ),
        {"fecha_fin": date.today(), "id_geografia": id_geografia},
    )


def _insertar_registro(conexion, fila: dict[str, Any], usa_submodulo_dim: bool, usa_tipo_dim: bool) -> None:
    columnas = [
        "Fundo",
        "Sector",
        "Modulo",
        "Turno",
        "Valvula",
        "Cama",
        "Es_Test_Block",
        "Codigo_SAP_Campo",
    ]
    valores = [
        ":fundo",
        ":sector",
        ":modulo",
        ":turno",
        ":valvula",
        ":cama",
        ":es_test_block",
        ":codigo_sap",
    ]
    if usa_submodulo_dim:
        columnas.append("SubModulo")
        valores.append(":submodulo")
    if usa_tipo_dim:
        columnas.append("Tipo_Conduccion")
        valores.append(":tipo_conduccion")
    columnas.extend(["Fecha_Inicio_Vigencia", "Fecha_Fin_Vigencia", "Es_Vigente"])
    valores.extend([":fecha_inicio", "NULL", "1"])

    consulta = f"""
        INSERT INTO Silver.Dim_Geografia (
            {", ".join(columnas)}
        ) VALUES (
            {", ".join(valores)}
        )
    """

    conexion.execute(
        text(consulta),
        {
            "fundo": fila.get("Fundo"),
            "sector": fila.get("Sector"),
            "modulo": fila.get("Modulo"),
            "turno": fila.get("Turno"),
            "valvula": fila.get("Valvula"),
            "cama": fila.get("Cama"),
            "es_test_block": int(fila.get("Es_Test_Block", 0)),
            "codigo_sap": fila.get("Codigo_SAP_Campo"),
            "submodulo": fila.get("SubModulo"),
            "tipo_conduccion": fila.get("Tipo_Conduccion"),
            "fecha_inicio": date.today(),
        },
    )


def _contar_vigentes(engine: Engine) -> dict[str, int]:
    with engine.connect() as conexion:
        fila = conexion.execute(
            text(
                """
                SELECT
                    COUNT(*) AS Vigentes,
                    SUM(CASE WHEN ISNULL(Es_Test_Block, 0) = 1 THEN 1 ELSE 0 END) AS Test_Block,
                    SUM(CASE WHEN ISNULL(Es_Test_Block, 0) = 0 THEN 1 ELSE 0 END) AS Operativos,
                    SUM(CASE WHEN LTRIM(RTRIM(ISNULL(Cama, ''))) IN ('', '0') THEN 1 ELSE 0 END) AS Sin_Cama_Explicita
                FROM Silver.Dim_Geografia
                WHERE ISNULL(Es_Vigente, 1) = 1
                """
            )
        ).mappings().one()
    return {
        "vigentes": int(fila["Vigentes"] or 0),
        "test_block": int(fila["Test_Block"] or 0),
        "operativos": int(fila["Operativos"] or 0),
        "sin_cama_explicita": int(fila["Sin_Cama_Explicita"] or 0),
    }


def _contar_duplicados(engine: Engine, usa_submodulo_dim: bool) -> int:
    select_submodulo = (
        "ISNULL(SubModulo, -1) AS SubModulo_Normalizado,"
        if usa_submodulo_dim
        else ""
    )
    group_submodulo = "ISNULL(SubModulo, -1)," if usa_submodulo_dim else ""
    with engine.connect() as conexion:
        total = conexion.execute(
            text(
                f"""
                WITH duplicados AS (
                    SELECT
                        Modulo,
                        {select_submodulo}
                        Turno,
                        LTRIM(RTRIM(ISNULL(Valvula, ''))) AS Valvula_Normalizada,
                        LTRIM(RTRIM(ISNULL(Cama, ''))) AS Cama_Normalizada,
                        COUNT(*) AS Registros
                    FROM Silver.Dim_Geografia
                    WHERE ISNULL(Es_Vigente, 1) = 1
                    GROUP BY
                        Modulo,
                        {group_submodulo}
                        Turno,
                        LTRIM(RTRIM(ISNULL(Valvula, ''))),
                        LTRIM(RTRIM(ISNULL(Cama, '')))
                    HAVING COUNT(*) > 1
                )
                SELECT COUNT(*) AS Total_Duplicados
                FROM duplicados
                """
            )
        ).scalar_one()
    return int(total or 0)


def cargar_dim_geografia(engine: Engine) -> dict[str, int]:
    resumen = {
        "insertados": 0,
        "cerrados": 0,
        "sin_cambios": 0,
        "omitidos_modulo_no_resuelto": 0,
        "vigentes": 0,
        "operativos": 0,
        "test_block": 0,
        "sin_cama_explicita": 0,
        "duplicados": 0,
    }

    if not _tabla_existe(engine, "MDM", "Catalogo_Geografia"):
        resumen.update(_contar_vigentes(engine))
        return resumen

    df_catalogo = _cargar_catalogo_geografia(engine)
    df_vigente, usa_submodulo_dim, usa_tipo_dim = _cargar_dim_vigente(engine)

    registros_catalogo: list[dict[str, Any]] = []
    claves_catalogo: set[tuple] = set()
    for fila_catalogo in df_catalogo.to_dict('records'):
        registro = _normalizar_catalogo_fila(fila_catalogo)
        if registro.get("Modulo") is None and int(registro.get("Es_Test_Block", 0)) == 0:
            resumen["omitidos_modulo_no_resuelto"] += 1
            continue
        clave = _clave_natural(registro)
        if clave in claves_catalogo:
            continue
        claves_catalogo.add(clave)
        registros_catalogo.append(registro)

    indice_vigentes: dict[tuple, dict[str, Any]] = {}
    for fila_vigente in df_vigente.to_dict('records'):
        registro = _normalizar_dim_fila(fila_vigente)
        clave = _clave_natural(registro)
        if clave not in indice_vigentes or registro["ID_Geografia"] > indice_vigentes[clave]["ID_Geografia"]:
            indice_vigentes[clave] = registro

    with engine.begin() as conexion:
        for registro_catalogo in registros_catalogo:
            clave = _clave_natural(registro_catalogo)
            registro_existente = indice_vigentes.get(clave)
            if registro_existente is None:
                _insertar_registro(conexion, registro_catalogo, usa_submodulo_dim, usa_tipo_dim)
                resumen["insertados"] += 1
                continue

            if _hay_cambio(registro_existente, registro_catalogo, usa_tipo_dim):
                _cerrar_registro(conexion, int(registro_existente["ID_Geografia"]))
                _insertar_registro(conexion, registro_catalogo, usa_submodulo_dim, usa_tipo_dim)
                resumen["cerrados"] += 1
                resumen["insertados"] += 1
            else:
                resumen["sin_cambios"] += 1

    resumen.update(_contar_vigentes(engine))
    resumen["duplicados"] = _contar_duplicados(engine, usa_submodulo_dim)
    return resumen
