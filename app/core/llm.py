from __future__ import annotations
import os
import requests
from dotenv import load_dotenv

from .constants import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL
from .errors import PlannerError

load_dotenv()

def ollama_chat(messages, timeout: int = 300) -> str:
    url = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    try:
        r = requests.post(
            f"{url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")
    except Exception as e:
        raise PlannerError(f"Ollama call failed: {e}")

def summarize_text(text: str, instructions: str = "") -> str:
    system = (
        "You are a careful summarizer. Summarize the provided text clearly and concisely. "
        "Preserve key points and any actionable items. Use bullet points when helpful."
    )
    user = f"{instructions}\n\nTEXT:\n{text}"
    return ollama_chat(
        [{"role":"system","content":system},{"role":"user","content":user}],
        timeout=300
    )


def extract_profile_and_targets(resume_text: str, task: str) -> str:
    system = (
        "Extract a job-search profile from the resume text and the user's task. "
        "Return ONLY JSON with keys: email, desired_roles (list), keywords (list), locations (list), seniority, notes. "
        "If email not present, set it to empty string."
    )
    user = f"TASK:\n{task}\n\nRESUME:\n{resume_text}"
    return ollama_chat([{"role":"system","content":system},{"role":"user","content":user}], timeout=300)

def extract_job_cards(page_text: str) -> str:
    system = (
        "Extract job posting fields from raw page text. Return ONLY JSON with keys: "
        "company, position, location, salary, url_notes."
    )
    user = f"PAGE TEXT:\n{page_text[:12000]}"
    return ollama_chat([{"role":"system","content":system},{"role":"user","content":user}], timeout=300)
