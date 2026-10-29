"""Prepare an isolated Python runtime before importing application dependencies."""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import venv

REQUIRED_MODULES = ('Cheetah', 'fastapi', 'uvicorn', 'sqlalchemy', 'greenlet',
                    'aiosqlite', 'pydantic', 'jinja2', 'PIL')

def missing_modules():
    return [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]

def ensure_runtime():
    """Create/reuse a venv, install missing requirements, then continue startup."""
    if os.environ.get('SICKSHIFT_NO_AUTO_INSTALL') == '1':
        return
    root = Path(__file__).resolve().parent
    if sys.prefix == sys.base_prefix:
        target = Path(os.environ.get('SICKSHIFT_VENV', str(root / '.venv'))).expanduser()
        python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.is_file():
            print('SickShift: preparing an isolated Python environment...', flush=True)
            try:
                venv.EnvBuilder(with_pip=True).create(target)
            except Exception as exc:
                raise SystemExit('Cannot create the Python environment. Check folder permissions and venv support. On Debian/Ubuntu, install python3-venv. On Windows/macOS, use a Python installation with venv and pip. No system packages were changed.\n' + str(exc)) from exc
        os.execv(str(python), [str(python), str(root / 'sickshift.py'), *sys.argv[1:]])
    missing = missing_modules()
    if not missing:
        return
    print('SickShift: installing missing Python packages (' + ', '.join(missing) + ')...', flush=True)
    try:
        if importlib.util.find_spec('pip') is None:
            subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                        '-r', str(root / 'requirements.txt'), '-r', str(root / 'requirements-dashboard.txt')], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit('Package installation could not finish. Check your internet connection, proxy, certificates and permissions, then run SickShift again. No global Python environment was modified.') from exc
    importlib.invalidate_caches()
    if missing_modules():
        raise SystemExit('Packages remain unavailable: ' + ', '.join(missing_modules()))
