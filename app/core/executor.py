from __future__ import annotations

import os
import json
import base64
from typing import Callable, Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs, unquote

from .schema import Plan
from .permissions import Permissions
from .kill_switch import check_stop
from .errors import ExecutionStopped
from .llm import summarize_text, extract_profile_and_targets, extract_job_cards
from ..tools.file_tools import read_text, write_text, listdir, mkdir, apply_patch
from ..tools.resume_tools import read_resume_text
from ..tools.browser_tools import BrowserManager
from ..tools import vscode_tools


def summary_output_path(src_path: str) -> str:
    base, ext = os.path.splitext(src_path)
    if not ext:
        ext = ".txt"
    return f"{base}_summary{ext}"


def jobs_output_path(save_dir: str) -> str:
    return os.path.join(save_dir, "jobs_applied.json")


def _b64_urlsafe_decode(s: str) -> str:
    s = s.strip()
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    data = base64.urlsafe_b64decode((s + pad).encode("utf-8"))
    return data.decode("utf-8", errors="replace")


def _maybe_decode_bing_u_param(u: str) -> str:
    if not u:
        return u
    u = unquote(u)

    if u.startswith("http://") or u.startswith("https://"):
        return u

    # Bing marker
    if u.startswith("a1"):
        u = u[2:]

    try:
        decoded = _b64_urlsafe_decode(u)
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
    except Exception:
        pass

    return u


def _unwrap_bing_redirect(url: str) -> str:
    try:
        if "bing.com/ck/" not in url:
            return url
        qs = parse_qs(urlparse(url).query)
        if "u" in qs and qs["u"]:
            return _maybe_decode_bing_u_param(qs["u"][0])
    except Exception:
        pass
    return url


def _unwrap_ddg_redirect(url: str) -> str:
    try:
        p = urlparse(url)
        if "duckduckgo.com" in p.netloc and p.path.startswith("/l/"):
            qs = parse_qs(p.query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])
    except Exception:
        pass
    return url


