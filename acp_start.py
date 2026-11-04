"""
ACP Platform - Lanzador Unificado
Doble clic en acp_start.bat o ejecutar: python acp_start.py
"""

import subprocess
import sys
import os
import time

from dotenv import load_dotenv
import signal
import threading
import urllib.request
import urllib.error
import webbrowser
import ctypes
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

# ─── Colores ANSI ───────────────────────────────────────────────────────────
# Activar colores en Windows 10+
if sys.platform == "win32":
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )
    sys.stdout.reconfigure(encoding='utf-8')

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
BASE = Path(__file__).parent
VENV = BASE / ".venv" / "Scripts"

# Puertos por defecto alejados de 8000/8501 (muy usados por otras apps).
load_dotenv(BASE / "backend" / ".env")
load_dotenv(BASE / ".env")
_PUERTO_BACKEND = int(os.getenv("ACP_PUERTO", "8810"))
# Portal NextJS (reemplaza el Streamlit legacy de acp_mdm_portal).
# Override con ACP_NEXTJS_PORT si el 3000 está ocupado por otro proyecto.
_PUERTO_NEXTJS = int(os.getenv("ACP_NEXTJS_PORT", "3000"))
_DIR_NEXTJS = BASE / "Portal_MDM_NEXTJS" / "Portal-Nextjs" / "portal-mdm"

SERVICIOS = [
    {
        "nombre":   "Backend FastAPI",
        "icono":    "⚙",
        "cmd":      [str(VENV / "uvicorn.exe"), "main:aplicacion",
                     "--host", "0.0.0.0", "--port", str(_PUERTO_BACKEND)],
        "cwd":      BASE / "backend",
        "health":   f"http://127.0.0.1:{_PUERTO_BACKEND}/health/live",
        "url":      f"http://localhost:{_PUERTO_BACKEND}/docs",
        # IMPORTANTE: nombre distinto del log interno del backend
        # (backend/nucleo/logging.py escribe a backend/logs/backend.log con
        # RotatingFileHandler). Compartir archivo causa file-locking en
        # Windows y el backend nunca llega a inicializarse.
        "log":      BASE / "backend" / "logs" / "backend.stdout.log",
        "puerto":   _PUERTO_BACKEND,
        "color":    BLUE,
        "proceso":  None,
    },
    {
        "nombre":   "Runner ETL",
        "icono":    "⚡",
        "cmd":      [str(VENV / "python.exe"), "-m", "runner.runner"],
        "cwd":      BASE / "backend",
        "health":   None,
        "url":      None,
        "log":      BASE / "backend" / "logs" / "runner.stdout.log",
        "puerto":   None,
        "color":    YELLOW,
        "proceso":  None,
    },
    {
        "nombre":   "Portal NextJS",
        "icono":    "🌐",
        # Invocamos directamente `node` con el entrypoint JS de Next en
        # vez de `npm run dev`. Evita la capa intermedia de cmd.exe que
        # rompe la propagación de CTRL_BREAK_EVENT al apagar.
        "cmd":      ["node",
                     str(_DIR_NEXTJS / "node_modules" / "next" / "dist" / "bin" / "next"),
                     "dev", "-p", str(_PUERTO_NEXTJS)],
        "cwd":      _DIR_NEXTJS,
        # NextJS no expone /health en dev. El root sirve como liveness:
        # devuelve 200 (página) o 307/308 (redirect a /login según RBAC),
        # ambos < 500.
        "health":   f"http://127.0.0.1:{_PUERTO_NEXTJS}/",
        "url":      f"http://localhost:{_PUERTO_NEXTJS}",
        "log":      BASE / "backend" / "logs" / "portal-nextjs.stdout.log",
        "puerto":   _PUERTO_NEXTJS,
        "color":    CYAN,
        "proceso":  None,
    },
]

PROCESOS_ACTIVOS = []  # para cleanup en Ctrl+C

