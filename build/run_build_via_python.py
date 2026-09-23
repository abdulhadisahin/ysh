from __future__ import annotations

import subprocess
import sys
from pathlib import Path

repo = Path(r"C:\Users\USER\Documents\Codex\2026-07-27\you-are-the-lead-software-engineer")
script = repo / "build" / "build_exe.ps1"

print(f"Running build script: {script}")
result = subprocess.run(
    ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script)],
    cwd=str(repo),
    text=True,
    capture_output=True,
)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

sys.exit(result.returncode)
