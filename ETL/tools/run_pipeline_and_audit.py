import subprocess
import sys

def main():
    print("=== INICIANDO REPROCESO DE TODAS LAS TABLAS SILVER ===")
    res = subprocess.run([sys.executable, "pipeline.py", "--modo-ejecucion", "facts"], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("ERRORES PIPELINE:", res.stderr)
    
    print("\n\n=== INICIANDO AUDITORIA FINAL ===")
    res_audit = subprocess.run([sys.executable, "tools/check_nulls.py"], capture_output=True, text=True)
    print(res_audit.stdout)
    if res_audit.stderr:
        print("ERRORES AUDITORIA:", res_audit.stderr)

if __name__ == "__main__":
    main()
