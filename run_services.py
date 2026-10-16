import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'

def terminate(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

def run_all():
    print('=' * 65)
    print('  LeakLens - Explainable Revenue & Operational Risk Monitor')
    print("  Track: Business - 'The Money Leak' (Datathon 2026)")
    print('=' * 65)
    backend_proc = None
    frontend_proc = None
    try:
        print('\n[1/2] Launching FastAPI Backend on http://localhost:8000 ...')
        backend_proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '0.0.0.0', '--port', '8000'], cwd=str(BACKEND_DIR))
        backend_ready = False
        for _ in range(40):
            if backend_proc.poll() is not None:
                raise RuntimeError(f'FastAPI backend exited with code {backend_proc.returncode} before becoming ready.')
            try:
                with urlopen('http://127.0.0.1:8000/health', timeout=1.0) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                    if payload.get('status') == 'ok' and payload.get('analysis_loaded'):
                        backend_ready = True
                        break
            except (URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(0.5)
        if not backend_ready:
            raise RuntimeError('FastAPI backend did not become ready within 20 seconds.')
        print('[2/2] Launching Streamlit Frontend on http://localhost:8501 ...')
        frontend_proc = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.port', '8501', '--server.headless', 'true'], cwd=str(FRONTEND_DIR))
        print('\n' + '=' * 65)
        print('  BOTH LEAKLENS SERVICES ACTIVE')
        print('  Frontend Dashboard:   http://localhost:8501')
        print('  FastAPI Swagger Docs: http://localhost:8000/docs')
        print('  Health Probe:         http://localhost:8000/health')
        print('  Press Ctrl+C to terminate both services.')
        print('=' * 65 + '\n')
        while True:
            if backend_proc.poll() is not None:
                raise RuntimeError(f'FastAPI backend stopped unexpectedly with code {backend_proc.returncode}.')
            if frontend_proc.poll() is not None:
                raise RuntimeError(f'Streamlit frontend stopped unexpectedly with code {frontend_proc.returncode}.')
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\nShutting down LeakLens services...')
    finally:
        terminate(frontend_proc)
        terminate(backend_proc)
if __name__ == '__main__':
    run_all()
