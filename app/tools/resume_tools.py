from __future__ import annotations
import os
from pypdf import PdfReader
from ..core.permissions import Permissions

def read_resume_text(path: str, perms: Permissions) -> str:
    perms.assert_path_allowed(path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    if ext == ".pdf":
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        return "\n".join(parts).strip()
    raise ValueError(f"Unsupported resume type: {ext}. Use .pdf or .txt/.md")
