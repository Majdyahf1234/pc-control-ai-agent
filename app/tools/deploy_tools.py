from __future__ import annotations

from typing import Dict, Any
from ..core.permissions import Permissions

def netlify_deploy(project_dir: str, perms: Permissions) -> Dict[str, Any]:
    # Stub: left as a manual step for now to keep the app free/offline.
    if not perms.allow_deploy:
        raise RuntimeError("Deploy tool not allowed.")
    perms.assert_path_allowed(project_dir)
    return {"ok": False, "message": "Netlify deploy is not implemented in this build."}
