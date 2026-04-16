from __future__ import annotations
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QFont

class LogView(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

    def append_line(self, line: str):
        self.append(line)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
