"""
verificacion_esquema.py
=======================
Valida que los objetos críticos del DWH existan en DB antes de correr el pipeline.
Llama a esto al arranque (en main.py) para detectar drift código↔DB de inmediato.

Tipos esperados:
  U = User Table
  V = View
  P = Stored Procedure
  * = cualquiera (U, V o P)
"""

from sqlalchemy import text, bindparam
from sqlalchemy.engine import Engine

# (schema, nombre, tipo_esperado)
# tipo_esperado: 'U' = tabla, 'V' = vista, 'P' = procedimiento, '*' = cualquiera
_OBJETOS_CRITICOS: list[tuple[str, str, str]] = [
    # Tablas que reciben INSERT/UPDATE — DEBEN ser 'U' (no vistas)
    ("Silver", "Dim_Geografia",          "*"),  # Puede ser U o V según la fase de migración
    ("Silver", "Dim_Fundo_Catalogo",     "U"),
    ("Silver", "Dim_Sector_Catalogo",    "U"),
    ("Silver", "Dim_Modulo_Catalogo",    "U"),
    ("Silver", "Dim_Turno_Catalogo",     "U"),
    ("Silver", "Dim_Valvula_Catalogo",   "U"),
    ("Silver", "Dim_Cama_Catalogo",      "U"),
    # MDM — pueden ser tablas o vistas según migración
    ("MDM",    "Regla_Modulo_Raw",       "U"),
    ("MDM",    "Catalogo_Geografia",     "U"),
    # Bronce — siempre tablas
    ("Bronce", "Conteo_Fruta",           "U"),
    ("Bronce", "Evaluacion_Pesos",       "U"),
    ("Bronce", "Floracion",              "U"),
]

_TIPO_LABEL = {
    'U': 'tabla',
    'V': 'vista',
    'P': 'procedimiento almacenado',
    'IF': 'función inline',
    'FN': 'función escalar',
}


def verificar_objetos_criticos(engine: Engine) -> None:
    """
    Lanza RuntimeError con la lista de objetos ausentes o con tipo incorrecto.
    Si todo está bien, retorna None silenciosamente.

    Además de verificar existencia, valida que el tipo de objeto en DB
    coincida con el tipo esperado (ej. no intentar INSERT sobre una VIEW).
    """
    nombres = [n for _, n, _ in _OBJETOS_CRITICOS]
    esquemas = list({s for s, _, _ in _OBJETOS_CRITICOS})

    with engine.connect() as conn:
        stmt = text("""
            SELECT s.name AS esquema, o.name AS objeto, o.type AS tipo
            FROM sys.objects o
            JOIN sys.schemas s ON s.schema_id = o.schema_id
            WHERE s.name IN :esquemas
              AND o.name IN :nombres
              AND o.type IN ('U', 'V', 'P', 'IF', 'FN')
        """).bindparams(
            bindparam("esquemas", expanding=True),
            bindparam("nombres",  expanding=True),
        )
        filas = conn.execute(stmt, {"esquemas": list(esquemas), "nombres": list(nombres)}).fetchall()

    encontrados = {(r[0], r[1]): r[2].strip() for r in filas}

    errores: list[str] = []
    for esquema, nombre, tipo_esperado in _OBJETOS_CRITICOS:
        clave = (esquema, nombre)
        if clave not in encontrados:
            errores.append(f"  - {esquema}.{nombre}: AUSENTE en DB")
            continue

        tipo_real = encontrados[clave]
        if tipo_esperado != '*' and tipo_real != tipo_esperado:
            label_real = _TIPO_LABEL.get(tipo_real, tipo_real)
            label_esperado = _TIPO_LABEL.get(tipo_esperado, tipo_esperado)
            errores.append(
                f"  - {esquema}.{nombre}: es {label_real} ({tipo_real}) "
                f"pero se espera {label_esperado} ({tipo_esperado})"
            )

    if errores:
        raise RuntimeError(
            "Objetos críticos con problemas en DB — corrija antes de ejecutar el pipeline:\n"
            + "\n".join(errores)
        )
