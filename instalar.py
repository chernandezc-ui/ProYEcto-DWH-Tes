"""Una instalación Python para API, runner, ETL y pruebas; usa solo stdlib."""

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
import venv

RAIZ = Path(__file__).resolve().parent


def python_compartido():
    if sys.prefix != sys.base_prefix:
        return Path(sys.executable)
    directory = RAIZ / '.venv'
    executable = directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not executable.exists():
        venv.EnvBuilder(with_pip=True).create(directory)
    return executable


def crear_env_si_falta():
    destination = RAIZ / '.env'
    content = (RAIZ / '.env.example').read_text(encoding='utf-8')
    content = content.replace('ACP_JWT_SECRETO=\n', f'ACP_JWT_SECRETO={secrets.token_urlsafe(48)}\n')
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
        file.write(content)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-index', action='store_true', help='Usar solo paquetes ya disponibles, sin consultar registros')
    args = parser.parse_args()
    python = str(python_compartido())
    command = [python, '-m', 'pip', 'install', '-r', str(RAIZ / 'requirements.txt')]
    if args.no_index:
        command.append('--no-index')
    subprocess.run(command, check=True, cwd=RAIZ)
    subprocess.run([python, '-m', 'pip', 'check'], check=True, cwd=RAIZ)
    created = crear_env_si_falta()
    print('.env global creado para desarrollo sin BD.' if created else '.env global existente conservado.')
    print('Instalación compartida lista. Iniciar con este Python:')
    print(f'  "{python}" "{RAIZ / "acp_start.py"}"')


if __name__ == '__main__':
    main()
