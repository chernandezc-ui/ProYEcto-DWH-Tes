from config.conexion import obtener_engine
from sqlalchemy import text
import pandas as pd

e = obtener_engine()
with e.connect() as c:
    df = pd.read_sql(text("SELECT TOP 5 * FROM Bronce.Censo_Plantas"), c)
    print(df.columns.tolist())
    print(df[['Plantas_Vivas_Raw', 'Plantas_Muertas_Raw', 'Total_Plantas_Raw']].head() if 'Plantas_Vivas_Raw' in df.columns else "No Plantas_Vivas_Raw")
    
    # Base area?
    df2 = pd.read_sql(text("SELECT TOP 1 * FROM Bronce.Base_Plantas_Area"), c)
    print("Base_Plantas_Area columns:", df2.columns.tolist())
