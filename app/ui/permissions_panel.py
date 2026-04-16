from __future__ import annotations
import os
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit, QGroupBox, QGridLayout, QCheckBox, QComboBox
from ..core.permissions import Permissions
from ..core.constants import EXEC_PLAN_ONLY, EXEC_STEP, EXEC_AUTO

class PermissionsPanel(QWidget):
    changed = Signal()

    def __init__(self, perms: Permissions):
        super().__init__()
        self.perms = perms
        root = QVBoxLayout(self)

        roots_box = QGroupBox("Allowed root folders")
        roots_layout = QVBoxLayout(roots_box)
        self.roots_list = QListWidget()
        for p in self.perms.allowed_roots:
            self.roots_list.addItem(p)
        roots_layout.addWidget(self.roots_list)

        row = QHBoxLayout()
        self.inp_root = QLineEdit()
        self.inp_root.setPlaceholderText(r"Example: C:\Projects")
        self.btn_add = QPushButton("Add")
        self.btn_remove = QPushButton("Remove selected")
        row.addWidget(self.inp_root, 1)
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        roots_layout.addLayout(row)
        self.btn_add.clicked.connect(self.add_root)
        self.btn_remove.clicked.connect(self.remove_selected)
        root.addWidget(roots_box)

        tools_box = QGroupBox("Allowed capabilities")
        grid = QGridLayout(tools_box)
        self.chk_browser = QCheckBox("Browser (Playwright)")
        self.chk_files = QCheckBox("Files")
        self.chk_shell = QCheckBox("Shell")
        self.chk_vscode = QCheckBox("VS Code")
        self.chk_git = QCheckBox("Git")
        self.chk_deploy = QCheckBox("Deploy (Netlify)")
        self.chk_browser.setChecked(self.perms.allow_browser)
        self.chk_files.setChecked(self.perms.allow_files)
        self.chk_shell.setChecked(self.perms.allow_shell)
        self.chk_vscode.setChecked(self.perms.allow_vscode)
        self.chk_git.setChecked(self.perms.allow_git)
        self.chk_deploy.setChecked(self.perms.allow_deploy)
        for i, w in enumerate([self.chk_browser, self.chk_files, self.chk_shell, self.chk_vscode, self.chk_git, self.chk_deploy]):
            grid.addWidget(w, i // 2, i % 2)
            w.stateChanged.connect(self.sync)
        root.addWidget(tools_box)

        exec_box = QGroupBox("Execution mode")
        exec_layout = QHBoxLayout(exec_box)
        exec_layout.addWidget(QLabel("Mode:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Plan only", EXEC_PLAN_ONLY)
        self.cmb_mode.addItem("Step-by-step", EXEC_STEP)
        self.cmb_mode.addItem("Auto-run", EXEC_AUTO)
        idx = self.cmb_mode.findData(self.perms.exec_mode)
        if idx >= 0:
            self.cmb_mode.setCurrentIndex(idx)
        self.cmb_mode.currentIndexChanged.connect(self.sync)
        exec_layout.addWidget(self.cmb_mode, 1)
        root.addWidget(exec_box)
        root.addStretch(1)

    def add_root(self):
        p = self.inp_root.text().strip()
        if not p:
            return
        ap = os.path.abspath(p)
        if ap not in self.perms.allowed_roots:
            self.perms.allowed_roots.append(ap)
            self.perms.normalize()
            self.roots_list.addItem(ap)
            self.inp_root.setText("")
            self.changed.emit()

    def remove_selected(self):
        row = self.roots_list.currentRow()
        if row < 0:
            return
        item = self.roots_list.takeItem(row)
        if item:
            val = item.text()
            self.perms.allowed_roots = [r for r in self.perms.allowed_roots if r != val]
            self.perms.normalize()
            self.changed.emit()

    def sync(self):
        self.perms.allow_browser = self.chk_browser.isChecked()
        self.perms.allow_files = self.chk_files.isChecked()
        self.perms.allow_shell = self.chk_shell.isChecked()
        self.perms.allow_vscode = self.chk_vscode.isChecked()
        self.perms.allow_git = self.chk_git.isChecked()
        self.perms.allow_deploy = self.chk_deploy.isChecked()
        self.perms.exec_mode = self.cmb_mode.currentData()
        self.changed.emit()
