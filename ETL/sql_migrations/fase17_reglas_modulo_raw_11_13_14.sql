SET NOCOUNT ON;

DECLARE @reglas TABLE (
    Modulo_Raw NVARCHAR(50) NOT NULL,
    Modulo_Int INT NULL,
    SubModulo_Int INT NULL,
    Tipo_Conduccion NVARCHAR(50) NULL,
    Es_Test_Block BIT NOT NULL,
    Es_Activa BIT NOT NULL,
    Observacion NVARCHAR(300) NULL
);

INSERT INTO @reglas (
    Modulo_Raw,
    Modulo_Int,
    SubModulo_Int,
    Tipo_Conduccion,
    Es_Test_Block,
    Es_Activa,
    Observacion
)
VALUES
    (N'11.1', 11, 1, N'SUELO', 0, 1, N'Canonica Fase 17: 11.1 => Modulo 11 SubModulo 1 SUELO'),
    (N'11.2', 11, 2, N'MACETA', 0, 1, N'Canonica Fase 17: 11.2 => Modulo 11 SubModulo 2 MACETA'),
    (N'13.1', 13, 1, N'SUELO', 0, 1, N'Canonica Fase 17: 13.1 => Modulo 13 SubModulo 1 SUELO'),
    (N'13.2', 13, 2, N'MACETA', 0, 1, N'Canonica Fase 17: 13.2 => Modulo 13 SubModulo 2 MACETA'),
    (N'14.1', 14, 1, N'SUELO', 0, 1, N'Canonica Fase 17: 14.1 => Modulo 14 SubModulo 1 SUELO'),
    (N'14.2', 14, 2, N'MACETA', 0, 1, N'Canonica Fase 17: 14.2 => Modulo 14 SubModulo 2 MACETA');

MERGE MDM.Regla_Modulo_Raw AS destino
USING @reglas AS origen
    ON destino.Modulo_Raw = origen.Modulo_Raw
WHEN MATCHED THEN
    UPDATE SET
        destino.Modulo_Int = origen.Modulo_Int,
        destino.SubModulo_Int = origen.SubModulo_Int,
        destino.Tipo_Conduccion = origen.Tipo_Conduccion,
        destino.Es_Test_Block = origen.Es_Test_Block,
        destino.Es_Activa = origen.Es_Activa,
        destino.Fecha_Modificacion = SYSDATETIME(),
        destino.Observacion = origen.Observacion
WHEN NOT MATCHED BY TARGET THEN
    INSERT (
        Modulo_Raw,
        Modulo_Int,
        SubModulo_Int,
        Tipo_Conduccion,
        Es_Test_Block,
        Es_Activa,
        Fecha_Creacion,
        Fecha_Modificacion,
        Observacion
    )
    VALUES (
        origen.Modulo_Raw,
        origen.Modulo_Int,
        origen.SubModulo_Int,
        origen.Tipo_Conduccion,
        origen.Es_Test_Block,
        origen.Es_Activa,
        SYSDATETIME(),
        SYSDATETIME(),
        origen.Observacion
    );

SELECT
    Modulo_Raw,
    Modulo_Int,
    SubModulo_Int,
    Tipo_Conduccion,
    Es_Test_Block,
    Es_Activa,
    Observacion
FROM MDM.Regla_Modulo_Raw
WHERE Modulo_Raw IN (N'11.1', N'11.2', N'13.1', N'13.2', N'14.1', N'14.2')
ORDER BY Modulo_Int, SubModulo_Int, Modulo_Raw;