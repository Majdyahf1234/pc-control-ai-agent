from __future__ import annotations
import os, json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMessageBox

from ..core.constants import APP_TITLE, SETTINGS_FILENAME, EXEC_PLAN_ONLY
from ..core.permissions import Permissions
from ..core.agent import Agent
from ..core.kill_switch import start_kill_switch, STOP_EVENT
from ..core.errors import PlannerError, PermissionError, ExecutionStopped

from .permissions_panel import PermissionsPanel
from .run_panel import RunPanel
from .log_view import LogView

def settings_path() -> str:
    return os.path.join(os.path.expanduser("~"), SETTINGS_FILENAME)

def load_permissions() -> Permissions:
    p = settings_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Permissions.from_dict(data.get("permissions", {}))
        except Exception:
            pass
    return Permissions()

def save_permissions(perms: Permissions) -> None:
    p = settings_path()
    obj = {"permissions": perms.to_dict()}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 860)

        self.perms = load_permissions()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.log_view = LogView()
        root.addWidget(self.log_view, 1)

        self.perms_panel = PermissionsPanel(self.perms)
        self.perms_panel.changed.connect(self.on_perms_changed)

        self.run_panel = RunPanel()
        self.run_panel.request_run.connect(self.on_request_run)

        self.tabs.addTab(self.perms_panel, "Permissions")
        self.tabs.addTab(self.run_panel, "Run")

        self.agent = Agent(perms=self.perms, log=self.log)

        start_kill_switch(on_trigger=self.on_kill_triggered)
        self.run_panel.btn_stop.clicked.connect(self.manual_stop)

        self.statusBar().showMessage("Ready. Press F12 anytime to stop.")

        self._save_timer = QTimer(self)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._autosave)
        self._save_timer.start()
        self._dirty = False

    def log(self, msg: str):
        self.log_view.append_line(msg)
        self.statusBar().showMessage(msg)

    def on_kill_triggered(self):
        self.log("STOP triggered (F12).")

    def manual_stop(self):
        STOP_EVENT.set()
        self.log("STOP triggered (button).")

    def on_perms_changed(self):
        self._dirty = True

    def _autosave(self):
        if not self._dirty:
            return
        try:
            save_permissions(self.perms)
            self._dirty = False
        except Exception as e:
            self.log(f"Failed to save settings: {e}")

    def on_request_run(self, task: str, skill_hint: str, do_execute: bool):
        if self.perms.exec_mode == EXEC_PLAN_ONLY:
            do_execute = False

        try:
            self.log("=== New Run ===")
            self.log(f"Task: {task}")
            self.log(f"Skill hint: {skill_hint}")
            self.log(f"Execution: {'execute' if do_execute else 'plan-only'}")

            # If user pressed Execute and Plan JSON box is non-empty, execute that plan exactly.
            if do_execute:
                plan_text = self.run_panel.txt_plan.toPlainText().strip()
                if plan_text:
                    import json
                    from ..core.schema import Plan, RunContext
                    from ..core.executor import execute_plan

                    self.log("State: EXECUTE (using Plan JSON from UI)")
                    plan_obj = json.loads(plan_text)
                    plan = Plan.model_validate(plan_obj)

                    outputs = execute_plan(plan=plan, perms=self.perms, log=self.log)
                    self.agent.last_outputs = outputs

                    ctx = RunContext(task=task)
                    ctx.plan = plan
                    self.run_panel.set_plan(plan)

                    summary = outputs.get("summary")
                    if isinstance(summary, str) and summary.strip():
                        self.run_panel.set_summary(summary)

                    sp = outputs.get("summary_path")
                    if sp:
                        self.log(f"Saved: {sp}")

                    self.log("Run complete.")
                    return

            # Otherwise: normal path (plan, and maybe execute)
            ctx = self.agent.run(task=task, skill_hint=skill_hint, do_execute=do_execute)

            if ctx.plan:
                self.run_panel.set_plan(ctx.plan)

            if do_execute and self.agent.last_outputs:
                summary = self.agent.last_outputs.get("summary")
                if isinstance(summary, str) and summary.strip():
                    self.run_panel.set_summary(summary)

                sp = self.agent.last_outputs.get("summary_path")
                if sp:
                    self.log(f"Saved: {sp}")

            self.log("Run complete.")
        except PlannerError as e:
            QMessageBox.critical(self, "Planner error", str(e))
            self.log(f"Planner error: {e}")
        except PermissionError as e:
            QMessageBox.critical(self, "Permission error", str(e))
            self.log(f"Permission error: {e}")
        except ExecutionStopped as e:
            self.log(str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.log(f"Error: {e}")
