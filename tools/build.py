#!/usr/bin/env python3
"""Build a static leaderboard page (index.html + data.json) from
agent-cost-bench result JSON files.

Usage: build.py OUT_DIR results1.json [results2.json ...]

Only aggregate numbers are published (no transcripts, prompts or stdout).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HARD_TASKS = {"multitenant-rbac-api", "event-sourcing-cqrs"}

# Short CLI key + how its cost figure was obtained (shown as a footnote badge).
CLI_META = {
    "Kiro": ("kiro", "按 credits × $0.04/credit 换算（假设值）"),
    "Claude Code": ("claude-code", "CLI 直接上报的 Bedrock 实际花费"),
    "Codex": ("codex", "按 token × OpenAI 官网 GPT-5.5 单价估算"),
}


def cli_of(target: str) -> tuple[str, str, str]:
    for name, (key, note) in CLI_META.items():
        if target.startswith(name):
            return name, key, note
    return target, target.lower(), ""


def main() -> None:
    out = Path(sys.argv[1])
    runs, run_ids, started = [], [], []
    for p in sys.argv[2:]:
        d = json.loads(Path(p).read_text())
        run_ids.append(d["run_id"])
        started.append(d["started_at"])
        for r in d["results"]:
            u = r.get("usage") or {}
            name, key, note = cli_of(r["target"])
            # Agent time = CLI phase durations only (excludes pytest / judge
            # grading time that the harness adds to the wall clock).
            phases = [p.get("duration_seconds") for p in r.get("phase_results") or []
                      if p.get("duration_seconds") is not None]
            agent_s = sum(phases) if phases else (u.get("wall_clock_seconds") or r.get("duration_seconds"))
            runs.append({
                "task": r["task_id"],
                "tier": "hard" if r["task_id"] in HARD_TASKS else "easy",
                "target": r["target"],
                "cli": name,
                "key": key,
                "cost_note": note,
                "passed": r["status"] == "passed",
                "score": (r.get("scores") or {}).get("final"),
                "cost_usd": u.get("cost_usd"),
                "credits": u.get("raw_credits"),
                "seconds": agent_s,
                "input_tokens": u.get("input_tokens"),
                "output_tokens": u.get("output_tokens"),
            })
    data = {
        "title": "Coding CLI 天梯：Kiro vs Claude Code vs Codex",
        "generated_from": run_ids,
        "run_date": min(started)[:10],
        "runs": runs,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tpl = (Path(__file__).parent / "template.html").read_text()
    (out / "index.html").write_text(
        tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    )
    (out / ".nojekyll").write_text("")
    print(f"wrote {out}/index.html with {len(runs)} runs")


if __name__ == "__main__":
    main()
