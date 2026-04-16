import os
import subprocess
from pathlib import Path

def _find_code_exe() -> str | None:
    candidates = [
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        str(Path.home() / r"AppData\Local\Programs\Microsoft VS Code\Code.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def open_folder(path: str) -> None:
    path = os.path.abspath(path)

    # 1) Try CLI if available
    try:
        subprocess.Popen(["code", path], shell=False)
        return
    except Exception:
        pass

    # 2) Try Code.exe direct
    code_exe = _find_code_exe()
    if code_exe:
        subprocess.Popen([code_exe, path], shell=False)
        return

    # 3) Final fallback: open folder in Explorer
    os.startfile(path)
