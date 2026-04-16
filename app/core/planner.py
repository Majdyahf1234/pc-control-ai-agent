from __future__ import annotations

import os
import json
import re
import requests
from typing import Any, Dict, List

from .schema import Plan
from .errors import PlannerError

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

# Very small sanitizer: ensure we always return a plan-shaped dict.
def _coerce_plan(obj: Any) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        return {"goal": "", "skill": "auto", "steps": []}
    goal = obj.get("goal") or ""
    skill = obj.get("skill") or "auto"
    steps = obj.get("steps") if isinstance(obj.get("steps"), list) else []
    cleaned: List[Dict[str, Any]] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        tool = s.get("tool")
        if not isinstance(tool, str):
            continue
        sid = s.get("id") if isinstance(s.get("id"), str) else f"step{len(cleaned)+1}"
        args = s.get("args") if isinstance(s.get("args"), dict) else {}
        cleaned.append({"id": sid, "tool": tool, "args": args})
    return {"goal": str(goal), "skill": str(skill), "steps": cleaned}

# --- DETERMINISTIC_JOB_PLAN (Phase 4.5.4) ---
import re

def _maybe_deterministic_job_plan(task: str):
    t = (task or "").strip()
    tl = t.lower()

    wants_jobs = any(k in tl for k in ["collect", "job", "jobs", "apply", "application", "applications"])
    if not wants_jobs:
        return None

    m = re.search(r'([A-Za-z]:\\[^"\n]+?\.(pdf|txt|md))', t, flags=re.IGNORECASE)
    if not m:
        return None
    resume_path = m.group(1)

    m2 = re.search(r'\b(\d{1,2})\b', t)
    count = int(m2.group(1)) if m2 else 10
    count = max(1, min(50, count))

    m3 = re.search(r'save (?:results )?to\s+([A-Za-z]:\\[^"\n]+)', t, flags=re.IGNORECASE)
    save_dir = m3.group(1).strip() if m3 else (resume_path.rsplit("\\", 1)[0])

    m4 = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', t)
    email = m4.group(0) if m4 else ""

    query = "frontend developer remote"
    if "backend" in tl:
        query = "backend developer remote"
    if "full" in tl and "stack" in tl:
        query = "full stack developer remote"
    if "react" in tl:
        query = "react developer remote"
    if "vue" in tl:
        query = "vue developer remote"

    return {
        "goal": f"Collect {count} job listings",
        "skill": "job_search",
        "steps": [
            {"id": "1", "tool": "resume.read", "args": {"path": resume_path}},
            {"id": "2", "tool": "job.collect", "args": {
                "resume_path": resume_path,
                "email": email,
                "count": count,
                "query": query,
                "save_dir": save_dir
            }}
        ]
    }
# --- END DETERMINISTIC_JOB_PLAN ---

# --- POSTPROCESS_JOB_PLAN (Phase 4.5.5) ---
def _postprocess_job_plan_dict(plan_dict: dict, task: str) -> dict:
    try:
        steps = plan_dict.get("steps") or []
        # detect resume path
        resume_path = ""
        for s in steps:
            if s.get("tool") in ("resume.read", "file.read"):
                p = (s.get("args") or {}).get("path") or ""
                if isinstance(p, str) and p:
                    resume_path = p
                    break

        # find job.collect
        for s in steps:
            if s.get("tool") == "job.collect":
                args = s.setdefault("args", {})
                # count
                c = args.get("count", 10)
                try:
                    args["count"] = int(c)
                except Exception:
                    args["count"] = 10
                # resume_path
                if not args.get("resume_path") and resume_path:
                    args["resume_path"] = resume_path
                # save_dir heuristic
                if not args.get("save_dir") and resume_path and "\\" in resume_path:
                    args["save_dir"] = resume_path.rsplit("\\", 1)[0]
                # email from task
                import re
                if not args.get("email"):
                    m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', task or "")
                    if m:
                        args["email"] = m.group(0)
                # query heuristic
                if not args.get("query"):
                    tl = (task or "").lower()
                    q = "frontend developer remote"
                    if "backend" in tl: q = "backend developer remote"
                    if "full" in tl and "stack" in tl: q = "full stack developer remote"
                    if "react" in tl: q = "react developer remote"
                    if "vue" in tl: q = "vue developer remote"
                    args["query"] = q
    except Exception:
        pass
    return plan_dict
# --- END POSTPROCESS_JOB_PLAN ---

