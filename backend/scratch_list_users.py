import sys
sys.path.append('d:/Proyecto2026/ACP_DWH/ACP Proyecciones/backend')
from repositorios import repo_usuarios
try:
    for u in repo_usuarios.listar_usuarios():
        print(f"{u['nombre_usuario']} (Activo: {u['es_activo']})")
except Exception as e:
    print('Error:', e)
