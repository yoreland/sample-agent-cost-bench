#!/usr/bin/env python3
"""Re-run functional verification for existing workspaces with the fixed
verifier (venv built from the harness's Python >=3.10 instead of PATH python3).

Writes <run_id>.reverified.json next to each input; the model outputs are not
regenerated. Only pytest/local-scored tasks are re-verified (rubric tasks keep
their judge scores).

Usage: reverify.py WS_ROOT results1.json [results2.json ...]
"""
import asyncio
import json
import shutil
import sys
from pathlib import Path

from agent_cost_bench.config import _load_task_config
from agent_cost_bench.evaluator.functional import FunctionalEvaluator

TASKS = Path("/projects/sandbox/sample-agent-cost-bench/tasks/vibe")


async def main(ws_root: Path, files: list[str]) -> None:
    for f in files:
        d = json.loads(Path(f).read_text())
        rid = d["run_id"]
        slug_by_target = {t["label"]: t["name"] for t in d["config"]["targets"]} \
            if "targets" in d.get("config", {}) else {}
        changed = 0
        for r in d["results"]:
            task = _load_task_config(TASKS / r["task_id"] / "task.yaml")
            if task.verify is None or task.verify.runner not in ("pytest", "local"):
                continue
            slug = slug_by_target.get(r["target"])
            ws = next(iter(ws_root.glob(f"*/{rid}_{r['task_id']}_{slug}")), None) if slug else None
            if ws is None:
                print("  !! workspace not found:", r["task_id"], r["target"]); continue
            for v in (".agent_cost_bench_venv", ".venv-verify"):
                shutil.rmtree(ws / v, ignore_errors=True)
            fr = await FunctionalEvaluator(task, ws).evaluate()
            old = r["scores"]["functional"]
            new_status = "passed" if fr.score >= task.functional_pass_threshold else "failed"
            if abs(old - fr.score) > 1e-9 or r["status"] != new_status:
                changed += 1
                print(f"  {r['task_id']:<22} {r['target']:<26} {old:.2f} -> {fr.score:.2f}  "
                      f"{r['status']} -> {new_status}  ({fr.summary})")
            import dataclasses; r["functional_result"] = json.loads(json.dumps(dataclasses.asdict(fr) if dataclasses.is_dataclass(fr) else vars(fr), default=str))
            r["scores"]["functional"] = fr.score
            r["scores"]["final"] = fr.score
            r["status"] = new_status
            r["reverified"] = True
        out = Path(f).with_suffix(".reverified.json")
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f"{rid}: {changed} result(s) changed -> {out.name}")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]), sys.argv[2:]))
