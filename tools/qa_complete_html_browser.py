"""Check the complete reader in desktop and narrow Chromium viewports."""

import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/full"
HTML = BUILD / "html/index.html"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
assert CHROME.is_file()

report = {
    "schema": "openlogic-full-html-browser-qa/1",
    "html_sha256": hashlib.sha256(HTML.read_bytes()).hexdigest(),
    "browser": None,
    "viewports": [],
}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=str(CHROME), headless=True)
    report["browser"] = browser.version
    for label, width, height in (("desktop", 1280, 720), ("mobile", 390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height}, locale="mr-IN")
        page = context.new_page()
        console_errors = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        page.goto(HTML.as_uri(), wait_until="domcontentloaded", timeout=120000)
        page.evaluate("document.fonts.ready")
        measures = page.evaluate("""() => {
          const images = [...document.images];
          const glyphs = [...document.querySelectorAll('img.math-glyph')];
          const tables = [...document.querySelectorAll('table.proof-steps')];
          const overflowOffenders = [...document.querySelectorAll('body *')]
            .map(e => ({e, r: e.getBoundingClientRect()}))
            .filter(o => o.r.right > window.innerWidth + 1 && o.r.left < window.innerWidth)
            .sort((a,b) => b.r.right - a.r.right)
            .slice(0, 20).map(o => ({
              tag: o.e.tagName, class: o.e.getAttribute('class'), id: o.e.id,
              left: Math.round(o.r.left), right: Math.round(o.r.right),
              overflowX: getComputedStyle(o.e).overflowX,
              text: o.e.textContent.trim().slice(0, 90)
            }));
          return {
            document_width: document.documentElement.scrollWidth,
            viewport_width: document.documentElement.clientWidth,
            images: images.length,
            image_load_failures: images.filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src),
            math: document.querySelectorAll('math').length,
            proof_tables: tables.length,
            glyphs: glyphs.length,
            glyph_widths: glyphs.slice(0, 20).map(g => Math.round(g.getBoundingClientRect().width * 100) / 100),
            overflow_offenders: overflowOffenders,
            font_status: document.fonts.status,
            skip_target: !!document.querySelector('#main-content'),
          };
        }""")
        screenshot = BUILD / f"HTML_BROWSER_{label.upper()}.png"
        page.screenshot(path=str(screenshot))
        detail_screenshot = None
        if label == "desktop":
            glyph = page.locator("img.math-glyph").first
            glyph.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            detail_screenshot = BUILD / "HTML_BROWSER_MATH_GLYPH.png"
            page.screenshot(path=str(detail_screenshot))
        else:
            page.evaluate("""() => {
              const longMath = [...document.querySelectorAll('math')]
                .find(m => m.scrollWidth > m.clientWidth + 50);
              if (longMath) longMath.scrollIntoView({block:'center'});
            }""")
            page.wait_for_timeout(1000)
            detail_screenshot = BUILD / "HTML_BROWSER_WIDE_MATH.png"
            page.screenshot(path=str(detail_screenshot))
        measure = {"name": label, "width": width, "height": height, **measures,
                   "page_errors": console_errors, "screenshot": str(screenshot),
                   "detail_screenshot": str(detail_screenshot)}
        report["viewports"].append(measure)
        context.close()
    browser.close()

report["result"] = "pass" if all(
    row["document_width"] <= row["viewport_width"] + 1
    and row["images"] >= 138
    and not row["image_load_failures"]
    and row["math"] >= 38000
    and row["proof_tables"] == 466
    and row["glyphs"] >= 68 and all(width > 0 for width in row["glyph_widths"])
    and row["skip_target"]
    and not row["page_errors"]
    for row in report["viewports"]
) else "fail"
(BUILD / "HTML_BROWSER_QA.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    "result": report["result"],
    "viewports": [{k: row[k] for k in ("name", "document_width", "viewport_width", "images", "math", "proof_tables", "glyphs", "glyph_widths", "image_load_failures", "page_errors", "overflow_offenders")}
                  for row in report["viewports"]],
}, ensure_ascii=False))
