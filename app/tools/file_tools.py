from __future__ import annotations
import os
from typing import List
from ..core.permissions import Permissions

def read_text(path: str, perms: Permissions) -> str:
    perms.assert_path_allowed(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_text(path: str, content: str, perms: Permissions) -> None:
    perms.assert_path_allowed(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def listdir(path: str, perms: Permissions) -> List[str]:
    perms.assert_path_allowed(path)
    return os.listdir(path)


def mkdir(path: str, perms: Permissions) -> None:
    perms.assert_path_allowed(path)
    os.makedirs(path, exist_ok=True)


def apply_patch(path: str, content: str, perms: Permissions) -> None:
    """Simple patch: replace whole file content."""
    write_text(path, content, perms=perms)
