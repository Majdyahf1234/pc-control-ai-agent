# Workspace Agent (Phase 2 scaffold)

See requirements.txt and run `python -m app.main` after venv install.
Press F12 to stop.


## Note (Phase 2.1)
If you see planner validation errors, update to Phase 2.1. This version forces args to be an object and auto-coerces common list forms.
\n\n## Phase 2.2\nPlanner now drops invalid/empty-arg steps (e.g., browser.search without query) and avoids web steps for file-only tasks.\n

## Phase 3 (Write summary)
Click **Execute** to read the file and write a summary next to it as `<original>_summary.txt`. The summary also appears in the UI.


## Phase 4 (Visible browser + Job collection)
Install Playwright browsers with: `python -m playwright install`.
This phase adds `resume.read` and `job.collect` to collect job postings and save `jobs_applied.json`.
It does NOT auto-submit applications yet.


## Phase 4.5 Stable Job Collector
This build uses visible Playwright and supports Bing + DuckDuckGo fallback, and decodes Bing redirect links correctly.

Run:
- `python -m venv .venv`
- `\.venv\Scripts\Activate.ps1`
- `pip install -r requirements.txt`
- `python -m playwright install`
- `python -m app.main`
