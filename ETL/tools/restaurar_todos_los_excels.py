import os
import re
import shutil
from pathlib import Path

def restaurar_excels():
    procesados_dir = Path(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\procesados")
    entrada_dir = Path(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\entrada")
    
    print("=== RESTAURANDO ARCHIVOS EXCEL ÚNICOS DESDE PROCESADOS ===")
    
    # Patrón para identificar timestamps del cargador: _YYYYMMDD_HHMMSS
    patron_timestamp = re.compile(r'_\d{8}_\d{6}$')
    
    for subfolder in sorted(procesados_dir.iterdir()):
        if not subfolder.is_dir():
            continue
        
        # Agrupar archivos por su nombre base original (sin el timestamp que le añade el cargador)
        archivos_por_base = {}
        for f in subfolder.iterdir():
            if not f.is_file() or f.suffix.lower() != '.xlsx':
                continue
            
            # Limpiar nombre para quitar el timestamp de procesado
            stem = f.stem
            # El pipeline puede haber agregado múltiples timestamps si se corrió varias veces
            while True:
                match = patron_timestamp.search(stem)
                if match:
                    stem = stem[:match.start()]
                else:
                    break
            
            nombre_base = f"{stem}{f.suffix}"
            
            # Guardamos el archivo y nos quedamos con el que tenga la fecha de modificación más reciente
            if nombre_base not in archivos_por_base:
                archivos_por_base[nombre_base] = f
            else:
                # Si ya existe, nos quedamos con el más reciente
                if f.stat().st_mtime > archivos_por_base[nombre_base].stat().st_mtime:
                    archivos_por_base[nombre_base] = f
        
        if not archivos_por_base:
            continue
            
        # Carpeta destino en entrada
        dest_subfolder = entrada_dir / subfolder.name
        dest_subfolder.mkdir(parents=True, exist_ok=True)
        
        print(f"\nSubcarpeta: {subfolder.name}")
        for nombre_base, ruta_origen in archivos_por_base.items():
            dest_file = dest_subfolder / nombre_base
            shutil.copy2(ruta_origen, dest_file)
            print(f"  [COPIADO] {ruta_origen.name} -> {nombre_base} ({ruta_origen.stat().st_size / 1024:.1f} KB)")

if __name__ == '__main__':
    restaurar_excels()
