from __future__ import annotations
from typing import Callable
from .schema import RunContext
from .permissions import Permissions
from .planner import generate_plan
from .executor import execute_plan
from .kill_switch import reset_stop

class Agent:
    def __init__(self, perms: Permissions, log: Callable[[str], None]):
        self.perms = perms
        self.log = log
        self.last_outputs = None

    def run(self, task: str, skill_hint: str = "auto", do_execute: bool = False) -> RunContext:
        reset_stop()
        ctx = RunContext(task=task)

        self.log("State: PLAN")
        plan = generate_plan(task=task, skill_hint=skill_hint)
        ctx.plan = plan
        self.log(f"Plan skill={plan.skill}, steps={len(plan.steps)}")

        if not do_execute:
            self.log("Mode: Plan-only (no execution).")
            self.last_outputs = None
            return ctx

        self.log("State: EXECUTE (Phase 3)")
        self.last_outputs = execute_plan(plan=plan, perms=self.perms, log=self.log)
        if self.last_outputs and self.last_outputs.get("summary_path"):
            self.log(f"Output: summary written to {self.last_outputs['summary_path']}")
        self.log("State: REPORT (done)")
        return ctx
