"""
dim_geografia_v2.py
===================
Sincroniza Silver.Dim_Geografia (Arquitectura de Catálogos)
desde MDM.Catalogo_Geografia (Geografías Aprendidas y Validadas).

Patrón Get-or-Create dinámico para poblar los 7 catálogos y 
la Junk Dimension preservando el historial SCD Tipo 2.
"""

from __future__ import annotations
from datetime import date
import logging
import re
from typing import Any
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.texto import limpiar_numerico_texto, titulo, normalizar_espacio
from silver.dims.dim_geografia import _normalizar_texto, _normalizar_codigo, _normalizar_entero, _parsear_modulo_operativo, _columna_existe, _tabla_existe

_log = logging.getLogger("ETL_Pipeline")

class GestorCatalogos:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.fundos = {}
        self.sectores = {}
        self.modulos = {}
        self.turnos = {}
        self.valvulas = {}
        self.camas = {}
        self._cargar_caches()

    def _cargar_caches(self):
        with self.engine.connect() as conn:
            # Fundos
            for row in conn.execute(text("SELECT ID_Fundo_Catalogo, Fundo FROM Silver.Dim_Fundo_Catalogo")).mappings():
                if row['Fundo']: self.fundos[row['Fundo'].upper()] = row['ID_Fundo_Catalogo']
            
            # Sectores
            for row in conn.execute(text("SELECT ID_Sector_Catalogo, Sector FROM Silver.Dim_Sector_Catalogo")).mappings():
                if row['Sector']: self.sectores[row['Sector'].upper()] = row['ID_Sector_Catalogo']
            
            # Modulos (Clave compuesta: Modulo_SubModulo)
            for row in conn.execute(text("SELECT ID_Modulo_Catalogo, Modulo, SubModulo FROM Silver.Dim_Modulo_Catalogo")).mappings():
                clave = f"{row['Modulo']}_{row['SubModulo'] if row['SubModulo'] is not None else -1}"
                self.modulos[clave] = row['ID_Modulo_Catalogo']
            
            # Turnos
            for row in conn.execute(text("SELECT ID_Turno_Catalogo, Turno FROM Silver.Dim_Turno_Catalogo")).mappings():
                self.turnos[row['Turno']] = row['ID_Turno_Catalogo']
            
            # Valvulas
            for row in conn.execute(text("SELECT ID_Valvula_Catalogo, Valvula FROM Silver.Dim_Valvula_Catalogo")).mappings():
                if row['Valvula']: self.valvulas[row['Valvula'].upper()] = row['ID_Valvula_Catalogo']

            # Camas (Catalogo Legacy si existe)
            if _tabla_existe(self.engine, "Silver", "Dim_Cama_Catalogo"):
                try:
                    for row in conn.execute(text("SELECT ID_Cama_Catalogo, Cama_Normalizada FROM Silver.Dim_Cama_Catalogo")).mappings():
                        if row['Cama_Normalizada']: self.camas[row['Cama_Normalizada'].upper()] = row['ID_Cama_Catalogo']
                except:
                    pass

    def get_or_create_fundo(self, conn, fundo: str) -> int:
        if not fundo: return 0
        clave = fundo.upper()
        if clave in self.fundos: return self.fundos[clave]
        res = conn.execute(text("INSERT INTO Silver.Dim_Fundo_Catalogo (Fundo) OUTPUT INSERTED.ID_Fundo_Catalogo VALUES (:v)"), {"v": fundo}).scalar_one()
        self.fundos[clave] = res
        return res

    def get_or_create_sector(self, conn, sector: str) -> int:
        if not sector: return 0
        clave = sector.upper()
        if clave in self.sectores: return self.sectores[clave]
        res = conn.execute(text("INSERT INTO Silver.Dim_Sector_Catalogo (Sector) OUTPUT INSERTED.ID_Sector_Catalogo VALUES (:v)"), {"v": sector}).scalar_one()
        self.sectores[clave] = res
        return res

    def get_or_create_modulo(self, conn, modulo: int, submodulo: int, tipo_conduccion: str) -> int:
        if modulo is None: return 0
        clave = f"{modulo}_{submodulo if submodulo is not None else -1}"
        if clave in self.modulos: return self.modulos[clave]
        res = conn.execute(text("""
            INSERT INTO Silver.Dim_Modulo_Catalogo (Modulo, SubModulo, Tipo_Conduccion) 
            OUTPUT INSERTED.ID_Modulo_Catalogo 
            VALUES (:m, :sm, :tc)
        """), {"m": modulo, "sm": submodulo, "tc": tipo_conduccion}).scalar_one()
        self.modulos[clave] = res
        return res

    def get_or_create_turno(self, conn, turno: int) -> int:
        if turno is None: return 0
        if turno in self.turnos: return self.turnos[turno]
        res = conn.execute(text("INSERT INTO Silver.Dim_Turno_Catalogo (Turno) OUTPUT INSERTED.ID_Turno_Catalogo VALUES (:v)"), {"v": turno}).scalar_one()
        self.turnos[turno] = res
        return res

    def get_or_create_valvula(self, conn, valvula: str) -> int:
        if not valvula: return 0
        clave = valvula.upper()
        if clave in self.valvulas: return self.valvulas[clave]
        res = conn.execute(text("INSERT INTO Silver.Dim_Valvula_Catalogo (Valvula) OUTPUT INSERTED.ID_Valvula_Catalogo VALUES (:v)"), {"v": valvula}).scalar_one()
        self.valvulas[clave] = res
        return res

    def get_or_create_cama(self, conn, cama: str) -> int:
        # Simplificado: asume que las camas ya vienen creadas en Dim_Cama_Catalogo
        if not cama: return 0
        clave = cama.upper()
        if clave in self.camas: return self.camas[clave]
        return 0


