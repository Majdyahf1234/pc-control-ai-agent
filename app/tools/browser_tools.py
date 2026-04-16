from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Any
from urllib.parse import quote_plus

from playwright.sync_api import (
    sync_playwright,
    Page,
    Browser,
    BrowserContext,
    TimeoutError as PWTimeoutError,
)
from ..core.kill_switch import check_stop


@dataclass
class BrowserSession:
    playwright: Any
    browser: Browser
    context: BrowserContext
    page: Page


class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._session: Optional[BrowserSession] = None

    def start(self) -> BrowserSession:
        if self._session:
            return self._session
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=self.headless)
        context = browser.new_context()
        page = context.new_page()
        self._session = BrowserSession(pw, browser, context, page)
        return self._session

    def stop(self):
        if not self._session:
            return
        try:
            self._session.context.close()
        except Exception:
            pass
        try:
            self._session.browser.close()
        except Exception:
            pass
        try:
            self._session.playwright.stop()
        except Exception:
            pass
        self._session = None

    def open(self, url: str, timeout_ms: int = 60000):
        check_stop()
        s = self.start()
        s.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        s.page.wait_for_timeout(1200)
        try:
            s.page.wait_for_load_state("networkidle", timeout=8000)
        except PWTimeoutError:
            pass

    def _extract_links(self, selector: str) -> List[str]:
        s = self.start()
        try:
            links = s.page.eval_on_selector_all(
                selector,
                "els => els.map(e => e.href).filter(Boolean)"
            )
            if isinstance(links, list):
                return [str(x) for x in links]
        except Exception:
            pass
        return []

    def search_bing(self, query: str, max_results: int = 10) -> List[str]:
        check_stop()
        s = self.start()

        q = quote_plus(query)
        s.page.goto(
            f"https://www.bing.com/search?q={q}",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        try:
            s.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except PWTimeoutError:
            pass

        s.page.wait_for_timeout(1200)

        links = self._extract_links("li.b_algo h2 a")
        if not links:
            links = self._extract_links("#b_results a")

        out: List[str] = []
        for u in links:
            if u and u not in out:
                out.append(u)
            if len(out) >= max_results:
                break
        return out

    def search_ddg(self, query: str, max_results: int = 10) -> List[str]:
        check_stop()
        s = self.start()

        q = quote_plus(query)
        s.page.goto(
            f"https://html.duckduckgo.com/html/?q={q}",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        try:
            s.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except PWTimeoutError:
            pass

        s.page.wait_for_timeout(1200)

        links = self._extract_links("a.result__a")

        out: List[str] = []
        for u in links:
            if u and u not in out:
                out.append(u)
            if len(out) >= max_results:
                break
        return out

    def extract_text(self, selector: str = "body") -> str:
        check_stop()
        s = self.start()

        try:
            s.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except PWTimeoutError:
            pass

        # Give dynamic pages a tiny moment before reading
        s.page.wait_for_timeout(400)

        try:
            el = s.page.query_selector(selector)
            if not el:
                return ""
            return el.inner_text() or ""
        except Exception:
            try:
                return s.page.content()
            except Exception:
                return ""
