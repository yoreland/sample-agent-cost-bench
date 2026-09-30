#!/usr/bin/env python3
"""Generate the CLI × model matrix configs (one per task batch)."""
import sys
from pathlib import Path

import yaml

KIRO_ARGS = ["chat", "--agent-engine", "v3", "--no-interactive", "--trust-all-tools",
             "--model={model}", "--effort={effort}", "--output-format", "stream-json"]
CC_ARGS = ["-p", "{prompt}", "--output-format", "json", "--model", "{model}",
           "--dangerously-skip-permissions", "--effort", "{effort}"]
CODEX_ARGS = ["exec", "--json", "--ephemeral", "--skip-git-repo-check",
              "--dangerously-bypass-approvals-and-sandbox",
              "-c", 'model_provider="amazon-bedrock"',
              "-c", 'model_providers.amazon-bedrock.aws.region="us-east-1"',
              "-c", 'model_reasoning_effort="{effort}"',
              "-m", "{model}", "{prompt}"]

M = 1e-6  # per-1M → per-token
CODEX_PRICES = {  # OpenAI standard short-context list prices (USD / 1M), 2026-09
    "openai.gpt-6.1-sol":  dict(i=2.00,  c=0.10, w=2.50,  o=10.00),
    "openai.gpt-6-astra":  dict(i=10.00, c=1.00, w=12.50, o=50.00),
    "openai.gpt-6-luna":   dict(i=0.10,  c=0.01, w=0.125, o=0.50),
}

runners = []
for slug, model, label in [
    ("kiro-auto", "auto", "Kiro · auto"),
    ("kiro-opus-5-5", "claude-opus-5.5", "Kiro · Opus 5.5"),
    ("kiro-opus-5", "claude-opus-5", "Kiro · Opus 5"),
    ("kiro-gpt-5-6-sol", "gpt-5.6-sol", "Kiro · GPT-5.6 Sol"),
]:
    runners.append(dict(name=slug, display_name=label, cli_path="kiro-cli", model_id=model,
                        pricing=dict(usd_per_credit=0.02), cli_base_args=KIRO_ARGS))
for slug, model, label in [
    ("cc-opus-5-5", "us.anthropic.claude-opus-5-5", "Claude Code · Opus 5.5"),
    ("cc-sonnet-5-5", "global.anthropic.claude-sonnet-5-5", "Claude Code · Sonnet 5.5"),
]:
    runners.append(dict(name=slug, display_name=label, cli_path="claude", model_id=model,
                        cli_base_args=CC_ARGS))
for slug, model, label in [
    ("codex-gpt-6-1-sol", "openai.gpt-6.1-sol", "Codex · GPT-6.1 Sol"),
    ("codex-gpt-6-astra", "openai.gpt-6-astra", "Codex · GPT-6 Astra"),
    ("codex-gpt-6-luna", "openai.gpt-6-luna", "Codex · GPT-6 Luna"),
]:
    p = CODEX_PRICES[model]
    runners.append(dict(name=slug, display_name=label, cli_path="codex", model_id=model,
                        pricing=dict(usd_per_input_token=p["i"] * M,
                                     usd_per_cached_input_token=p["c"] * M,
                                     usd_per_cache_write_token=p["w"] * M,
                                     usd_per_output_token=p["o"] * M),
                        cli_base_args=CODEX_ARGS))

BATCHES = {
    "A": ["rest-api", "log-analyzer-cli", "note-cli"],
    "B1": ["event-sourcing-cqrs"],
    "B2": ["multitenant-rbac-api"],
}
out = Path(__file__).parent
for name, tasks in BATCHES.items():
    cfg = dict(
        comparison_label="CLI × Model matrix",
        runners=runners,
        tasks_dir="/projects/sandbox/sample-agent-cost-bench/tasks",
        task_ids=tasks, modes=["vibe"],
        judge_cli_path="kiro-cli", judge_model="auto", judge_weight=0.6,
        concurrency="per_target", timeout_minutes=20, repeats=1,
        functional_pass_threshold=0.99,
        workspace_base=f"/projects/sandbox/bench-local/matrix/ws-{name}",
        devin_permissions_file="",
        output_dir="/projects/sandbox/bench-local/matrix/results",
        report_title=f"CLI × Model matrix — batch {name}", open_report=False,
    )
    (out / f"config.{name}.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    print("wrote", out / f"config.{name}.yaml", len(runners), "runners ×", len(tasks), "tasks")
