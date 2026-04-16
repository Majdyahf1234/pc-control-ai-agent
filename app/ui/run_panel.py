from __future__ import annotations
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QMessageBox
)
from ..core.schema import Plan

class RunPanel(QWidget):
    request_run = Signal(str, str, bool)  # task, skill_hint, do_execute

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Skill hint:"))
        self.cmb_skill = QComboBox()
        self.cmb_skill.addItem("Auto", "auto")
        self.cmb_skill.addItem("Job search", "job_search")
        self.cmb_skill.addItem("Website builder", "website_builder")
        self.cmb_skill.addItem("Code fixer", "code_fixer")
        top.addWidget(self.cmb_skill, 1)

        self.btn_plan = QPushButton("Generate Plan")
        self.btn_run = QPushButton("Execute (read + write summary)")
        self.btn_stop = QPushButton("STOP (F12)")
        top.addWidget(self.btn_plan)
        top.addWidget(self.btn_run)
        top.addWidget(self.btn_stop)
        root.addLayout(top)

        root.addWidget(QLabel("Task"))
        self.txt_task = QTextEdit()
        self.txt_task.setPlaceholderText("Example: Read C:\\Projects\\test.txt and summarize it.")
        root.addWidget(self.txt_task, 2)

        root.addWidget(QLabel("Plan JSON"))
        self.txt_plan = QTextEdit()
        self.txt_plan.setPlaceholderText("Plan will appear here...")
        root.addWidget(self.txt_plan, 2)

        root.addWidget(QLabel("Summary (after Execute)"))
        self.txt_summary = QTextEdit()
        self.txt_summary.setPlaceholderText("Summary will appear here after Execute...")
        root.addWidget(self.txt_summary, 2)

        self.btn_plan.clicked.connect(self.on_plan)
        self.btn_run.clicked.connect(self.on_run)

    def on_plan(self):
        task = self.txt_task.toPlainText().strip()
        if not task:
            QMessageBox.information(self, "Missing task", "Please enter a task.")
            return
        self.request_run.emit(task, self.cmb_skill.currentData(), False)

    def on_run(self):
        task = self.txt_task.toPlainText().strip()
        if not task:
            QMessageBox.information(self, "Missing task", "Please enter a task.")
            return
        self.request_run.emit(task, self.cmb_skill.currentData(), True)

    def set_plan(self, plan: Plan):
        self.txt_plan.setPlainText(plan.model_dump_json(indent=2))

    def set_summary(self, summary: str):
        self.txt_summary.setPlainText(summary or "")
