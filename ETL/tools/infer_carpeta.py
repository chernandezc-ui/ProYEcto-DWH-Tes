import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[3]))  # add project root

from bronce.rutas import _inferir_carpeta_por_archivo

file_name = 'Fenología de Producción Arándano - Campaña 2025.xlsx'
canon = _inferir_carpeta_por_archivo(file_name)
print('Inferred carpeta:', canon)
