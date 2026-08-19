#!/usr/bin/env python3
"""
dashboard.py — governance dashboard from Copilot usage metrics + hook traces

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 6 · Lab 6.6 (audit, metrics & cost)
How to run:
    python3 dashboard.py                                # shipped fixtures, console report
    python3 dashboard.py --hook-trace <labs-repo>/hook-trace.jsonl  # your own Lab 6.2 trace
    python3 dashboard.py --hook-trace fixtures/hook-trace-sample.jsonl
                                        # realistic Lab 6.2-shaped demo trace (14 gate
                                        # events) — use it when your own trace is empty
    python3 dashboard.py --html report.html             # also write an HTML report
    python3 dashboard.py --budget 4000 --total-prs 12   # tune assumptions

Inputs:
  --usage        NDJSON usage-metrics report (one JSON object per line).
                 Fixture: fixtures/sample-usage-metrics.ndjson (SYNTHETIC data —
                 shapes are the lesson, not magnitudes). The real source is the
                 Copilot usage metrics API (GA): NDJSON reports, 1-day and 28-day,
                 ~1-year retention, requires the metrics policy enabled. The
                 LEGACY Metrics API closed Apr 2026 — do not build on it. Adapt
                 field names to the live API schema when you wire real data.
  --hook-trace   JSONL from the Lab 6.2 audit hook (audit_log.py). labs-repo's
                 hook-trace.jsonl ships EMPTY — every event in yours is one your
                 own probes produced (that's the Lab 6.2/6.6 success bar);
                 fixtures/hook-trace-sample.jsonl is the instructor demo trace.
                 The trace exists
                 because GitHub's audit log does NOT capture client-side prompts
                 or tool calls — the trace is the compensating evidence, and the
                 agent-vs-human provenance source for ISO 26262 (see
                 traceability-log-schema.md).

Outputs: console report; optional single-file HTML (stdlib only, no secrets).
Metrics: credit spend (total/by user/by model) vs budget with 75/90/100% alerts;
% PRs with AI review; bugs caught pre-merge (blocker findings); gate blocks;
override rate on gated actions; agent-vs-human provenance counts.
"""

import argparse
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALERTS = (75, 90, 100)  # budget alert thresholds, per billing settings


def read_ndjson(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"{path.name}:{i}: not valid NDJSON (one JSON object per line): {e}")
    return rows


def analyze(usage: list[dict], trace: list[dict], budget: float, total_prs: int) -> dict:
    total_credits = sum(r.get("credits", 0.0) for r in usage)
    by_user = Counter()
    by_model = Counter()
    by_team = Counter()      # credits are POOLED — team attribution is our job
    by_feature = Counter()
    reviewed_prs, agent_prs = set(), set()
    blockers = 0
    for r in usage:
        by_user[r.get("login", "?")] += r.get("credits", 0.0)
        by_model[r.get("model", "?")] += r.get("credits", 0.0)
        by_team[r.get("team") or "unattributed"] += r.get("credits", 0.0)
        by_feature[r.get("feature", "?")] += r.get("credits", 0.0)
        if r.get("feature") == "code_review" and r.get("pr_number") is not None:
            reviewed_prs.add(r["pr_number"])
            blockers += r.get("blocker_findings") or 0
        if r.get("feature") == "coding_agent" and r.get("pr_number") is not None:
            agent_prs.add(r["pr_number"])

    pct_budget = (total_credits / budget * 100.0) if budget else 0.0
    fired = [t for t in ALERTS if pct_budget >= t]

    gates = [t for t in trace if t.get("verdict") in ("block", "ask")]
    blocks = [t for t in gates if t.get("verdict") == "block"]
    asks = [t for t in gates if t.get("verdict") == "ask"]
    # Override rate = of the ASK prompts a HUMAN actually decided, how many were
    # approved. Exclude asks with no `approved` field from the denominator — the
    # raw hook trace records the ask but not the human's outcome; CI/the harness
    # must backfill `approved` (see audit_log.py + the LIVE.md note). Counting an
    # undecided ask as a denial would understate trust.
    decided = [t for t in asks if t.get("approved") is not None]
    overridden = [t for t in decided if t.get("approved") is True]
    override_rate = (len(overridden) / len(decided) * 100.0) if decided else 0.0
    asks_undecided = len(asks) - len(decided)
    provenance = Counter(t.get("actor", "?") for t in trace)
    gate_names = Counter(t.get("gate", "?") for t in gates)

    return {
        "total_credits": total_credits,
        "budget": budget,
        "pct_budget": pct_budget,
        "alerts_fired": fired,
        "by_user": by_user.most_common(),
        "by_model": by_model.most_common(),
        "by_team": by_team.most_common(),
        "by_feature": by_feature.most_common(),
        "reviewed_prs": len(reviewed_prs),
        "agent_prs": len(agent_prs),
        "total_prs": total_prs,
        "pct_prs_ai_review": (len(reviewed_prs) / total_prs * 100.0) if total_prs else 0.0,
        "bugs_pre_merge": blockers,
        "gate_events": len(gates),
        "blocks": len(blocks),
        "asks": len(asks),
        "asks_undecided": asks_undecided,
        "override_rate": override_rate,
        "gate_names": gate_names.most_common(),
        "provenance": provenance.most_common(),
        "trace_events": len(trace),
    }


