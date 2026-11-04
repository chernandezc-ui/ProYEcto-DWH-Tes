"""
Generador de documentacion para ACP_DataWarehose_Proyecciones.

- Introspeccion read-only sobre SQL Server.
- Produce:
    1) Archivos Markdown para Obsidian (un archivo por objeto)
       en D:\\Proyecto2026\\.obsidian\\ACP_DWH\\Proyecciones\\
    2) DDL consolidado v3 sincronizado con la BD real en
       ETL\\sql_migrations\\DDL_DataWarehose_Proyecciones_v3.sql

Idempotente: cada ejecucion regenera todo (excepto carpetas de prosa).
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

DB_NAME = "ACP_DataWarehose_Proyecciones"
VAULT_ROOT = Path(r"D:\Proyecto2026\.obsidian\ACP_DWH\Proyecciones")
DDL_OUT = Path(
    r"D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\sql_migrations"
    r"\DDL_DataWarehose_Proyecciones_v3.sql"
)

LAYER_TAGS = {"Bronce": "bronze", "Silver": "silver", "Gold": "gold"}


def make_engine():
    params = quote_plus(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


# ----------------------------- Metadata loaders -----------------------------

def load_schemas(conn):
    rows = conn.execute(text("""
        SELECT s.name
        FROM sys.schemas s
        WHERE s.name NOT IN ('sys','INFORMATION_SCHEMA','guest',
            'db_owner','db_accessadmin','db_securityadmin','db_ddladmin',
            'db_backupoperator','db_datareader','db_datawriter',
            'db_denydatareader','db_denydatawriter')
        ORDER BY s.name
    """)).fetchall()
    return [r[0] for r in rows]


def load_tables(conn):
    rows = conn.execute(text("""
        SELECT s.name, t.name, t.object_id
        FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id
        ORDER BY s.name, t.name
    """)).fetchall()
    return [dict(schema=r[0], name=r[1], object_id=r[2]) for r in rows]


def load_columns(conn):
    rows = conn.execute(text("""
        SELECT
            c.object_id, c.column_id, c.name, ty.name,
            c.max_length, c.precision, c.scale,
            c.is_nullable, c.is_identity, dc.definition
        FROM sys.columns c
        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        LEFT JOIN sys.default_constraints dc
            ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
        ORDER BY c.object_id, c.column_id
    """)).fetchall()
    cols = defaultdict(list)
    for r in rows:
        cols[r[0]].append(dict(
            column_id=r[1], name=r[2], type=r[3],
            max_length=r[4], precision=r[5], scale=r[6],
            nullable=bool(r[7]), identity=bool(r[8]), default=r[9],
        ))
    return cols


def load_primary_keys(conn):
    rows = conn.execute(text("""
        SELECT i.object_id, c.name
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.is_primary_key = 1
        ORDER BY i.object_id, ic.key_ordinal
    """)).fetchall()
    pks = defaultdict(list)
    for oid, col in rows:
        pks[oid].append(col)
    return pks


def load_indexes(conn):
    rows = conn.execute(text("""
        SELECT
            i.object_id, i.name, i.type_desc, i.is_unique, i.is_primary_key,
            c.name, ic.key_ordinal, ic.is_included_column
        FROM sys.indexes i
        JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE i.type > 0 AND i.is_hypothetical = 0
        ORDER BY i.object_id, i.index_id, ic.key_ordinal
    """)).fetchall()
    idx = defaultdict(lambda: defaultdict(lambda: dict(cols=[], included=[], info=None)))
    for r in rows:
        oid, name, type_desc, is_unique, is_pk, col, ord_, incl = r
        if not name:
            continue
        entry = idx[oid][name]
        entry["info"] = dict(type=type_desc, unique=bool(is_unique), pk=bool(is_pk))
        if incl:
            entry["included"].append(col)
        else:
            entry["cols"].append(col)
    return idx


def load_foreign_keys(conn):
    rows = conn.execute(text("""
        SELECT
            fk.name,
            ps.name, pt.name, pc.name,
            rs.name, rt.name, rc.name,
            fk.parent_object_id, fk.referenced_object_id,
            fkc.constraint_column_id
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.tables pt ON pt.object_id = fk.parent_object_id
        JOIN sys.schemas ps ON ps.schema_id = pt.schema_id
        JOIN sys.columns pc ON pc.object_id = fkc.parent_object_id
            AND pc.column_id = fkc.parent_column_id
        JOIN sys.tables rt ON rt.object_id = fk.referenced_object_id
        JOIN sys.schemas rs ON rs.schema_id = rt.schema_id
        JOIN sys.columns rc ON rc.object_id = fkc.referenced_object_id
            AND rc.column_id = fkc.referenced_column_id
        ORDER BY fk.name, fkc.constraint_column_id
    """)).fetchall()
    by_parent = defaultdict(list)
    by_ref = defaultdict(list)
    all_fks = defaultdict(lambda: dict(name=None, parent=None, ref=None, cols=[]))
    for r in rows:
        name, ps_, pt_, pc_, rs_, rt_, rc_, p_oid, r_oid, _ = r
        entry = all_fks[name]
        entry["name"] = name
        entry["parent"] = (ps_, pt_, p_oid)
        entry["ref"] = (rs_, rt_, r_oid)
        entry["cols"].append((pc_, rc_))
    for fk in all_fks.values():
        by_parent[fk["parent"][2]].append(fk)
        by_ref[fk["ref"][2]].append(fk)
    return all_fks, by_parent, by_ref


def load_modules(conn):
    rows = conn.execute(text("""
        SELECT
            o.object_id, s.name, o.name, o.type_desc, m.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        LEFT JOIN sys.sql_modules m ON m.object_id = o.object_id
        WHERE o.is_ms_shipped = 0
          AND o.type IN ('V','P','FN','IF','TF','TR')
        ORDER BY s.name, o.type, o.name
    """)).fetchall()
    return [
        dict(object_id=r[0], schema=r[1], name=r[2], type_desc=r[3], code=r[4] or "")
        for r in rows
    ]


def load_proc_params(conn):
    rows = conn.execute(text("""
        SELECT p.object_id, p.name, ty.name,
               p.max_length, p.precision, p.scale, p.is_output, p.parameter_id
        FROM sys.parameters p
        JOIN sys.types ty ON p.user_type_id = ty.user_type_id
        ORDER BY p.object_id, p.parameter_id
    """)).fetchall()
    out = defaultdict(list)
    for r in rows:
        out[r[0]].append(dict(
            name=r[1], type=r[2], max_length=r[3], precision=r[4],
            scale=r[5], is_output=bool(r[6])))
    return out


def load_dependencies(conn):
    rows = conn.execute(text("""
        SELECT
            d.referencing_id,
            COALESCE(d.referenced_schema_name, OBJECT_SCHEMA_NAME(d.referenced_id)),
            d.referenced_entity_name
        FROM sys.sql_expression_dependencies d
        WHERE d.referenced_entity_name IS NOT NULL
    """)).fetchall()
    deps_out = defaultdict(set)
    for ref_id, sch, name in rows:
        if not sch or not name:
            continue
        deps_out[ref_id].add(f"{sch}.{name}")
    return deps_out


# ----------------------------- Format helpers -----------------------------

def format_type(type_name, max_length, precision, scale):
    t = type_name.lower()
    if t in ("nvarchar", "nchar"):
        n = max_length // 2 if max_length and max_length > 0 else -1
        return f"{type_name.upper()}({'MAX' if max_length == -1 else n})"
    if t in ("varchar", "char", "varbinary", "binary"):
        return f"{type_name.upper()}({'MAX' if max_length == -1 else max_length})"
    if t in ("decimal", "numeric"):
        return f"{type_name.upper()}({precision},{scale})"
    if t in ("datetime2", "time", "datetimeoffset"):
        return f"{type_name.upper()}({scale})"
    return type_name.upper()


def safe_filename(s):
    return s.replace("/", "_").replace("\\", "_")


def wikilink(folder, schema, name, label=None):
    target = f"{folder}/{schema}.{safe_filename(name)}"
    return f"[[{target}|{label}]]" if label else f"[[{target}]]"


# ----------------------------- Renderers -----------------------------

def render_table_md(t, columns, pks, indexes, fks_out, fks_in, deps_in_map):
    schema, name, oid = t["schema"], t["name"], t["object_id"]
    layer = LAYER_TAGS.get(schema, schema.lower())
    pk_cols = set(pks.get(oid, []))
    cols = columns.get(oid, [])
    L = []
    L += ["---", "type: table", f"schema: {schema}", f"layer: {layer}",
          f"database: {DB_NAME}", f"tags: [dwh, {layer}, table]", "---",
          f"# {schema}.{name}", "",
          f"> Tabla del schema **{schema}** ({layer}) en `{DB_NAME}`.", "",
          f"- Schema: [[_schemas/{schema}]]", "- Tipo: tabla de usuario", "",
          "## Columnas", "",
          "| # | Columna | Tipo | Null | Default | PK | Identity |",
          "|---|---------|------|------|---------|----|----------|"]
    for c in cols:
        is_pk = "PK" if c["name"] in pk_cols else ""
        ident = "ID" if c["identity"] else ""
        nullable = "NULL" if c["nullable"] else "NOT NULL"
        default = (c["default"] or "").replace("|", "\\|")
        L.append(
            f"| {c['column_id']} | `{c['name']}` | "
            f"{format_type(c['type'], c['max_length'], c['precision'], c['scale'])} | "
            f"{nullable} | {default} | {is_pk} | {ident} |"
        )
    L += ["", "## Llaves"]
    if pk_cols:
        L.append(f"- **PK**: {', '.join('`' + p + '`' for p in pks.get(oid, []))}")
    else:
        L.append("- _Sin Primary Key_")
    for fk in fks_out.get(oid, []):
        rs_, rt_, _ = fk["ref"]
        pair = ", ".join(f"`{c[0]}` -> `{c[1]}`" for c in fk["cols"])
        L.append(f"- **FK** `{fk['name']}`: {pair} -> {wikilink('tables', rs_, rt_)}")
    for fk in fks_in.get(oid, []):
        ps_, pt_, _ = fk["parent"]
        L.append(f"- **Referenciada por**: {wikilink('tables', ps_, pt_)} (`{fk['name']}`)")
    L += ["", "## Indices"]
    idxs = indexes.get(oid, {})
    non_pk = {n: v for n, v in idxs.items() if not v["info"]["pk"]}
    if not non_pk:
        L.append("- _Sin indices adicionales_")
    else:
        for n, v in non_pk.items():
            info = v["info"]
            tag = "UNIQUE " if info["unique"] else ""
            cols_s = ", ".join(f"`{c}`" for c in v["cols"])
            inc = f" INCLUDE ({', '.join('`' + c + '`' for c in v['included'])})" if v["included"] else ""
            L.append(f"- {tag}{info['type']} `{n}` ({cols_s}){inc}")
    refs_in = deps_in_map.get(f"{schema}.{name}", set())
    if refs_in:
        L += ["", "## Usada por"]
        for r in sorted(refs_in):
            L.append(f"- {r}")
    L += ["", "## Notas", "> _(anade aqui descripcion funcional, reglas de negocio, etc.)_", ""]
    return "\n".join(L)


def render_module_md(m, params, deps_out, deps_in_map):
    schema, name, oid, type_desc = m["schema"], m["name"], m["object_id"], m["type_desc"]
    folder = {
        "VIEW": "views",
        "SQL_STORED_PROCEDURE": "procedures",
        "SQL_SCALAR_FUNCTION": "functions",
        "SQL_INLINE_TABLE_VALUED_FUNCTION": "functions",
        "SQL_TABLE_VALUED_FUNCTION": "functions",
        "SQL_TRIGGER": "triggers",
    }.get(type_desc, "objects")
    kind_label = {
        "VIEW": "View",
        "SQL_STORED_PROCEDURE": "Stored Procedure",
        "SQL_SCALAR_FUNCTION": "Scalar Function",
        "SQL_INLINE_TABLE_VALUED_FUNCTION": "Inline TVF",
        "SQL_TABLE_VALUED_FUNCTION": "Table-valued Function",
        "SQL_TRIGGER": "Trigger",
    }.get(type_desc, type_desc)
    L = []
    L += ["---", f"type: {folder.rstrip('s')}", f"schema: {schema}",
          f"database: {DB_NAME}", f"object_kind: {kind_label}",
          f"tags: [dwh, {folder.rstrip('s')}, {schema.lower()}]", "---",
          f"# {schema}.{name}", "",
          f"> {kind_label} del schema **{schema}** en `{DB_NAME}`.", "",
          f"- Schema: [[_schemas/{schema}]]", ""]
    if type_desc == "SQL_STORED_PROCEDURE" or type_desc.endswith("FUNCTION"):
        ps = [p for p in params.get(oid, []) if p["name"]]
        L.append("## Parametros")
        if not ps:
            L.append("- _Sin parametros_")
        else:
            L += ["", "| # | Nombre | Tipo | Direccion |", "|---|--------|------|-----------|"]
            for i, p in enumerate(ps, 1):
                direction = "OUT" if p["is_output"] else "IN"
                tp = format_type(p["type"], p["max_length"], p["precision"], p["scale"])
                L.append(f"| {i} | `{p['name']}` | {tp} | {direction} |")
        L.append("")
    refs = sorted(deps_out.get(oid, set()))
    if refs:
        L.append("## Referencia a")
        for r in refs:
            try:
                sch, nm = r.split(".", 1)
                L.append(f"- {wikilink('tables', sch, nm)}")
            except ValueError:
                L.append(f"- `{r}`")
        L.append("")
    refs_in = deps_in_map.get(f"{schema}.{name}", set())
    if refs_in:
        L.append("## Referenciado por")
        for r in sorted(refs_in):
            L.append(f"- {r}")
        L.append("")
    L += ["## Codigo", "", "```sql", (m["code"] or "").rstrip(), "```", "",
          "## Notas", "> _(anade aqui descripcion funcional / reglas / cambios)._", ""]
    return "\n".join(L)


def render_schema_md(schema, tables_by_schema, modules_by_schema):
    layer = LAYER_TAGS.get(schema, schema.lower())
    descr = {
        "Bronce": "Capa **Bronze**. Datos crudos sin transformar.",
        "Silver": "Capa **Silver**. Datos limpios, tipados y conformados.",
        "Gold": "Capa **Gold**. Datos listos para consumo analitico.",
        "MDM": "Master Data Management. Catalogos maestros.",
        "Config": "Configuracion y parametrizacion del DWH.",
        "Control": "Control y orquestacion: corridas, dependencias.",
        "Auditoria": "Auditoria y trazabilidad de cambios.",
        "Admin": "Objetos administrativos del DWH.",
        "Seguridad": "Roles, accesos y permisos.",
        "dbo": "Schema por defecto. Funciones utilitarias y SPs transversales.",
    }.get(schema, "")
    L = ["---", "type: schema", f"name: {schema}", f"layer: {layer}",
         f"tags: [dwh, schema, {layer}]", "---", f"# Schema . {schema}", "",
         f"> {descr}", ""]
    ts = tables_by_schema.get(schema, [])
    if ts:
        L.append("## Tablas")
        for t in sorted(ts, key=lambda x: x["name"]):
            L.append(f"- {wikilink('tables', schema, t['name'])}")
        L.append("")
    ms = modules_by_schema.get(schema, [])
    groups = defaultdict(list)
    for m in ms:
        groups[m["type_desc"]].append(m)
    labels = [
        ("VIEW", "Views", "views"),
        ("SQL_STORED_PROCEDURE", "Stored Procedures", "procedures"),
        ("SQL_SCALAR_FUNCTION", "Funciones escalares", "functions"),
        ("SQL_INLINE_TABLE_VALUED_FUNCTION", "Inline TVFs", "functions"),
        ("SQL_TABLE_VALUED_FUNCTION", "Table-valued Functions", "functions"),
        ("SQL_TRIGGER", "Triggers", "triggers"),
    ]
    for type_desc, label, folder in labels:
        items = groups.get(type_desc, [])
        if items:
            L.append(f"## {label}")
            for it in sorted(items, key=lambda x: x["name"]):
                L.append(f"- {wikilink(folder, schema, it['name'])}")
            L.append("")
    return "\n".join(L)


def render_index_md(schemas, counts):
    total_t = sum(c["tables"] for c in counts.values())
    total_v = sum(c["views"] for c in counts.values())
    total_p = sum(c["procs"] for c in counts.values())
    total_f = sum(c["funcs"] for c in counts.values())
    L = ["---", "type: index", f"database: {DB_NAME}", "tags: [dwh, index]", "---",
         f"# {DB_NAME}", "", "**Data Warehouse - Agricola Cerro Prieto . Proyecciones**", "",
         "Arquitectura **Medallion** (Bronce -> Silver -> Gold) sobre SQL Server.", "",
         "## Diagramas", "- [[ERD]] - diagrama de relaciones (Mermaid)", "",
         "## Secciones operativas",
         "- [[conexiones/index|Conexiones]] - SQL Server, pool/engine, parametros runtime.",
         "- [[pipelines/index|Pipelines ETL]] - orquestacion, Bronce->Silver->Gold, MDM, DQ, auditoria, runbook.", "",
         "## Schemas", "",
         "| Schema | Capa | Tablas | Views | SPs | Funciones |",
         "|--------|------|-------:|------:|----:|----------:|"]
    for s in schemas:
        layer = LAYER_TAGS.get(s, s.lower())
        c = counts.get(s, dict(tables=0, views=0, procs=0, funcs=0))
        L.append(f"| [[_schemas/{s}]] | {layer} | {c['tables']} | {c['views']} | {c['procs']} | {c['funcs']} |")
    L.append(f"| **TOTAL** | - | **{total_t}** | **{total_v}** | **{total_p}** | **{total_f}** |")
    L += ["", "## Como navegar",
          "- Cada tabla, vista, SP y funcion tiene su propio archivo.",
          "- Las relaciones (FK) se renderizan como `[[wikilinks]]` entre archivos.",
          "- Usa la vista de **Graph** de Obsidian para ver el grafo completo.", "",
          "## Proximas secciones",
          "- Microservicios", "- APIs", "- Decisiones tecnicas (ADRs)",
          "- Queries importantes / Troubleshooting", "- Arquitectura ML", ""]
    return "\n".join(L)


def render_erd_md(tables, all_fks):
    L = ["---", "type: erd", "tags: [dwh, erd]", "---",
         "# ERD . ACP_DataWarehose_Proyecciones", "",
         "Diagrama global de relaciones entre tablas (todas las FKs).", "",
         "```mermaid", "erDiagram"]
    table_set = {(t["schema"], t["name"]) for t in tables}
    rendered_tables = set()
    for fk in all_fks.values():
        ps_, pt_, _ = fk["parent"]
        rs_, rt_, _ = fk["ref"]
        a, b = f"{ps_}__{pt_}", f"{rs_}__{rt_}"
        L.append(f"    {b} ||--o{{ {a} : \"{fk['name']}\"")
        rendered_tables.add((ps_, pt_))
        rendered_tables.add((rs_, rt_))
    for s, n in sorted(table_set - rendered_tables):
        L += [f"    {s}__{n} {{", "    }"]
    L += ["```", ""]
    return "\n".join(L)


# ----------------------------- DDL generator -----------------------------

def render_ddl(schemas, tables, columns, pks, indexes, all_fks, modules):
    out = []
    out += [
        "-- " + "=" * 72,
        "-- DDL . ACP_DataWarehose_Proyecciones - Agricola Cerro Prieto",
        "-- v3 - Sincronizado con la BD real (autogenerado por ETL/tools/generate_docs.py)",
        "-- Collation: Modern_Spanish_CI_AS",
        "-- " + "=" * 72,
        "USE master;", "GO", "",
        "IF DB_ID('ACP_DataWarehose_Proyecciones') IS NULL",
        "BEGIN",
        "    CREATE DATABASE ACP_DataWarehose_Proyecciones",
        "        COLLATE Modern_Spanish_CI_AS;",
        "END", "GO",
        "USE ACP_DataWarehose_Proyecciones;", "GO", "",
        "-- " + "=" * 72,
        "-- SCHEMAS",
        "-- " + "=" * 72,
    ]
    for s in schemas:
        if s == "dbo":
            continue
        out.append(f"IF SCHEMA_ID('{s}') IS NULL EXEC('CREATE SCHEMA [{s}]');")
        out.append("GO")
    out.append("")

    schema_order = ["Bronce", "Silver", "Gold", "MDM", "Config", "Control",
                    "Auditoria", "Admin", "Seguridad", "dbo"]
    schema_order += [s for s in schemas if s not in schema_order]

    out += ["-- " + "=" * 72, "-- TABLAS", "-- " + "=" * 72]
    tables_by_schema = defaultdict(list)
    for t in tables:
        tables_by_schema[t["schema"]].append(t)
    for s in schema_order:
        ts = tables_by_schema.get(s, [])
        if not ts:
            continue
        out.append("")
        out.append(f"-- ---- Schema [{s}] . {len(ts)} tablas ----")
        for t in sorted(ts, key=lambda x: x["name"]):
            out.append("")
            out.append(f"IF OBJECT_ID('[{s}].[{t['name']}]','U') IS NULL")
            out.append("BEGIN")
            out.append(f"CREATE TABLE [{s}].[{t['name']}] (")
            cdefs = []
            cols = columns.get(t["object_id"], [])
            pk_cols = pks.get(t["object_id"], [])
            for c in cols:
                tp = format_type(c["type"], c["max_length"], c["precision"], c["scale"])
                parts = [f"    [{c['name']}] {tp}"]
                if c["identity"]:
                    parts.append("IDENTITY(1,1)")
                parts.append("NULL" if c["nullable"] else "NOT NULL")
                if c["default"]:
                    parts.append(f"DEFAULT {c['default']}")
                cdefs.append(" ".join(parts))
            if pk_cols:
                cdefs.append(
                    f"    CONSTRAINT [PK_{t['schema']}_{t['name']}] PRIMARY KEY "
                    f"({', '.join('[' + c + ']' for c in pk_cols)})"
                )
            out.append(",\n".join(cdefs))
            out.append(");")
            out.append("END")
            out.append("GO")

    out += ["", "-- " + "=" * 72, "-- INDICES (no-PK)", "-- " + "=" * 72]
    table_by_oid = {t["object_id"]: t for t in tables}
    for oid, idxs in indexes.items():
        if oid not in table_by_oid:
            continue
        t = table_by_oid[oid]
        for name, v in idxs.items():
            if v["info"]["pk"]:
                continue
            unique = "UNIQUE " if v["info"]["unique"] else ""
            kind = "CLUSTERED" if "CLUSTERED" in v["info"]["type"] and "NON" not in v["info"]["type"] else "NONCLUSTERED"
            cols_s = ", ".join(f"[{c}]" for c in v["cols"])
            inc = f" INCLUDE ({', '.join('[' + c + ']' for c in v['included'])})" if v["included"] else ""
            out.append(
                f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='{name}' "
                f"AND object_id=OBJECT_ID('[{t['schema']}].[{t['name']}]'))"
            )
            out.append(
                f"    CREATE {unique}{kind} INDEX [{name}] ON "
                f"[{t['schema']}].[{t['name']}] ({cols_s}){inc};"
            )
            out.append("GO")

    out += ["", "-- " + "=" * 72, "-- FOREIGN KEYS", "-- " + "=" * 72]
    for fk in all_fks.values():
        ps_, pt_, _ = fk["parent"]
        rs_, rt_, _ = fk["ref"]
        pcols = ", ".join(f"[{c[0]}]" for c in fk["cols"])
        rcols = ", ".join(f"[{c[1]}]" for c in fk["cols"])
        out.append(f"IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='{fk['name']}')")
        out.append(
            f"    ALTER TABLE [{ps_}].[{pt_}] WITH CHECK ADD CONSTRAINT [{fk['name']}] "
            f"FOREIGN KEY ({pcols}) REFERENCES [{rs_}].[{rt_}] ({rcols});"
        )
        out.append("GO")

    out += ["", "-- " + "=" * 72,
            "-- VIEWS / PROCEDURES / FUNCTIONS / TRIGGERS",
            "-- " + "=" * 72]
    for m in modules:
        out.append("")
        out.append(f"-- [{m['schema']}].[{m['name']}] ({m['type_desc']})")
        code = (m["code"] or "").strip()
        if not code:
            out.append("-- (sin definicion disponible)")
            continue
        out.append(code)
        out.append("GO")

    return "\n".join(out) + "\n"


# ----------------------------- Main -----------------------------

def main():
    eng = make_engine()
    with eng.connect() as conn:
        schemas = load_schemas(conn)
        tables = load_tables(conn)
        columns = load_columns(conn)
        pks = load_primary_keys(conn)
        indexes = load_indexes(conn)
        all_fks, fks_by_parent, fks_by_ref = load_foreign_keys(conn)
        modules = load_modules(conn)
        proc_params = load_proc_params(conn)
        deps_out = load_dependencies(conn)

    obj_oid_to_fqn = {t["object_id"]: f"{t['schema']}.{t['name']}" for t in tables}
    for m in modules:
        obj_oid_to_fqn[m["object_id"]] = f"{m['schema']}.{m['name']}"
    deps_in_map = defaultdict(set)
    for ref_id, refs in deps_out.items():
        src = obj_oid_to_fqn.get(ref_id)
        if not src:
            continue
        for fqn in refs:
            deps_in_map[fqn].add(src)

    tables_by_schema = defaultdict(list)
    for t in tables:
        tables_by_schema[t["schema"]].append(t)
    modules_by_schema = defaultdict(list)
    for m in modules:
        modules_by_schema[m["schema"]].append(m)

    counts = {}
    for s in schemas:
        c = dict(tables=len(tables_by_schema.get(s, [])), views=0, procs=0, funcs=0)
        for m in modules_by_schema.get(s, []):
            if m["type_desc"] == "VIEW":
                c["views"] += 1
            elif m["type_desc"] == "SQL_STORED_PROCEDURE":
                c["procs"] += 1
            elif m["type_desc"].endswith("FUNCTION"):
                c["funcs"] += 1
        counts[s] = c

    AUTO_SUBS = ("_schemas", "tables", "views", "procedures", "functions", "triggers")
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    for sub in AUTO_SUBS:
        p = VAULT_ROOT / sub
        p.mkdir(parents=True, exist_ok=True)
        for child in p.glob("*.md"):
            try:
                child.unlink()
            except PermissionError:
                pass

    written = 0
    (VAULT_ROOT / "index.md").write_text(render_index_md(schemas, counts), encoding="utf-8")
    written += 1
    (VAULT_ROOT / "ERD.md").write_text(render_erd_md(tables, all_fks), encoding="utf-8")
    written += 1

    for s in schemas:
        (VAULT_ROOT / "_schemas" / f"{s}.md").write_text(
            render_schema_md(s, tables_by_schema, modules_by_schema), encoding="utf-8")
        written += 1

    for t in tables:
        md = render_table_md(t, columns, pks, indexes, fks_by_parent, fks_by_ref, deps_in_map)
        (VAULT_ROOT / "tables" / f"{t['schema']}.{safe_filename(t['name'])}.md").write_text(
            md, encoding="utf-8")
        written += 1

    folder_map = {
        "VIEW": "views",
        "SQL_STORED_PROCEDURE": "procedures",
        "SQL_SCALAR_FUNCTION": "functions",
        "SQL_INLINE_TABLE_VALUED_FUNCTION": "functions",
        "SQL_TABLE_VALUED_FUNCTION": "functions",
        "SQL_TRIGGER": "triggers",
    }
    for m in modules:
        folder = folder_map.get(m["type_desc"], "objects")
        md = render_module_md(m, proc_params, deps_out, deps_in_map)
        (VAULT_ROOT / folder / f"{m['schema']}.{safe_filename(m['name'])}.md").write_text(
            md, encoding="utf-8")
        written += 1

    ddl = render_ddl(schemas, tables, columns, pks, indexes, all_fks, modules)
    DDL_OUT.parent.mkdir(parents=True, exist_ok=True)
    DDL_OUT.write_text(ddl, encoding="utf-8")

    print(f"Vault:    {VAULT_ROOT}")
    print(f"Archivos: {written} .md")
    print(f"DDL v3:   {DDL_OUT}")
    print(f"  Schemas: {len(schemas)}")
    print(f"  Tablas : {len(tables)}")
    print(f"  Vistas : {sum(1 for m in modules if m['type_desc']=='VIEW')}")
    print(f"  SPs    : {sum(1 for m in modules if m['type_desc']=='SQL_STORED_PROCEDURE')}")
    print(f"  Func.  : {sum(1 for m in modules if m['type_desc'].endswith('FUNCTION'))}")
    print(f"  Trigs. : {sum(1 for m in modules if m['type_desc']=='SQL_TRIGGER')}")


if __name__ == "__main__":
    main()