# ─── Helpers de UI ───────────────────────────────────────────────────────────

def limpiar():
    os.system("cls" if sys.platform == "win32" else "clear")


def banner():
    print(f"""
{BOLD}{BG_BLUE}                                                        {RESET}
{BOLD}{BG_BLUE}    ACP PLATFORM  -  Lanzador Unificado de Servicios    {RESET}
{BOLD}{BG_BLUE}                                                        {RESET}
{DIM}    Proyecto: ACP Data Warehouse | Entorno: DEV          {RESET}
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
_DIR_LOGS_LAUNCHER = BASE / "backend" / "logs"
_DIR_LOGS_LAUNCHER.mkdir(parents=True, exist_ok=True)
_launcher_log = logging.getLogger("acp_start")
_launcher_log.setLevel(logging.INFO)
if not _launcher_log.handlers:
    _h = logging.handlers.RotatingFileHandler(
        filename=_DIR_LOGS_LAUNCHER / "launcher.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _launcher_log.addHandler(_h)


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
            req = urllib.request.urlopen(url, timeout=timeout)
            return req.status < 500
        except Exception:
            if intentos > 1:
                time.sleep(0.5)
    return False


# ─── Inicio de servicios ─────────────────────────────────────────────────────

def _pid_en_puerto(puerto: int) -> str | None:
    """Devuelve el PID (como str) que escucha en el puerto, o None."""
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if f":{puerto} " in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                if pid.isdigit() and pid != "0":
                    return pid
    except Exception:
        pass
    return None


def _liberar_puerto(puerto: int) -> tuple[bool, str | None]:
    """
    Intenta matar el proceso huérfano que ocupa el puerto.

    Retorna (liberado, pid_intentado). `liberado=False` puede pasar si el
    proceso corre con privilegios distintos (SYSTEM, admin) y taskkill
    no tiene permisos. En ese caso el caller debe abortar, NO continuar
    como si todo estuviera bien.
    """
    pid = _pid_en_puerto(puerto)
    if pid is None:
        return True, None
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/PID", pid],
            capture_output=True,
            text=True,
        )
        time.sleep(0.5)
        # Verificar que realmente murió — taskkill puede retornar 0 y dejar
        # el proceso vivo si el SO lo respawnea, o retornar !=0 silenciosamente
        # cuando no hay permisos.
        if _pid_en_puerto(puerto) == pid:
            log(
                f"Falló taskkill PID {pid} en puerto {puerto}"
                f" (rc={r.returncode}): {r.stderr.strip() or r.stdout.strip()}",
                "ERR",
            )
            return False, pid
        log(f"Proceso huérfano {pid} en puerto {puerto} terminado", "WARN")
        return True, pid
    except Exception as exc:
        log(f"Excepción liberando puerto {puerto}: {exc}", "ERR")
        return False, pid


def iniciar_servicio(svc: dict) -> bool:
    nombre = svc["nombre"]
    color  = svc["color"]

    # Verificar si puerto ya está en uso; si es así, liberar el proceso huérfano.
    # Si NO logramos liberar (perms insuficientes, respawn), abortamos este
    # servicio — antes retornábamos True silenciosamente y la app simulaba
    # estar corriendo, lo que enmascaraba el fallo y daba 0 trazas.
    if svc["puerto"] and puerto_en_uso(svc["puerto"]):
        liberado, pid_intentado = _liberar_puerto(svc["puerto"])
        if not liberado:
            log(
                f"{color}{nombre}{RESET}  puerto {svc['puerto']} ocupado por PID"
                f" {pid_intentado} y NO se pudo liberar. Pasos a probar:",
                "ERR",
            )
            log(
                f"  1) Abrir PowerShell como Administrador y correr:"
                f"  Stop-Process -Id {pid_intentado} -Force",
                "ERR",
            )
            log(
                f"  2) O cambiar el puerto del servicio en .env"
                f" (var de entorno asociada)",
                "ERR",
            )
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


def esperar_health_paralelo(servicios: list[dict], timeout: int = 35) -> dict[str, bool]:
    """
    Lanza health checks de todos los servicios en paralelo.

    Imprime el resultado de cada uno en orden tan pronto como termina,
    así la salida sigue siendo legible. El tiempo total = max(tiempos)
    en lugar de sum(tiempos) que es lo que daba el bucle secuencial.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Pre-imprime la línea de espera para cada servicio (en orden).
    for svc in servicios:
        nombre = svc["nombre"]
        color = svc["color"]
        print(
            f"  {DIM}         Esperando {color}{nombre}{RESET}"
            f"{DIM} (max {timeout}s)...{RESET}"
        )

    resultados: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=len(servicios)) as pool:
        inicios = {svc["nombre"]: time.perf_counter() for svc in servicios}
        futuros = {pool.submit(esperar_health, svc, timeout): svc for svc in servicios}
        for fut in as_completed(futuros):
            svc = futuros[fut]
            ok = False
            try:
                ok = fut.result()
            except Exception as exc:
                log(f"Error en health check de {svc['nombre']}: {exc}", "ERR")
            resultados[svc["nombre"]] = ok
            secs = time.perf_counter() - inicios[svc["nombre"]]
            estado = (
                f"{GREEN}OK ({secs:.1f}s){RESET}"
                if ok
                else (
                    f"{RED}FALLO{RESET}"
                    if svc["proceso"] and svc["proceso"].poll() is not None
                    else f"{YELLOW}TIMEOUT ({secs:.1f}s){RESET}"
                )
            )
            print(f"  {DIM}         → {svc['color']}{svc['nombre']}{RESET}  {estado}")
    return resultados


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
    log("Deteniendo todos los servicios...", "INFO")
    for proc, handler in PROCESOS_ACTIVOS:
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        finally:
            try:
                handler.close()
            except Exception:
                pass
    log("Servicios detenidos.", "OK")


