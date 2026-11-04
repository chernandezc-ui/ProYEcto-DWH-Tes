"""
ACP Platform - Lanzador Unificado
Doble clic en INICIAR ACP.bat o ejecutar: python acp_start.py
"""

import argparse
import subprocess
import sys
import os
import time

import signal
import urllib.request
import urllib.error
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BG_BLUE = "\033[44m"

# ─── Configuración de servicios ──────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
SERVICIOS = []


def construir_servicios(config):
    """API y runner comparten Python, .env y dependencias; siguen aislados por proceso."""
    command = [sys.executable, '-m', 'uvicorn', 'main:aplicacion',
               '--host', config.host, '--port', str(config.puerto)]
    if config.reload:
        command.append('--reload')
    elif config.workers != 1:
        command.extend(['--workers', str(config.workers)])
    services = [{
        'nombre': 'Backend FastAPI', 'icono': '⚙', 'color': BLUE,
        'cmd': command,
        'cwd': BASE / 'backend',
        'health': f'http://127.0.0.1:{config.puerto}/health/live',
        'url': f'http://localhost:{config.puerto}/docs',
        'log': BASE / 'backend/logs/backend.stdout.log',
        'puerto': config.puerto, 'proceso': None,
    }]
    if config.runner_activo:
        if config.db_driver == 'ACP_OFFLINE_NO_DATABASE':
            raise ValueError('ACP_RUNNER_ACTIVO requiere configurar una conexión SQL Server real.')
        services.append({
            'nombre': 'Runner ETL', 'icono': '⚡', 'color': YELLOW,
            'cmd': [sys.executable, '-m', 'runner.runner'],
            'cwd': BASE / 'backend', 'health': None, 'url': None,
            'log': BASE / 'backend/logs/runner.stdout.log',
            'puerto': None, 'proceso': None,
        })
    return services


PROCESOS_ACTIVOS = []  # para cleanup en Ctrl+C

# ─── Helpers de UI ───────────────────────────────────────────────────────────

def banner(entorno):
    print(f"""
{BOLD}{BG_BLUE}                                                        {RESET}
{BOLD}{BG_BLUE}    ACP PLATFORM  -  Lanzador Unificado de Servicios    {RESET}
{BOLD}{BG_BLUE}                                                        {RESET}
{DIM}    Proyecto: ACP Data Warehouse | Entorno: {entorno}          {RESET}
""")


def linea(char="─", ancho=54):
    print(f"  {DIM}{char * ancho}{RESET}")


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg, nivel="INFO"):
    colores = {"INFO": GREEN, "WARN": YELLOW, "ERR": RED, "OK": GREEN}
    c = colores.get(nivel, WHITE)
    print(f"  {DIM}[{ts()}]{RESET} {c}{nivel:4}{RESET}  {msg}")
    _launcher_log.info(f"[{nivel}] {msg}")


