"""Compatibility wrapper. Use the project-root run_services.py launcher."""

from pathlib import Path
import runpy

ROOT_LAUNCHER = Path(__file__).resolve().parents[1] / "run_services.py"
runpy.run_path(str(ROOT_LAUNCHER), run_name="__main__")
