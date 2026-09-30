"""Headless smoke test for the leaderboard page. Usage: smoke.py URL OUT_DIR"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for name, vp in (("desktop", (1200, 900)), ("mobile", (390, 844))):
        pg = b.new_page(viewport={"width": vp[0], "height": vp[1]})
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
        pg.goto(url, wait_until="networkidle")
        if name == "desktop":
            for tier in ("all", "easy", "hard"):
                pg.click(f'#tabs button[data-tier="{tier}"]')
                pg.wait_for_timeout(600)
                for board in ("cost", "speed"):
                    rows = pg.locator(f"#{board} .row").all_inner_texts()
                    print(f"[{tier}] {board}:", [" ".join(r.split()) for r in rows])
                pg.screenshot(path=str(out / f"leaderboard-{tier}.png"), full_page=True)
            pg.click('#tabs button[data-tier="all"]')
            pg.locator("details").nth(0).evaluate("d => d.open = true")
            pg.locator("details").nth(1).evaluate("d => d.open = true")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(out / "leaderboard-expanded.png"), full_page=True)
        else:
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(out / "leaderboard-mobile.png"), full_page=True)
    b.close()
print("errors:", errors or "none")
sys.exit(1 if errors else 0)