# --- DETERMINISTIC_WEB_PLAN (Phase 5) ---
def _maybe_deterministic_web_plan(task: str):
    t = (task or "").strip()
    tl = t.lower()
    if not any(k in tl for k in ["web", "website", "web page", "webpage", "landing page"]):
        return None
    # find a base directory like C:\web or C:\something
    mdir = re.search(r'([A-Za-z]:\\[^"\n]+)', t)
    base_dir = mdir.group(1) if mdir else "C:\\web"
    # restaurant name
    mname = re.search(r'(?:named|called)\s+([A-Za-z0-9\- _]+)', t, flags=re.IGNORECASE)
    name = (mname.group(1).strip() if mname else "AL-Majd").strip()
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or "site"
    project_dir = base_dir.rstrip('\\') + "\\" + slug

    index_path = project_dir + "\\index.html"
    css_path = project_dir + "\\styles.css"
    js_path = project_dir + "\\script.js"

    # Simple modern template (offline, no assets)
    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{name} Restaurant</title>
  <link rel=\"stylesheet\" href=\"./styles.css\" />
</head>
<body>
  <header class=\"nav\">
    <div class=\"brand\">{name}</div>
    <nav class=\"links\">
      <a href=\"#menu\">Menu</a>
      <a href=\"#story\">Our Story</a>
      <a href=\"#gallery\">Gallery</a>
      <a class=\"cta\" href=\"#reserve\">Reserve</a>
    </nav>
  </header>

  <main>
    <section class=\"hero\">
      <div class=\"hero-inner\">
        <p class=\"tag\">Lebanese • Grill • Mezze</p>
        <h1>Warm hospitality, bold flavors, unforgettable nights.</h1>
        <p class=\"sub\">
          Experience authentic taste with a modern twist — fresh ingredients,
          open-fire grill, and mezze made to share.
        </p>
        <div class=\"hero-actions\">
          <a class=\"btn primary\" href=\"#reserve\">Book a table</a>
          <a class=\"btn\" href=\"#menu\">Explore menu</a>
        </div>

        <div class=\"cards\">
          <div class=\"card\">
            <h3>Open-Fire Grill</h3>
            <p>Charcoal classics with a perfect smoky finish.</p>
          </div>
          <div class=\"card\">
            <h3>Fresh Mezze</h3>
            <p>Made daily — hummus, moutabal, tabbouleh, and more.</p>
          </div>
          <div class=\"card\">
            <h3>Family Nights</h3>
            <p>Live music on weekends + set menus.</p>
          </div>
        </div>
      </div>
    </section>

    <section id=\"menu\" class=\"section\">
      <div class=\"section-head\">
        <h2>Signature Menu</h2>
        <p>Favorites our guests come back for.</p>
      </div>

      <div class=\"grid\">
        <article class=\"item\">
          <div>
            <h3>Majd Mixed Grill</h3>
            <p>Kofta, chicken tawook, lamb — charcoal grilled.</p>
          </div>
          <span class=\"price\">$18</span>
        </article>

        <article class=\"item\">
          <div>
            <h3>Classic Mezze Platter</h3>
            <p>Hummus, moutabal, vine leaves, labneh, olives.</p>
          </div>
          <span class=\"price\">$14</span>
        </article>

        <article class=\"item\">
          <div>
            <h3>{name} Shawarma</h3>
            <p>Slow roasted, garlic sauce, pickles, warm bread.</p>
          </div>
          <span class=\"price\">$9</span>
        </article>

        <article class=\"item\">
          <div>
            <h3>Pistachio Kunafa</h3>
            <p>Golden crust, soft cheese, rose syrup.</p>
          </div>
          <span class=\"price\">$7</span>
        </article>
      </div>
    </section>

    <section id=\"story\" class=\"section alt\">
      <div class=\"two-col\">
        <div>
          <h2>Our Story</h2>
          <p>
            {name} is built on simple things: generous plates, real ingredients,
            and a table that always feels like home.
          </p>
          <ul class=\"bullets\">
            <li>Fresh daily mezze</li>
            <li>Charcoal grill specialties</li>
            <li>Cozy, welcoming atmosphere</li>
          </ul>
        </div>
        <div class=\"photo\">
          <div class=\"photo-inner\">
            <p>“Come hungry. Leave happy.”</p>
          </div>
        </div>
      </div>
    </section>

    <section id=\"gallery\" class=\"section\">
      <div class=\"section-head\">
        <h2>Gallery</h2>
        <p>A peek at the vibe.</p>
      </div>
      <div class=\"gallery\">
        <div class=\"g g1\"></div>
        <div class=\"g g2\"></div>
        <div class=\"g g3\"></div>
        <div class=\"g g4\"></div>
        <div class=\"g g5\"></div>
      </div>
    </section>

    <section id=\"reserve\" class=\"section reserve\">
      <div class=\"reserve-card\">
        <h2>Reserve a Table</h2>
        <p>We’ll confirm in minutes.</p>
        <form id=\"form\">
          <div class=\"row\">
            <input name=\"name\" placeholder=\"Full name\" required />
            <input name=\"phone\" placeholder=\"Phone\" required />
          </div>
          <div class=\"row\">
            <input type=\"date\" name=\"date\" required />
            <input type=\"time\" name=\"time\" required />
          </div>
          <textarea name=\"notes\" placeholder=\"Notes (optional)\"></textarea>
          <button class=\"btn primary\" type=\"submit\">Request reservation</button>
          <p id=\"msg\" class=\"msg\"></p>
        </form>
      </div>
    </section>

    <footer class=\"footer\">
      <div>
        <strong>{name} Restaurant</strong>
        <p>Open daily • 12:00 — 23:00</p>
      </div>
      <div class=\"foot-links\">
        <a href=\"#\">Instagram</a>
        <a href=\"#\">Facebook</a>
        <a href=\"#\">Google Maps</a>
      </div>
    </footer>
  </main>

  <script src=\"./script.js\"></script>
