"""
ETL Notificador
===============
Puente entre el motor ETL y el Central Command del Backend.
Aisla las dependencias para evitar que errores en señales detengan la carga de datos.
"""
import sys
import os

def notificar_fin_tarea(sender: str, tabla: str, filas: int, mensaje: str = ""):
    """
    Intenta enviar una señal al Event Bus del backend. 
    Falla silenciosamente si el bus no está disponible.
    """
    try:
        # Añadir dinámicamente el path del backend para el bus
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
        if backend_path not in sys.path:
            sys.path.append(backend_path)
            
        from servicios.event_bus import bus
        
        bus.task_finished.send(
            sender, 
            tabla=tabla, 
            filas=filas, 
            mensaje=mensaje or f"Carga de {tabla} completada exitosamente."
        )
    except Exception as e:
        # En producción, solo logueamos que no se pudo notificar, pero NO lanzamos excepción.
        print(f"[Aviso] No se pudo emitir señal de auditoría: {e}")