def _is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def execute_plan(plan: Plan, perms: Permissions, log: Callable[[str], None]) -> Dict[str, Any]:
    outputs: Dict[str, Any] = {
        "read_files": {},
        "summary": None,
        "summary_path": None,
        "jobs": [],
        "written_files": [],
        "dirs": [],
    }

    last_read_path: Optional[str] = None
    last_read_text: Optional[str] = None
    resume_text: Optional[str] = None

    browser = BrowserManager(headless=False)

    try:
        for step in plan.steps:
            try:
                check_stop()
                perms.assert_tool_allowed(step.tool)

                # ---- FILES ----
                if step.tool == "file.read":
                    path = step.args.get("path")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] file.read missing args.path")
                        continue
                    perms.assert_path_allowed(path)
                    log(f"[RUN] file.read {path}")
                    txt = read_text(path, perms=perms)
                    outputs["read_files"][path] = txt
                    last_read_path = path
                    last_read_text = txt
                    log(f"[OK] Read {len(txt)} chars")

                elif step.tool == "file.write":
                    path = step.args.get("path")
                    content = step.args.get("content", "")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] file.write missing args.path")
                        continue
                    if not isinstance(content, str):
                        content = str(content)
                    perms.assert_path_allowed(path)
                    log(f"[RUN] file.write {path}")
                    write_text(path, content, perms=perms)
                    outputs["written_files"].append(path)
                    log("[OK] Wrote file")

                elif step.tool == "file.mkdir":
                    path = step.args.get("path")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] file.mkdir missing args.path")
                        continue
                    perms.assert_path_allowed(path)
                    log(f"[RUN] file.mkdir {path}")
                    mkdir(path, perms=perms)
                    outputs["dirs"].append(path)
                    log("[OK] Directory ensured")

                elif step.tool == "file.apply_patch":
                    path = step.args.get("path")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] file.apply_patch missing args.path")
                        continue
                    content = step.args.get("content")
                    if content is None:
                        content = step.args.get("patch", "")
                    if not isinstance(content, str):
                        content = str(content)
                    perms.assert_path_allowed(path)
                    log(f"[RUN] file.apply_patch {path}")
                    apply_patch(path, content, perms=perms)
                    outputs["written_files"].append(path)
                    log("[OK] Patched file")

                elif step.tool == "file.listdir":
                    path = step.args.get("path")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] file.listdir missing args.path")
                        continue
                    perms.assert_path_allowed(path)
                    log(f"[RUN] file.listdir {path}")
                    items = listdir(path, perms=perms)
                    outputs["read_files"][f"listdir:{path}"] = "\n".join(items)
                    log(f"[OK] {len(items)} items")

                # ---- VS CODE ----
                elif step.tool == "vscode.open_folder":
                    path = step.args.get("path") or step.args.get("folder") or step.args.get("dir")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] vscode.open_folder missing args.path")
                        continue
                    perms.assert_path_allowed(path)
                    log(f"[RUN] vscode.open_folder {path}")
                    vscode_tools.open_folder(path, perms=perms)
                    log("[OK] VS Code/open-folder invoked")

                # ---- RESUME / JOBS ----
                elif step.tool == "resume.read":
                    path = step.args.get("path")
                    if not isinstance(path, str) or not path:
                        log("[ERROR] resume.read missing args.path")
                        continue
                    perms.assert_path_allowed(path)
                    log(f"[RUN] resume.read {path}")
                    resume_text = read_resume_text(path, perms=perms)
                    log(f"[OK] Resume loaded ({len(resume_text)} chars)")

                elif step.tool == "job.collect":
                    resume_path = step.args.get("resume_path", "")
                    email = step.args.get("email", "")
                    count = int(step.args.get("count", 10) or 10)
                    query = step.args.get("query", "")
                    save_dir = step.args.get("save_dir", "")

                    # Default query if planner omitted it
                    if not query:
                        goal_l = (plan.goal or "").lower()
                        if "backend" in goal_l:
                            query = "backend developer remote"
                        elif "full" in goal_l and "stack" in goal_l:
                            query = "full stack developer remote"
                        elif "react" in goal_l:
                            query = "react developer remote"
                        elif "vue" in goal_l:
                            query = "vue developer remote"
                        elif "frontend" in goal_l or "front end" in goal_l:
                            query = "frontend developer remote"
                        else:
                            query = "software engineer remote"
                        log(f"[WARN] job.collect missing args.query; using default: {query}")

                    # Save directory defaults
                    if save_dir:
                        perms.assert_path_allowed(save_dir)
                    else:
                        if isinstance(resume_path, str) and "\\" in resume_path:
                            save_dir = resume_path.rsplit("\\", 1)[0]
                        else:
                            save_dir = perms.allowed_roots[0] if getattr(perms, "allowed_roots", []) else os.path.expanduser("~")

                    # Load resume text if not already loaded
                    local_resume = resume_text
                    if not local_resume:
                        if isinstance(resume_path, str) and resume_path:
                            perms.assert_path_allowed(resume_path)
                            local_resume = read_resume_text(resume_path, perms=perms)
                        else:
                            local_resume = ""

                    log("[RUN] Extract profile from resume + task")
                    profile_json = extract_profile_and_targets(local_resume, task=plan.goal)
                    try:
                        profile = json.loads(profile_json)
                    except Exception:
                        profile = {}

                    links_all: List[str] = []
                    seen = set()

                    log(f"[RUN] Browser search (Bing): {query}")
                    for u in browser.search_bing(query=query, max_results=max(25, count * 6)):
                        if u and u not in seen:
                            seen.add(u)
                            links_all.append(u)

                    if len(links_all) < max(5, count):
                        log(f"[RUN] Browser search (DuckDuckGo): {query}")
                        for u in browser.search_ddg(query=query, max_results=max(25, count * 6)):
                            if u and u not in seen:
                                seen.add(u)
                                links_all.append(u)

                    normalized: List[str] = []
                    for u in links_all:
                        u2 = _unwrap_bing_redirect(u)
                        u2 = _unwrap_ddg_redirect(u2)
                        u2 = u2.strip()
                        if _is_http_url(u2) and u2 not in normalized:
                            normalized.append(u2)

                    preferred_domains = [
                        "remote.co",
                        "weworkremotely.com",
                        "remotive.com",
                        "workingnomads.com",
                        "remoteok.com",
                        "flexjobs.com",
                    ]

                    def score(u: str) -> int:
                        return 0 if any(d in u for d in preferred_domains) else 1

                    normalized.sort(key=score)

                    links = normalized[:max(0, count)]
                    log(f"[OK] Got {len(links)} links")

                    blocked = ["linkedin.com", "indeed.com", "glassdoor.com", "upwork.com"]
                    jobs: List[Dict[str, Any]] = []

                    for idx, url in enumerate(links):
                        check_stop()

                        if any(d in url for d in blocked):
                            log(f"[SKIP] blocked site: {url}")
                            continue

                        log(f"[RUN] Open {idx+1}/{len(links)}: {url}")
                        try:
                            browser.open(url)
                            txt = browser.extract_text("body")
                        except Exception as e:
                            log(f"[WARN] Failed to open/extract: {e}")
                            continue

                        if not txt or len(txt.strip()) < 50:
                            log("[WARN] Empty page text, skipping")
                            continue

                        try:
                            info = json.loads(extract_job_cards(txt))
                        except Exception:
                            info = {"company": "", "position": "", "location": "", "salary": "", "url_notes": ""}

                        info["url"] = url
                        jobs.append(info)
                        log(f"[OK] Parsed: {info.get('company','')} - {info.get('position','')}")

                        if len(jobs) >= count:
                            break

                    outputs["jobs"] = jobs
                    out_path = jobs_output_path(save_dir)
                    perms.assert_tool_allowed("file.write")
                    perms.assert_path_allowed(out_path)
                    write_text(out_path, json.dumps({"email": email, "profile": profile, "jobs": jobs}, indent=2), perms=perms)
                    log(f"[OK] Saved: {out_path}")
                    log("[NOTE] This build collects postings and writes a report. It does NOT auto-submit applications.")

                else:
                    log(f"[SKIP] {step.id}: {step.tool} (not implemented in this build)")

            except RuntimeError:
                raise ExecutionStopped("Stopped (F12).")

        # Optional summary mode (for file.read tasks)
        goal_l = (plan.goal or "").lower()
        should_summarize = ("summarize" in goal_l) or ("summary" in goal_l)

        if should_summarize and last_read_path and last_read_text is not None:
            try:
                check_stop()
                log("[RUN] summarize via Ollama")
                summary = summarize_text(last_read_text)
                outputs["summary"] = summary

                out_path = summary_output_path(last_read_path)
                perms.assert_tool_allowed("file.write")
                perms.assert_path_allowed(out_path)

                log(f"[RUN] file.write {out_path}")
                write_text(out_path, summary, perms=perms)
                outputs["summary_path"] = out_path
                log("[OK] Summary written")
            except RuntimeError:
                raise ExecutionStopped("Stopped (F12).")

        return outputs

    finally:
        try:
            browser.stop()
        except Exception:
            pass