def handler_sigint(sig, frame):
    print()
    log("Interrupción recibida (Ctrl+C)", "WARN")
    detener_todo()
    sys.exit(0)


signal.signal(signal.SIGINT, handler_sigint)

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
    print()
    for svc in SERVICIOS:
        iniciar_servicio(svc)

    print()
    linea()
    print(f"  {BOLD}Verificando health checks (en paralelo)...{RESET}\n")

    resultados = esperar_health_paralelo(SERVICIOS, timeout=35)

    print()
    linea()
    print()
    mostrar_estado()

    # Abrir navegador solo si los servicios críticos levantaron
    if resultados.get("Backend FastAPI") and resultados.get("Portal NextJS"):
        log("Abriendo navegador...", "INFO")
        time.sleep(1)
        webbrowser.open(f"http://localhost:{_PUERTO_NEXTJS}")
    elif resultados.get("Backend FastAPI"):
        webbrowser.open(f"http://localhost:{_PUERTO_BACKEND}/docs")
    else:
        log("Algunos servicios no respondieron. Revisa los logs.", "WARN")


def main():
    limpiar()
    banner()

    # Verificar que el venv existe
    if not VENV.exists():
        print(f"  {RED}ERROR: No se encontró el entorno virtual en:{RESET}")
        print(f"  {DIM}{VENV}{RESET}")
        print(f"\n  {YELLOW}Crea el venv con:{RESET}  python -m venv .venv")
        print(f"  {YELLOW}Instala deps con:{RESET}   .venv\\Scripts\\pip install -r requirements.txt\n")
        input("  Presiona Enter para salir...")
        sys.exit(1)

    # Verificar .env
    env_raiz = BASE / ".env"
    if not env_raiz.exists():
        log("Archivo .env no encontrado en la raíz del proyecto.", "WARN")

    log("Iniciando ACP Platform...", "INFO")
    print()

    arrancar_servicios()
    menu()


if __name__ == "__main__":
    main()