def _crear_log_rotativo(ruta: Path):
    """Retorna un RotatingFileHandler para redirigir stdout/stderr del subproceso."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=ruta,
        maxBytes=50 * 1024 * 1024,   # 50 MB por archivo
        backupCount=10,
        encoding="utf-8",
    )
    return handler


# Logger del propio lanzador (separado de los subprocesos)
_launcher_log = logging.getLogger('acp_start')


def configurar_log_lanzador():
    directory = BASE / 'backend/logs'
    directory.mkdir(parents=True, exist_ok=True)
    _launcher_log.setLevel(logging.INFO)
    if not _launcher_log.handlers:
        handler = logging.handlers.RotatingFileHandler(
            directory / 'launcher.log', maxBytes=10 * 1024 * 1024,
            backupCount=5, encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        _launcher_log.addHandler(handler)


def puerto_en_uso(puerto: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def health_check(url: str, intentos: int = 1, timeout: float = 3.0) -> bool:
    """
    Hace un GET al endpoint de health.

    timeout=3.0s es el valor original — bajarlo a 1s causaba que el primer
    request a un servicio que está warming up (uvicorn/streamlit) abortara
    antes de leer la respuesta, dando falso TIMEOUT al cabo del ciclo completo.
    """
    for _ in range(intentos):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=timeout) as response:
                return response.status < 500
        except Exception:
            if intentos > 1:
                time.sleep(0.5)
    return False


# ─── Inicio de servicios ─────────────────────────────────────────────────────

def iniciar_servicio(svc: dict) -> bool:
    nombre = svc["nombre"]
    color  = svc["color"]

    # El lanzador solo administra sus propios procesos.
    if svc['puerto'] and puerto_en_uso(svc['puerto']):
        log(f"{nombre}: puerto ocupado. Cambia ACP_PUERTO en el .env global.", 'ERR')
        return False

    # Crear carpeta de logs
    svc["log"].parent.mkdir(parents=True, exist_ok=True)

    log(f"Iniciando  {color}{nombre}{RESET} ...", "INFO")

    # Abre el archivo de log con rotación (50 MB, 10 backups).
    # subprocess necesita un file object con fileno(), así que abrimos el
    # archivo subyacente del handler directamente.
    rot_handler = _crear_log_rotativo(svc["log"])
    rot_handler.stream.write(f"\n{'='*60}\n[{datetime.now()}] INICIO\n{'='*60}\n")
    rot_handler.stream.flush()
    log_file = rot_handler.stream

    proc = subprocess.Popen(
        svc["cmd"],
        cwd=str(svc["cwd"]),
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    svc["proceso"] = proc
    PROCESOS_ACTIVOS.append((proc, rot_handler))
    return True


def esperar_health(svc: dict, timeout: int = 30) -> bool:
    """
    Espera a que un servicio responda a su health URL.

    Polling progresivo: rápido al inicio (200ms) para no perder décimas
    cuando el servicio acaba de estar listo, más espaciado luego para no
    saturar (cada 1s tras 5s acumulados).
    """
    # Si `iniciar_servicio` falló (puerto bloqueado por otro user, etc.)
    # el proceso nunca se asignó. Abortar inmediatamente para no esperar
    # 35s polling un servidor que nunca va a aparecer.
    if svc["proceso"] is None:
        return False
    if not svc["health"]:
        time.sleep(2)
        return svc["proceso"] is not None and svc["proceso"].poll() is None

    inicio = time.perf_counter()
    deadline = inicio + timeout

    while True:
        if svc["proceso"] and svc["proceso"].poll() is not None:
            return False
        if health_check(svc["health"], intentos=1, timeout=2.5):
            return True

        ahora = time.perf_counter()
        if ahora >= deadline:
            return False

        # Polling progresivo: 200ms los primeros 3s, 500ms hasta 8s, luego 1s.
        transcurrido = ahora - inicio
        if transcurrido < 3:
            time.sleep(0.2)
        elif transcurrido < 8:
            time.sleep(0.5)
        else:
            time.sleep(1.0)


# ─── Dashboard de estado ─────────────────────────────────────────────────────

def mostrar_estado():
    linea()
    print(f"\n  {'SERVICIO':<20} {'ESTADO':<12} {'PID':<8} {'URL'}")
    linea()
    for svc in SERVICIOS:
        proc  = svc["proceso"]
        color = svc["color"]
        nombre = f"{svc['icono']} {svc['nombre']}"

        if proc is None:
            estado = f"{RED}DETENIDO{RESET}"
            pid    = "─"
            url    = "─"
        elif proc.poll() is not None:
            estado = f"{RED}CAIDO   {RESET}"
            pid    = str(proc.pid)
            url    = "─"
        else:
            alive  = svc["health"] is None or health_check(svc["health"])
            estado = f"{GREEN}ACTIVO  {RESET}" if alive else f"{YELLOW}INICIANDO{RESET}"
            pid    = str(proc.pid)
            url    = svc["url"] or "─"

        print(f"  {color}{nombre:<20}{RESET} {estado:<20} {DIM}{pid:<8}{RESET} {CYAN}{url}{RESET}")
    print()


# ─── Apagado limpio ──────────────────────────────────────────────────────────

def detener_todo():
    owned = list(PROCESOS_ACTIVOS)
    PROCESOS_ACTIVOS.clear()
    for proc, handler in owned:
        try:
            if proc.poll() is None:
                if sys.platform == 'win32':
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        finally:
            handler.close()
    if owned:
        log('Servicios detenidos.', 'OK')


def handler_sigint(sig, frame):
    print()
    log("Interrupción recibida (Ctrl+C)", "WARN")
    detener_todo()
    sys.exit(0)



# ─── Menú interactivo ────────────────────────────────────────────────────────

def menu():
    while True:
        linea()
        print(f"\n  {BOLD}Comandos:{RESET}  "
              f"{GREEN}[S]{RESET} Status   "
              f"{BLUE}[L]{RESET} Logs   "
              f"{YELLOW}[R]{RESET} Restart   "
              f"{RED}[Q]{RESET} Salir\n")
        try:
            cmd = input(f"  {BOLD}>{RESET} ").strip().upper()
        except EOFError:
            cmd = "Q"

        if cmd == "S":
            mostrar_estado()
        elif cmd == "L":
            mostrar_logs()
        elif cmd == "R":
            log("Reiniciando servicios...", "WARN")
            detener_todo()
            PROCESOS_ACTIVOS.clear()
            for svc in SERVICIOS:
                svc["proceso"] = None
            time.sleep(2)
            arrancar_servicios()
        elif cmd == "Q":
            detener_todo()
            print(f"\n  {DIM}Hasta luego.{RESET}\n")
            sys.exit(0)
        else:
            print(f"  {DIM}Comando no reconocido.{RESET}")


def mostrar_logs(lineas: int = 15):
    for svc in SERVICIOS:
        color = svc["color"]
        print(f"\n  {color}── {svc['nombre']} ──{RESET}")
        if svc["log"].exists():
            try:
                with open(svc["log"], encoding="utf-8", errors="replace") as f:
                    todas = f.readlines()
                    for l in todas[-lineas:]:
                        print(f"  {DIM}{l.rstrip()}{RESET}")
            except Exception as e:
                print(f"  {RED}Error leyendo log: {e}{RESET}")
        else:
            print(f"  {DIM}(sin log todavía){RESET}")


# ─── Flujo principal ─────────────────────────────────────────────────────────

def arrancar_servicios():
    api = SERVICIOS[0]
    if not iniciar_servicio(api) or not esperar_health(api):
        log('El backend no inició; revisar backend/logs/backend.stdout.log.', 'ERR')
        return False
    for service in SERVICIOS[1:]:
        ready = {**api, 'health': api['health'].replace('/health/live', '/health/ready')}
        if not esperar_health(ready):
            log('SQL Server no está listo; el runner no se inicia.', 'ERR')
            return False
        if not iniciar_servicio(service) or not esperar_health(service):
            log('El runner no inició; revisar backend/logs/runner.stdout.log.', 'ERR')
            return False
    mostrar_estado()
    return True


def main():
    parser = argparse.ArgumentParser(description='Arranque único de API y runner con el .env global.')
    parser.add_argument('--comprobar', action='store_true', help='Arrancar, comprobar y cerrar los servicios propios')
    parser.add_argument('--sin-interaccion', action='store_true', help='Mantener servicios activos sin menú')
    args = parser.parse_args()
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.prefix == sys.base_prefix:
        python = BASE / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.exists():
            print('Primero ejecuta: python instalar.py')
            return 1
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

    from backend.nucleo.settings import settings

    try:
        services = construir_servicios(settings)
    except ValueError as error:
        print(str(error))
        return 1
    SERVICIOS[:] = services
    configurar_log_lanzador()
    signal.signal(signal.SIGINT, handler_sigint)
    signal.signal(signal.SIGTERM, handler_sigint)
    banner(settings.entorno)
    try:
        if not arrancar_servicios():
            return 1
        if args.comprobar:
            return 0
        if args.sin_interaccion:
            while all(proc.poll() is None for proc, _ in PROCESOS_ACTIVOS):
                time.sleep(0.5)
            return 1
        menu()
    finally:
        detener_todo()


if __name__ == '__main__':
    raise SystemExit(main())
