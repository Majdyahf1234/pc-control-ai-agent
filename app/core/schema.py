from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ToolName = Literal[
    "browser.open", "browser.search", "browser.extract", "browser.screenshot",
    "file.read", "file.write", "file.listdir", "file.apply_patch", "file.mkdir",
    "shell.run",
    "vscode.open_folder",
    "git.status", "git.diff", "git.commit", "git.push",
    "deploy.netlify", "resume.read", "job.collect"
]

class Step(BaseModel):
    id: str = Field(..., min_length=1)
    tool: ToolName
    args: Dict[str, Any] = Field(default_factory=dict)

class Plan(BaseModel):
    goal: str = Field(..., min_length=1)
    skill: str = Field(..., min_length=1)
    steps: List[Step] = Field(default_factory=list)

class RunContext(BaseModel):
    task: str
    plan: Optional[Plan] = None
    logs: List[str] = Field(default_factory=list)
