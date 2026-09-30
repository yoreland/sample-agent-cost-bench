"""Headless smoke test for the leaderboard page. Usage: smoke.py URL OUT_DIR"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for name, vp in (("desktop", (1280, 900)), ("mobile", (390, 844))):
        pg = b.new_page(viewport={"width": vp[0], "height": vp[1]})
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
        pg.goto(url, wait_until="networkidle")
        if name == "desktop":
            for tier in ("all", "easy", "hard"):
                pg.click(f'#tiers button[data-tier="{tier}"]')
                pg.wait_for_timeout(500)
                for board in ("cost", "speed"):
                    rows = pg.locator(f"#{board} .row").all_inner_texts()
                    print(f"[{tier}] {board}: {len(rows)} rows")
                    for r in rows:
                        print("    ", " ".join(r.split()))
                pg.screenshot(path=str(out / f"leaderboard-{tier}.png"), full_page=True)
            # tool filter: uncheck Codex -> ladders must drop its rows
            pg.click('#tiers button[data-tier="all"]')
            before = pg.locator("#cost .row").count()
            pg.uncheck('#tools input[value="Codex"]')
            pg.wait_for_timeout(300)
            after = pg.locator("#cost .row").count()
            print(f"tool filter: {before} -> {after} rows after unchecking Codex")
            if after >= before:
                errors.append("tool filter did not remove rows")
            pg.check('#tools input[value="Codex"]')
            pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(out / "leaderboard-expanded.png"), full_page=True)
        else:
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(out / "leaderboard-mobile.png"), full_page=True)
    b.close()
print("errors:", errors or "none")
sys.exit(1 if errors else 0)