def _cargar_catalogo_crudo(engine: Engine) -> pd.DataFrame:
    """
    Carga los datos desde la tabla obsoleta para el rescate inicial.
    """
    consulta = """
        SELECT
            c.Fundo, c.Sector, c.Modulo AS Modulo_Raw, c.Turno, c.Valvula, c.Cama, c.Codigo_SAP_Campo,
            ISNULL(c.Es_Test_Block, 0) AS Es_Test_Block_Catalogo,
            c.SubModulo AS SubModulo_Catalogo,
            c.Tipo_Conduccion AS Tipo_Conduccion_Catalogo,
            NULL AS Modulo_Regla,
            NULL AS SubModulo_Regla,
            NULL AS Tipo_Conduccion_Regla,
            0 AS Es_Test_Block_Regla
        FROM Silver.Dim_Geografia_Obsoleta c
        WHERE ISNULL(c.Es_Vigente, 1) = 1
    """
    with engine.connect() as conexion:
        return pd.read_sql(consulta, conexion)

def cargar_dim_geografia_v2(engine: Engine) -> dict[str, int]:
    resumen = {"insertados": 0, "cerrados": 0, "sin_cambios": 0}
    
    if not _tabla_existe(engine, "Silver", "Dim_Geografia_Base") and not _tabla_existe(engine, "Silver", "Dim_Geografia"):
        _log.warning(
            "WARNING: Silver.Dim_Geografia_Base y Silver.Dim_Geografia ausentes. "
            "Se omite sincronización. Verifique el esquema."
        )
        return resumen

    # Si no existe Obsoleta, no hay nada que rescatar hacia la nueva arquitectura
    if not _tabla_existe(engine, "Silver", "Dim_Geografia_Obsoleta"):
        _log.info("INFO: Silver.Dim_Geografia_Obsoleta ausente. Se asume migración completa y catálogos estables.")
        return resumen

    # 1. Cargar datos crudos y Catálogos
    df_raw = _cargar_catalogo_crudo(engine)
    gestor = GestorCatalogos(engine)

    # 2. Cargar combinaciones activas en memoria
    combinaciones_activas = {}
    with engine.connect() as conn:
        for row in conn.execute(text("SELECT * FROM Silver.Dim_Geografia WHERE Es_Vigente = 1")).mappings():
            clave = (row['ID_Fundo_Catalogo'], row['ID_Sector_Catalogo'], row['ID_Modulo_Catalogo'], 
                     row['ID_Turno_Catalogo'], row['ID_Valvula_Catalogo'], row['ID_Cama_Catalogo'])
            combinaciones_activas[clave] = dict(row)

    # 3 + 4. Procesar catálogos y aplicar SCD Tipo 2 en una sola transacción
    with engine.begin() as conn:
        registros_a_procesar = {}

        for fila in df_raw.to_dict('records'):
            modulo_por_regla = _normalizar_entero(fila.get("Modulo_Regla"))
            submodulo_cat = _normalizar_entero(fila.get("SubModulo_Catalogo"))
            submodulo_reg = _normalizar_entero(fila.get("SubModulo_Regla"))
            modulo_int = modulo_por_regla if modulo_por_regla is not None else _parsear_modulo_operativo(fila.get("Modulo_Raw"))
            submodulo_int = submodulo_cat if submodulo_cat is not None else submodulo_reg

            tipo_cond = _normalizar_texto(fila.get("Tipo_Conduccion_Catalogo")) or _normalizar_texto(fila.get("Tipo_Conduccion_Regla"))
            es_test = 1 if (_normalizar_entero(fila.get("Es_Test_Block_Catalogo")) == 1 or _normalizar_entero(fila.get("Es_Test_Block_Regla")) == 1) else 0

            if es_test == 1 and modulo_int is None: modulo_int = -1
            if modulo_int is None and es_test == 0: continue

            fundo_str = _normalizar_texto(fila.get("Fundo"), True)
            sector_str = _normalizar_texto(fila.get("Sector"), True)
            turno_int = _normalizar_entero(fila.get("Turno"))
            valvula_str = _normalizar_codigo(fila.get("Valvula"))
            cama_str = _normalizar_codigo(fila.get("Cama"))
            cod_sap = _normalizar_texto(fila.get("Codigo_SAP_Campo"))

            if cama_str: granularidad = 'HASTA_CAMA'
            elif valvula_str: granularidad = 'HASTA_VALVULA'
            elif turno_int: granularidad = 'HASTA_TURNO'
            else: granularidad = 'HASTA_MODULO'

            id_fundo = gestor.get_or_create_fundo(conn, fundo_str)
            id_sector = gestor.get_or_create_sector(conn, sector_str)
            id_modulo = gestor.get_or_create_modulo(conn, modulo_int, submodulo_int, tipo_cond)
            id_turno = gestor.get_or_create_turno(conn, turno_int)
            id_valvula = gestor.get_or_create_valvula(conn, valvula_str)
            id_cama = gestor.get_or_create_cama(conn, cama_str)

            clave_comb = (id_fundo, id_sector, id_modulo, id_turno, id_valvula, id_cama)
            registros_a_procesar[clave_comb] = {
                "Es_Test_Block": es_test,
                "Codigo_SAP_Campo": cod_sap,
                "Nivel_Granularidad": granularidad,
            }

        hoy = date.today()
        for clave, atributos in registros_a_procesar.items():
            existente = combinaciones_activas.get(clave)

            es_nuevo = existente is None
            cambio_scd = not es_nuevo and (
                existente.get('Codigo_SAP_Campo') != atributos['Codigo_SAP_Campo'] or
                existente.get('Es_Test_Block') != atributos['Es_Test_Block']
            )

            if cambio_scd:
                conn.execute(
                    text("UPDATE Silver.Dim_Geografia SET Fecha_Fin_Vigencia = :hoy, Es_Vigente = 0 WHERE ID_Geografia = :id"),
                    {"hoy": hoy, "id": existente['ID_Geografia']},
                )
                resumen["cerrados"] += 1

            if es_nuevo or cambio_scd:
                conn.execute(text("""
                    INSERT INTO Silver.Dim_Geografia
                    (ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo, ID_Turno_Catalogo,
                     ID_Valvula_Catalogo, ID_Cama_Catalogo, Es_Test_Block, Codigo_SAP_Campo,
                     Nivel_Granularidad, Fecha_Inicio_Vigencia)
                    VALUES (:f, :s, :m, :t, :v, :c, :tb, :sap, :niv, :hoy)
                """), {
                    "f": clave[0], "s": clave[1], "m": clave[2], "t": clave[3],
                    "v": clave[4], "c": clave[5],
                    "tb": atributos['Es_Test_Block'], "sap": atributos['Codigo_SAP_Campo'],
                    "niv": atributos['Nivel_Granularidad'], "hoy": hoy,
                })
                resumen["insertados"] += 1
            else:
                resumen["sin_cambios"] += 1

    return resumen