"""
LeakLens Unified Service Launcher.
Starts the FastAPI Backend (port 8000) and Streamlit Frontend (port 8501).
"""

import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

def run_all():
    print("=" * 65)
    print("  LeakLens - Explainable Revenue & Operational Risk Monitor")
    print("  Track: Business - 'The Money Leak' (Datathon 2026)")
    print("=" * 65)

    # 1. Start FastAPI Backend
    print("\n[1/2] Launching FastAPI Backend on http://localhost:8000 ...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "app:app",
        "--host", "0.0.0.0", "--port", "8000"
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(BACKEND_DIR))

    # Give backend 2 seconds to bind and load local analysis
    time.sleep(2.5)

    # 2. Start Streamlit Frontend
    print("[2/2] Launching Streamlit Frontend on http://localhost:8501 ...")
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501", "--server.headless", "true"
    ]
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(FRONTEND_DIR))

    print("\n" + "=" * 65)
    print("  ✅ BOTH LEAKLENS SERVICES ACTIVE!")
    print("  • Frontend Dashboard:     http://localhost:8501")
    print("  • FastAPI Swagger Docs:   http://localhost:8000/docs")
    print("  • FastAPI Health Probe:   http://localhost:8000/health")
    print("=" * 65)
    print("  Press Ctrl+C to terminate both services.\n")

    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down LeakLens services...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    run_all()
