from __future__ import annotations
import os
from dataclasses import dataclass, asdict, field
from typing import List, Dict
from .constants import EXEC_PLAN_ONLY
from .errors import PermissionError

@dataclass
class Permissions:
    allowed_roots: List[str] = field(default_factory=list)
    allow_browser: bool = True
    allow_files: bool = True
    allow_shell: bool = False
    allow_vscode: bool = True
    allow_git: bool = False
    allow_deploy: bool = False
    exec_mode: str = EXEC_PLAN_ONLY

    def normalize(self):
        self.allowed_roots = [os.path.abspath(p.strip()) for p in self.allowed_roots if p.strip()]
        self.allowed_roots = sorted(list(dict.fromkeys(self.allowed_roots)))

    def assert_path_allowed(self, path: str):
        self.normalize()
        ap = os.path.abspath(path)
        for root in self.allowed_roots:
            rootn = root.rstrip("\\/")
            if ap == rootn or ap.startswith(rootn + os.sep):
                return
        raise PermissionError(f"Path not allowed by permissions: {ap}")

    def assert_tool_allowed(self, tool: str):
        if tool.startswith("browser.") and not self.allow_browser:
            raise PermissionError("Browser tool not allowed.")
        if tool.startswith("file.") and not self.allow_files:
            raise PermissionError("File tool not allowed.")
        if tool.startswith("shell.") and not self.allow_shell:
            raise PermissionError("Shell tool not allowed.")
        if tool.startswith("vscode.") and not self.allow_vscode:
            raise PermissionError("VS Code tool not allowed.")
        if tool.startswith("git.") and not self.allow_git:
            raise PermissionError("Git tool not allowed.")
        if tool.startswith("deploy.") and not self.allow_deploy:
            raise PermissionError("Deploy tool not allowed.")

    def to_dict(self) -> Dict:
        self.normalize()
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> "Permissions":
        p = Permissions(**(d or {}))
        p.normalize()
        return p