</body>
</html>"""

    css = """:root{--bg:#0b0b10;--card:#12121a;--text:#f4f4f7;--muted:#b7b7c5;--line:rgba(255,255,255,.08);--accent:#ffb24a;--accent2:#ff5ea8}
*{box-sizing:border-box}html,body{height:100%}
body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;color:var(--text);
  background:radial-gradient(900px 500px at 10% 10%,rgba(255,178,74,.18),transparent 60%),
           radial-gradient(900px 500px at 90% 20%,rgba(255,94,168,.14),transparent 55%),
           radial-gradient(900px 600px at 50% 110%,rgba(120,170,255,.14),transparent 60%),var(--bg)}
a{color:inherit;text-decoration:none}
.section{padding:72px 20px;max-width:1100px;margin:0 auto}
.section.alt{background:rgba(255,255,255,.03);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin-bottom:22px}
.section-head h2{margin:0;font-size:32px}.section-head p{margin:0;color:var(--muted)}
.nav{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:14px 20px;
  backdrop-filter:blur(10px);background:rgba(11,11,16,.6);border-bottom:1px solid var(--line)}
.brand{font-weight:800;letter-spacing:.6px}
.links{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.links a{padding:8px 10px;border-radius:10px;color:var(--muted)}
.links a:hover{background:rgba(255,255,255,.06);color:var(--text)}
.links .cta{color:var(--text);border:1px solid var(--line)}
.hero{padding:64px 20px 26px;max-width:1100px;margin:0 auto}
.hero-inner{border:1px solid var(--line);background:rgba(255,255,255,.03);border-radius:22px;padding:38px;overflow:hidden}
.tag{display:inline-flex;gap:10px;align-items:center;padding:7px 12px;border-radius:999px;border:1px solid var(--line);color:var(--muted);margin:0 0 14px}
.hero h1{margin:0 0 12px;font-size:44px;line-height:1.05}
.sub{margin:0 0 18px;color:var(--muted);max-width:62ch}
.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 10px}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 14px;border-radius:14px;border:1px solid var(--line);
  background:rgba(255,255,255,.04);color:var(--text);cursor:pointer}
