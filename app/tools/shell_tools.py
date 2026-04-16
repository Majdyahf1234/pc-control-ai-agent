from __future__ import annotations

import subprocess
from typing import List, Dict, Any
from ..core.permissions import Permissions

def run(cmd: List[str], cwd: str | None, perms: Permissions) -> Dict[str, Any]:
    if not perms.allow_shell:
        raise RuntimeError("Shell tool not allowed.")
    if cwd:
        perms.assert_path_allowed(cwd)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=False)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