def bar(pct: float, width: int = 30) -> str:
    filled = min(width, round(pct / 100 * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:5.1f}%"


def print_report(a: dict) -> None:
    print("=" * 62)
    print(" Copilot governance dashboard — Session 6 · Lab 6.6")
    print("=" * 62)

    print("\n-- FinOps: AI-credit spend (pooled; 1 credit = $0.01) --")
    print(f"  total: {a['total_credits']:,.0f} of {a['budget']:,.0f} credits  "
          + bar(a["pct_budget"]))
    for t in ALERTS:
        state = "FIRED" if t in a["alerts_fired"] else "ok"
        print(f"  alert @{t:>3}%: {state}")
    print("\n  by user (spend attribution):")
    for user, c in a["by_user"]:
        print(f"    {user:<12} {c:9,.0f}  ({c / a['total_credits'] * 100:4.1f}%)")
    print("  by model:")
    for model, c in a["by_model"]:
        print(f"    {model:<20} {c:9,.0f}")

    print("\n-- Quality signals --")
    print(f"  PRs with AI review:   {a['reviewed_prs']}/{a['total_prs']} "
          f"({a['pct_prs_ai_review']:.0f}%)")
    print(f"  bugs caught pre-merge (blocker findings): {a['bugs_pre_merge']}")
    print(f"  agent-authored PRs (coding agent): {a['agent_prs']}")

    print("\n-- Gate activity (from hook trace; the audit-gap compensator) --")
    print(f"  trace events: {a['trace_events']}   gate events: {a['gate_events']} "
          f"(blocks: {a['blocks']}, approval prompts: {a['asks']})")
    print(f"  override rate on gated actions: {a['override_rate']:.0f}%  "
          "(rising = eroding trust in the gates — review gate scope)")
    if a["asks_undecided"]:
        print(f"    note: {a['asks_undecided']} ask(s) had no recorded human "
              "decision — excluded from the rate (backfill 'approved' in CI)")
    for g, n in a["gate_names"]:
        print(f"    {g:<22} {n}")

    print("\n-- Tool-call actor distribution (NOT per-change authorship) --")
    for actor, n in a["provenance"]:
        print(f"    {actor:<8} {n}")
    print("  (this counts trace EVENTS — one agent session is many tool calls, a")
    print("   human manual change is one. For authorship provenance per change,")
    print("   use the traceability log's author_type, not these counts.)")
    print("\nNote: GitHub's audit log does not capture client-side prompts; this")
    print("trace is the compensating control. Schema: traceability-log-schema.md")


def write_html(a: dict, path: Path) -> None:
    """Single self-contained HTML report (inline CSS, no deps, no JS needed)."""
    def rows(pairs, total=None, fmt="{:,.0f}"):
        out = []
        for k, v in pairs:
            share = (f"<td class='num dim'>{v / total * 100:4.1f}%</td>"
                     if total else "")
            out.append(f"<tr><td>{html.escape(str(k))}</td>"
                       f"<td class='num'>{fmt.format(v)}</td>{share}</tr>")
        return "".join(out)

    # Budget alert chips: each threshold visibly FIRED or armed.
    chips = []
    for t in ALERTS:
        fired = t in a["alerts_fired"]
        cls = "chip fired" if fired else "chip ok"
        chips.append(f"<span class='{cls}'>{t}% {'FIRED' if fired else 'ok'}</span>")
    chip_html = " ".join(chips)
    pct = a["pct_budget"]
    color = "#c0392b" if pct >= 90 else ("#e67e22" if pct >= 75 else "#2e7d32")
    total = a["total_credits"] or 1.0

    override_note = (f"{a['asks_undecided']} ask(s) undecided — excluded"
                     if a["asks_undecided"] else "all asks had a recorded decision")
    actor_mix = " · ".join(f"{k}: {n}" for k, n in a["provenance"])
    gate_rows = rows(a["gate_names"]) or "<tr><td colspan='2'>no gate events</td></tr>"

    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Copilot governance dashboard — Session 6 · Lab 6.6</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:960px;margin:2em auto;color:#222;padding:0 1em}}
h1{{font-size:1.3em}} h2{{font-size:1.05em;margin-top:1.8em}}
table{{border-collapse:collapse;min-width:320px}} td,th{{border:1px solid #ccc;padding:.3em .6em}}
th{{background:#f4f4f4;text-align:left}} .num{{text-align:right}} .dim{{color:#888}}
.cards{{display:flex;flex-wrap:wrap;gap:14px;margin-top:1em}}
.card{{flex:1 1 200px;border:1px solid #ddd;border-radius:10px;padding:.9em 1em;background:#fafafa}}
.card .big{{font-size:1.6em;font-weight:700}} .card .label{{color:#666;font-size:.8em;text-transform:uppercase;letter-spacing:.04em}}
.card .sub{{color:#666;font-size:.82em;margin-top:.3em}}
.bar{{background:#eee;border-radius:6px;height:18px;width:100%;margin-top:.5em;position:relative}}
.fill{{background:{color};height:100%;border-radius:6px;width:{min(100, pct):.1f}%}}
.tick{{position:absolute;top:-3px;bottom:-3px;width:2px;background:#555}}
.chip{{display:inline-block;border-radius:999px;padding:.1em .7em;font-size:.78em;font-weight:600;margin-right:.2em}}
.chip.fired{{background:#c0392b;color:#fff}} .chip.ok{{background:#e6efe6;color:#2e7d32;border:1px solid #b8d4b8}}
.gap{{display:flex;flex-wrap:wrap;gap:14px}} .gap>div{{flex:1 1 300px;border:1px solid #ddd;border-radius:10px;padding:.8em 1em}}
.gap .client{{background:#eef4fb}} .gap .server{{background:#fdf3ee}}
.gap ul{{margin:.4em 0 .2em 1.2em;padding:0;font-size:.88em}}
.cols{{display:flex;flex-wrap:wrap;gap:2em}}
.note{{color:#666;font-size:.85em}}
</style></head><body>
<h1>Copilot governance dashboard — Session 6 · Lab 6.6</h1>

<div class="cards">
<div class="card" style="flex:2 1 300px">
  <div class="label">AI-credit spend vs budget (pooled; 1 credit = $0.01)</div>
  <div class="big" style="color:{color}">{a['total_credits']:,.0f} <span style="font-size:.55em;color:#666">/ {a['budget']:,.0f} credits ({pct:.1f}%)</span></div>
  <div class="bar"><div class="fill"></div>
    <div class="tick" style="left:75%"></div><div class="tick" style="left:90%"></div></div>
  <div class="sub">budget alerts: {chip_html}</div>
</div>
<div class="card">
  <div class="label">PRs with AI review</div>
  <div class="big">{a['pct_prs_ai_review']:.0f}%</div>
  <div class="sub">{a['reviewed_prs']} of {a['total_prs']} merged PRs · {a['bugs_pre_merge']} blocker finding(s) caught pre-merge</div>
</div>
<div class="card">
  <div class="label">Override rate on gated actions</div>
  <div class="big">{a['override_rate']:.0f}%</div>
  <div class="sub">{override_note}; rising = eroding trust in the gates — review gate scope</div>
</div>
<div class="card">
  <div class="label">Gate activity</div>
  <div class="big">{a['blocks']} <span style="font-size:.55em;color:#666">blocks</span> · {a['asks']} <span style="font-size:.55em;color:#666">asks</span></div>
  <div class="sub">{a['gate_events']} gate events in {a['trace_events']} trace events · agent-authored PRs: {a['agent_prs']}</div>
</div>
</div>

<div class="cols">
<div><h2>Spend by team (attribution of the pooled credits)</h2>
<table><tr><th>team</th><th>credits</th><th>share</th></tr>{rows(a['by_team'], total)}</table></div>
<div><h2>Spend by feature</h2>
<table><tr><th>feature</th><th>credits</th><th>share</th></tr>{rows(a['by_feature'], total)}</table></div>
</div>
<div class="cols">
<div><h2>Spend by user</h2>
<table><tr><th>user</th><th>credits</th><th>share</th></tr>{rows(a['by_user'], total)}</table></div>
<div><h2>Spend by model</h2>
<table><tr><th>model</th><th>credits</th><th>share</th></tr>{rows(a['by_model'], total)}</table></div>
</div>

<h2>Gate breakdown &amp; actor mix</h2>
<table><tr><th>gate</th><th>events</th></tr>{gate_rows}</table>
<p class="note">Tool-call actor mix — {actor_mix} — counts trace EVENTS, not
per-change authorship; authorship provenance for ISO 26262 lives in the
traceability log's <code>author_type</code> (traceability-log-schema.md).</p>

<h2>The audit gap — client-side hooks vs GitHub's server-side audit log</h2>
<div class="gap">
<div class="client"><b>Client-side: hook trace (this repo's compensating control)</b>
<ul>
<li><b>{a['trace_events']}</b> events captured this period — every agent tool call,
including <b>{a['blocks']}</b> blocked and <b>{a['asks']}</b> gated attempts
(self-logged by the gates; a denied call never reaches PostToolUse)</li>
<li>identity + tool + target + verdict per event; metadata only, no prompt content</li>
<li>retention: yours to set — align with the safety-case lifecycle; ship to SIEM</li>
</ul></div>
<div class="server"><b>Server-side: GitHub audit log (<code>action:copilot</code>)</b>
<ul>
<li><b>0</b> of those client-side prompts/tool calls appear here — it captures
plan, policy and seat changes plus website agent activity only</li>
<li>~180-day retention — far short of a safety-case lifecycle</li>
<li>still authoritative for policy/seat forensics — use both, they don't overlap</li>
</ul></div>
</div>

<p class="note">GitHub's audit log does not capture client-side prompts — the
hook trace above is the compensating evidence.
Usage data source: Copilot usage metrics API (GA, NDJSON; 1-day/28-day reports,
~1-year retention, metrics policy required; legacy Metrics API closed Apr 2026).
Fixture data is <b>synthetic</b> — shapes are the lesson, not magnitudes; adapt
field names to the live API schema when wiring real data (LIVE.md).</p>
</body></html>"""
    path.write_text(doc, encoding="utf-8")
    print(f"\nHTML report written: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Copilot governance dashboard (Lab 6.6)")
    ap.add_argument("--usage", type=Path, default=HERE / "fixtures/sample-usage-metrics.ndjson")
    ap.add_argument("--hook-trace", type=Path, default=HERE / "fixtures/sample-hook-trace.jsonl")
    ap.add_argument("--budget", type=float, default=4000.0,
                    help="monthly credit budget for this cost center (default 4000)")
    ap.add_argument("--total-prs", type=int, default=12,
                    help="PRs merged in the period (denominator for %% AI review)")
    ap.add_argument("--html", type=Path, help="also write a single-file HTML report")
    ap.add_argument("--simulate-alerts", action="store_true",
                    help="walk the budget down so each 75/90/100 threshold fires "
                         "in turn (budget-alert demo for Lab 6.6)")
    args = ap.parse_args()

    if args.simulate_alerts:
        usage = read_ndjson(args.usage)
        spend = sum(r.get("credits", 0.0) for r in usage)
        print(f"budget-alert simulation — fixed spend {spend:,.0f} credits, "
              "shrinking the budget:\n")
        # Budgets placing spend just under / at each threshold, so the 100%
        # alert fires AT 100% (not via an overshoot).
        for target_pct in (70, 85, 92, 100):
            budget = spend / (target_pct / 100.0)
            pct = spend / budget * 100.0
            fired = [t for t in ALERTS if pct >= t]
            print(f"  budget {budget:>8,.0f}  → {pct:5.1f}%  "
                  + bar(pct) + f"  alerts: {', '.join(f'{t}%' for t in fired) or 'none'}")
        print("\nEach threshold fires as spend crosses it; wire these to the org's")
        print("billing budget alerts (budget-alerts-setup.md). Note the budget")
        print("TYPE: an alert-only budget keeps spending past 100% (you just get")
        print("notified); a hard-stop budget BLOCKS further paid usage at 100%, so")
        print("105% is unreachable there — pick the type deliberately per cost center.")
        return 0

    usage = read_ndjson(args.usage)
    trace = read_ndjson(args.hook_trace) if args.hook_trace.exists() else []
    if not trace:
        print(f"note: hook trace '{args.hook_trace}' missing or empty — "
              "run the Lab 6.2 probes to generate one.\n")

    a = analyze(usage, trace, args.budget, args.total_prs)
    print_report(a)
    if args.html:
        write_html(a, args.html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
