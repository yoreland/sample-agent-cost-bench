#!/usr/bin/env python3
"""Build a static leaderboard page (index.html + data.json) from
agent-cost-bench result JSON files. Each entry is one CLI × model combination.

Usage: build.py OUT_DIR results1.json [results2.json ...]

Target display names are expected as "<Tool> · <Model>" (e.g. "Kiro · auto").
Only aggregate numbers are published (no transcripts, prompts or stdout).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HARD_TASKS = {"multitenant-rbac-api", "event-sourcing-cqrs"}

TOOLS = {
    "Kiro": dict(key="kiro", cost_note="credits × $0.04/credit 换算（每 credit 单价为假设值，取决于套餐）"),
    "Claude Code": dict(key="claude-code", cost_note="Claude Code 自报的 total_cost_usd（Bedrock 调用，按 CLI 内置价目计算）"),
    "Codex": dict(key="codex", cost_note="token 数 × OpenAI 官网标准价估算（经 Bedrock 调用，实际账单可能不同）"),
}
MODEL_NOTES = {
    ("Kiro", "auto"): "≈ Opus 4.8",
}


def split_target(target: str) -> tuple[str, str]:
    tool, _, model = target.partition(" · ")
    return tool.strip(), model.strip() or target


def main() -> None:
    out = Path(sys.argv[1])
    runs, run_ids, started = [], [], []
    for p in sys.argv[2:]:
        d = json.loads(Path(p).read_text())
        run_ids.append(d["run_id"])
        started.append(d["started_at"])
        for r in d["results"]:
            u = r.get("usage") or {}
            tool, model = split_target(r["target"])
            meta = TOOLS.get(tool, dict(key=tool.lower(), cost_note=""))
            # Agent time = CLI phase durations only (excludes pytest / judge
            # grading time that the harness adds to the wall clock).
            phases = [ph.get("duration_seconds") for ph in r.get("phase_results") or []
                      if ph.get("duration_seconds") is not None]
            agent_s = sum(phases) if phases else (u.get("wall_clock_seconds") or r.get("duration_seconds"))
            runs.append({
                "task": r["task_id"],
                "tier": "hard" if r["task_id"] in HARD_TASKS else "easy",
                "target": r["target"],
                "tool": tool,
                "model": model,
                "model_note": MODEL_NOTES.get((tool, model), ""),
                "key": meta["key"],
                "passed": r["status"] == "passed",
                "score": (r.get("scores") or {}).get("final"),
                "cost_usd": u.get("cost_usd"),
                "credits": u.get("raw_credits"),
                "seconds": agent_s,
                "reverified": bool(r.get("reverified")),
            })
    data = {
        "title": "Coding CLI × 模型 天梯",
        "generated_from": run_ids,
        "run_date": min(started)[:10],
        "tool_notes": {k: v["cost_note"] for k, v in TOOLS.items()},
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
