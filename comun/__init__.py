"""
comun/
======
Capa compartida entre ETL y backend ACP.

Contiene SOLO utilidades que ambos lados consumen para evitar duplicacion:
- conexion: factory de Engine SQLAlchemy unica
- sql_utils: helpers de mapeo y ejecucion de queries
- validacion: re-export de validadores de DNI / fechas (canonicos en ETL/utils)

Reglas:
- No depender de modulos especificos de ETL ni de backend.
- Configuración tipada común desde el .env raíz y variables del entorno.
- Todo singleton es per-process, thread-safe.
"""