.btn:hover{background:rgba(255,255,255,.07)}
.btn.primary{border-color:rgba(255,178,74,.35);background:linear-gradient(135deg,rgba(255,178,74,.22),rgba(255,94,168,.14))}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:20px}
.card{border:1px solid var(--line);background:rgba(0,0,0,.18);border-radius:18px;padding:16px}
.card h3{margin:0 0 6px}.card p{margin:0;color:var(--muted);font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.item{display:flex;justify-content:space-between;gap:16px;border:1px solid var(--line);background:rgba(255,255,255,.03);border-radius:18px;padding:16px}
.item h3{margin:0 0 6px}.item p{margin:0;color:var(--muted);font-size:14px}
.price{font-weight:800;color:var(--accent);white-space:nowrap}
.two-col{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;align-items:stretch}
.bullets{margin:14px 0 0;padding-left:18px;color:var(--muted)}
.photo{border:1px solid var(--line);border-radius:22px;background:radial-gradient(500px 200px at 20% 20%,rgba(255,178,74,.18),transparent 65%),
  radial-gradient(500px 220px at 70% 60%,rgba(255,94,168,.16),transparent 60%),rgba(255,255,255,.03);overflow:hidden}
.photo-inner{height:100%;display:flex;align-items:flex-end;padding:18px}.photo-inner p{margin:0;color:var(--text);font-weight:700}
.gallery{display:grid;grid-template-columns:repeat(12,1fr);gap:12px}
.g{border:1px solid var(--line);border-radius:22px;min-height:140px;background:radial-gradient(220px 120px at 30% 20%,rgba(255,178,74,.18),transparent 60%),
  radial-gradient(240px 140px at 70% 70%,rgba(120,170,255,.18),transparent 60%),rgba(255,255,255,.03)}
.g1{grid-column:span 7;min-height:220px}.g2{grid-column:span 5;min-height:220px}
.g3{grid-column:span 4}.g4{grid-column:span 4}.g5{grid-column:span 4}
.reserve{padding-bottom:90px}
.reserve-card{max-width:760px;margin:0 auto;border:1px solid var(--line);background:rgba(255,255,255,.03);border-radius:22px;padding:22px}
.reserve-card h2{margin:0 0 6px}.reserve-card p{margin:0 0 12px;color:var(--muted)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
input,textarea{width:100%;padding:12px 12px;border-radius:14px;border:1px solid var(--line);background:rgba(0,0,0,.18);color:var(--text);outline:none}
textarea{min-height:96px;resize:vertical;margin-bottom:12px}
.msg{margin:12px 0 0;color:var(--muted);min-height:18px}
.footer{padding:26px 20px;border-top:1px solid var(--line);background:rgba(0,0,0,.14);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.footer p{margin:6px 0 0;color:var(--muted)}
.foot-links{display:flex;gap:12px;align-items:center}
.foot-links a{color:var(--muted)}.foot-links a:hover{color:var(--text)}
@media (max-width:860px){.cards{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.two-col{grid-template-columns:1fr}.hero h1{font-size:36px}
  .g1,.g2{grid-column:span 12}.g3,.g4,.g5{grid-column:span 12}.row{grid-template-columns:1fr}}
"""

    js = """const form=document.getElementById("form");
const msg=document.getElementById("msg");
form.addEventListener("submit",(e)=>{e.preventDefault();
  const data=Object.fromEntries(new FormData(form).entries());
  msg.textContent=`Thanks ${data.name}! Reservation requested for ${data.date} at ${data.time}. We'll confirm soon.`;
  form.reset();
});"""

    return {
        "goal": f"Create a restaurant website for {name} in {project_dir}",
        "skill": "web_build",
        "steps": [
            {"id": "1", "tool": "file.mkdir", "args": {"path": project_dir}},
            {"id": "2", "tool": "file.write", "args": {"path": index_path, "content": html}},
            {"id": "3", "tool": "file.write", "args": {"path": css_path, "content": css}},
            {"id": "4", "tool": "file.write", "args": {"path": js_path, "content": js}},
            {"id": "5", "tool": "vscode.open_folder", "args": {"path": project_dir}}
        ]
    }
# --- END DETERMINISTIC_WEB_PLAN ---

def generate_plan(task: str, skill_hint: str = "auto") -> Plan:
    url = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    system = (
        "You are a planning engine for a desktop agent.\n"
        "Return ONLY valid JSON with this exact shape:\n"
        "{ \"goal\": string, \"skill\": string, \"steps\": [{\"id\": string, \"tool\": string, \"args\": object}] }\n\n"
        "Rules:\n"
        "- args must be an object (dictionary), never a list.\n"
        "- Use only these tools:\n"
        "  file.read, file.write, file.listdir, file.mkdir, file.apply_patch,\n"
        "  resume.read, job.collect\n"
        "- If the task mentions a PDF resume path, use resume.read (NOT file.read).\n"
        "- If the task is about collecting jobs, output steps: resume.read then job.collect.\n"
        "- JSON only, no markdown.\n"
    )

    user = f"Task: {task}\nSkill hint: {skill_hint}\nReturn JSON only."

    try:
        r = requests.post(
            f"{url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "")
        # Extract JSON substring if the model wrapped text
        m = re.search(r"\{[\s\S]*\}$", content.strip())
        raw = m.group(0) if m else content.strip()
        obj = json.loads(raw)
        plan_obj = _coerce_plan(obj)
        return Plan.model_validate(plan_obj)
    except Exception as e:
        raise PlannerError(f"Planner failed: {e}")
