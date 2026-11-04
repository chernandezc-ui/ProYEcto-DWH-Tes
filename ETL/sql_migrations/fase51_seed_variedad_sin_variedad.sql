/*
================================================================================
 fase51_seed_variedad_sin_variedad.sql
================================================================================
 Crea el registro centinela Silver.Dim_Variedad.ID_Variedad = -1 ('SIN_VARIEDAD').

 Motivo: Bronce.Censo_Plantas no declara variedad en ~86% de sus filas
 (un censo cuenta plantas por estado; la variedad es opcional). Antes el loader
 rechazaba esas 30k+ filas por "Variedad sin match", perdiendo todo el censo.
 Con este centinela, las filas sin variedad declarada se etiquetan como
 SIN_VARIEDAD en vez de descartarse; las que SÍ traen variedad sin match en el
 catálogo siguen yendo a cuarentena (gap de homologación real).

 Convención consistente con el DWH (Dim_Personal ya usa ID = -1 'Sin Evaluador').
 Idempotente: no duplica si ya existe.
================================================================================
*/
SET NOCOUNT ON;

IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Variedad WHERE ID_Variedad = -1)
BEGIN
    SET IDENTITY_INSERT Silver.Dim_Variedad ON;

    INSERT INTO Silver.Dim_Variedad
        (ID_Variedad, Nombre_Variedad, Es_Activa, Fecha_Creacion)
    VALUES
        (-1, 'SIN_VARIEDAD', 0, SYSDATETIME());

    SET IDENTITY_INSERT Silver.Dim_Variedad OFF;

    PRINT '[fase51] Centinela ID_Variedad=-1 (SIN_VARIEDAD) creado.';
END
ELSE
    PRINT '[fase51] Centinela ID_Variedad=-1 ya existe. Nada que hacer.';
