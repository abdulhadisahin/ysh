"""Run the portable Windows build with this exact Python interpreter."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
result = subprocess.run([
    "powershell.exe", "-ExecutionPolicy", "Bypass", "-File",
    str(repo / "build" / "build_exe.ps1"), "-PythonPath", sys.executable,
    *sys.argv[1:],
], cwd=repo)
raise SystemExit(result.returncode)
