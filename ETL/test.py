"""Inspección manual de Bronce; importar este archivo no consulta SQL Server."""


def main():
    from config.conexion import obtener_engine
    from sqlalchemy import text
    import pandas as pd

    with obtener_engine().connect() as connection:
        df = pd.read_sql(text("SELECT TOP 5 * FROM Bronce.Censo_Plantas"), connection)
        print(df.columns.tolist())
        columnas = ['Plantas_Vivas_Raw', 'Plantas_Muertas_Raw', 'Total_Plantas_Raw']
        print(df[columnas].head() if 'Plantas_Vivas_Raw' in df.columns else "No Plantas_Vivas_Raw")
        df2 = pd.read_sql(text("SELECT TOP 1 * FROM Bronce.Base_Plantas_Area"), connection)
        print("Base_Plantas_Area columns:", df2.columns.tolist())


if __name__ == '__main__':
    main()
