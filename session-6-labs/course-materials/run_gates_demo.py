#!/usr/bin/env python3
"""
run_gates_demo.py — payload injector for the four Session 6 governance gates.

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 6 · Lab 6.2 (`make demo`) and `make verify` (--check/--json).
How to run:
    python3 run_gates_demo.py            # narrated event × gate decision matrix
    python3 run_gates_demo.py --check    # self-check: assert the expected matrix
    python3 run_gates_demo.py --json     # machine-readable matrix (also asserts)

Feeds ~15 recorded tool-call payloads (both snake_case and camelCase, incl.
sneaky variants like a force-push buried in an `&&` chain) through EVERY gate
script, exactly as hooks/gates.json wires them — remember the kit's core
caveat: matchers are parsed but NOT applied, so each script self-matches and
must exit 0 fast for tools it doesn't govern. The demo therefore runs all
three PreToolUse gates on every event and combines verdicts most-restrictive
first (block > ask > allow), then runs the PostToolUse audit logger only for
events that survive — blocked/asked calls never reach PostToolUse, which is
why the gates self-log their denials via _trace.py.

Matrix cells:
  block  — gate exits 2 (hard stop; stderr reaches the agent)
  ask    — gate emits JSON permissionDecision:"ask" (human approval prompt)
  allow  — gate exits 0 with no ask (G4 may still print an audit note)
Audit column:
  logged   — event survived; audit_log.py appended a PostToolUse trace line
  self-log — a gate denied; the GATE appended its own trace line (_trace.py)

The gates (from hooks/gates.json):
  G1 block_destructive     rm -rf / force-push / git clean / dd / DROP TABLE …
  G2 guard_credentials     writes to secrets/*, *.env, id_rsa, vault paths, …
  G4 safety_critical_gate  agent edits > threshold lines under safety paths
  --  audit_log            PostToolUse observer — always allow, always record

The audit JSONL is written to a fresh temp dir (path printed) — it is the
same shape dashboard.py consumes. This is the offline twin of probing the
gates in a live Copilot CLI session (see LIVE.md).
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / "hooks" / "scripts"

GATES = [  # order matters: block first (mirrors gates.json PreToolUse order)
    ("G1", "block_destructive.py"),
    ("G2", "guard_credentials.py"),
    ("G4", "safety_critical_gate.py"),
]
RANK = {"allow": 0, "ask": 1, "block": 2}

BIG_EDIT = "x = 0;\n" * 40    # 40 lines — over the safety gate's 20-line default
SMALL_EDIT = "y = 1;\n" * 3   # 3 lines — under it

# (label, event payload, expected per-gate verdicts, expected final verdict)
CASES = [
    # --- shell events → G1 territory -------------------------------------
    ("benign read (cat)",
     {"hook_event_name": "PreToolUse", "tool_name": "bash",
      "tool_input": {"command": "cat README.md"}},
     {"G1": "allow", "G2": "allow", "G4": "allow"}, "allow"),

    ("plain rm -rf",
     {"hook_event_name": "PreToolUse", "tool_name": "bash",
      "tool_input": {"command": "rm -rf build/"}},
     {"G1": "block", "G2": "allow", "G4": "allow"}, "block"),

    ("sneaky force-push in && chain (camelCase)",
     {"hookEventName": "PreToolUse", "toolName": "bash",
      "toolInput": {"command":
                    'git commit -m "wip" && git push --force origin main'}},
     {"G1": "block", "G2": "allow", "G4": "allow"}, "block"),

    ("benign git push (no force)",
     {"hook_event_name": "PreToolUse", "tool_name": "bash",
      "tool_input": {"command": "git push origin main"}},
     {"G1": "allow", "G2": "allow", "G4": "allow"}, "allow"),

    ("sneaky chained git clean -fdx",
     {"hook_event_name": "PreToolUse", "tool_name": "bash",
      "tool_input": {"command": "cd services/api && git clean -fdx"}},
     {"G1": "block", "G2": "allow", "G4": "allow"}, "block"),

    ("DROP TABLE via psql",
     {"hook_event_name": "PreToolUse", "tool_name": "bash",
      "tool_input": {"command": "psql -c 'DROP TABLE users;'"}},
     {"G1": "block", "G2": "allow", "G4": "allow"}, "block"),

    # --- edit/write events → G2 / G4 territory ---------------------------
    ("small edit, ordinary source file",
     {"hook_event_name": "PreToolUse", "tool_name": "edit",
      "tool_input": {"file_path": "src/app.c", "new_string": SMALL_EDIT}},
     {"G1": "allow", "G2": "allow", "G4": "allow"}, "allow"),

    ("write config/.env",
     {"hook_event_name": "PreToolUse", "tool_name": "write",
      "tool_input": {"file_path": "config/.env",
                     "content": "DB_PASSWORD=hunter2\n"}},
     {"G1": "allow", "G2": "ask", "G4": "allow"}, "ask"),

    ("write SSH key id_rsa (camelCase)",
     {"hookEventName": "PreToolUse", "toolName": "write",
      "toolInput": {"filePath": "/home/dev/.ssh/id_rsa",
                    "content": "-----BEGIN OPENSSH PRIVATE KEY-----\n"}},
     {"G1": "allow", "G2": "ask", "G4": "allow"}, "ask"),

    ("edit vault secrets path",
     {"hook_event_name": "PreToolUse", "tool_name": "edit",
      "tool_input": {"file_path": "vault/secrets/db-root-token.json",
                     "new_string": '{"token": "s.newroot"}'}},
     {"G1": "allow", "G2": "ask", "G4": "allow"}, "ask"),

    ("write deploy workflow (camelCase)",
     {"hookEventName": "PreToolUse", "toolName": "write",
      "toolInput": {"filePath": ".github/workflows/deploy-prod.yml",
                    "content": "on: push\n"}},
     {"G1": "allow", "G2": "ask", "G4": "allow"}, "ask"),

    ("small edit under src/safety/ (below threshold)",
     {"hook_event_name": "PreToolUse", "tool_name": "edit",
      "tool_input": {"file_path": "src/safety/watchdog.c",
                     "new_string": SMALL_EDIT}},
     {"G1": "allow", "G2": "allow", "G4": "allow"}, "allow"),

    ("big edit under safety/ (above threshold)",
     {"hook_event_name": "PreToolUse", "tool_name": "edit",
      "tool_input": {"file_path": "safety/brake_monitor.c",
                     "new_string": BIG_EDIT}},
     {"G1": "allow", "G2": "allow", "G4": "block"}, "block"),

    ("big edit OUTSIDE safety paths",
     {"hook_event_name": "PreToolUse", "tool_name": "edit",
      "tool_input": {"file_path": "src/app.c", "new_string": BIG_EDIT}},
     {"G1": "allow", "G2": "allow", "G4": "allow"}, "allow"),

    ("full-file write to calibration/ (camelCase, over-count)",
     {"hookEventName": "PreToolUse", "toolName": "write",
      "toolInput": {"filePath": "calibration/brake_curve.json",
                    "content": BIG_EDIT}},
     {"G1": "allow", "G2": "allow", "G4": "block"}, "block"),
]

# Derived expectations for the trace self-check:
EXPECTED_BLOCKS = sum(1 for *_, f in CASES if f == "block")   # gate self-logs
EXPECTED_ASKS = sum(1 for *_, f in CASES if f == "ask")       # gate self-logs
EXPECTED_ALLOWS = sum(1 for *_, f in CASES if f == "allow")   # audit-logged


def run_script(script: str, event: dict, env: dict) -> str:
    """Pipe one payload through one gate script; map its result to a verdict."""
    r = subprocess.run([sys.executable, str(SCRIPTS / script)],
                       input=json.dumps(event), text=True,
                       capture_output=True, env=env, timeout=15)
    if r.returncode == 2:
        return "block"
    if r.stdout.strip():
        try:
            out = json.loads(r.stdout)
            if out.get("hookSpecificOutput", {}).get("permissionDecision") == "ask":
                return "ask"
        except json.JSONDecodeError:
            pass
    return "allow"


def as_post_event(event: dict) -> dict:
    """The same event, replayed as the PostToolUse the audit hook would see."""
    post = dict(event)
    for k in ("hook_event_name", "hookEventName"):
        post.pop(k, None)
    key = "hookEventName" if "toolName" in event else "hook_event_name"
    post[key] = "PostToolUse"
    post["tool_result_status"] = "ok"
    return post


def main() -> int:
    ap = argparse.ArgumentParser(description="Session 6 gate payload injector")
    ap.add_argument("--check", action="store_true",
                    help="assert the expected matrix; exit non-zero on drift")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="emit the matrix as JSON (also exits non-zero on drift)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="gates-demo-"))
    trace = tmp / "hook-trace.jsonl"
    env = dict(__import__("os").environ, HOOK_TRACE_FILE=str(trace))

    results, failures = [], []
    for label, event, expected_gates, expected_final in CASES:
        verdicts = {}
        for gid, script in GATES:
            verdicts[gid] = run_script(script, event, env)
        final = max(verdicts.values(), key=RANK.__getitem__)
        audit = "self-log"
        if final == "allow":
            run_script("audit_log.py", as_post_event(event), env)
            audit = "logged"

        ok = (verdicts == expected_gates and final == expected_final)
        if not ok:
            failures.append(f"{label}: expected {expected_gates}/{expected_final}, "
                            f"got {verdicts}/{final}")
        tool_input = event.get("tool_input") or event.get("toolInput") or {}
        results.append({
            "case": label,
            "tool": event.get("tool_name") or event.get("toolName"),
            "target": tool_input.get("command")
                      or tool_input.get("file_path") or tool_input.get("filePath"),
            "gates": verdicts, "final": final, "audit": audit,
            "expected_gates": expected_gates, "expected_final": expected_final,
            "ok": ok,
        })

    records = []
    if trace.exists():
        records = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
    self_logged = [r for r in records if r.get("verdict") in ("block", "ask")]
    blocks = [r for r in self_logged if r["verdict"] == "block"]
    asks = [r for r in self_logged if r["verdict"] == "ask"]
    audited = [r for r in records if r.get("event") == "PostToolUse"]

    # Trace-side assertions (the narrative point: denials must not be lost).
    trace_failures = []
    if len(blocks) != EXPECTED_BLOCKS:
        trace_failures.append(f"expected {EXPECTED_BLOCKS} self-logged BLOCK "
                              f"records, found {len(blocks)}")
    if len(asks) != EXPECTED_ASKS:
        trace_failures.append(f"expected {EXPECTED_ASKS} self-logged ASK "
                              f"records, found {len(asks)}")
    if len(audited) != EXPECTED_ALLOWS:
        trace_failures.append(f"expected {EXPECTED_ALLOWS} PostToolUse audit "
                              f"records, found {len(audited)}")

    if args.as_json:
        print(json.dumps({
            "cases": results,
            "trace": {"path": str(trace), "records": len(records),
                      "self_logged_blocks": len(blocks),
                      "self_logged_asks": len(asks),
                      "audited_allows": len(audited)},
            "ok": not failures and not trace_failures,
        }, indent=2))
        return 1 if (failures or trace_failures) else 0

    print("governance gate decision matrix — event × gate → final (Lab 6.2)")
    print("=" * 98)
    print(f"{'case':<48} {'G1':<6} {'G2':<6} {'G4':<6} {'audit':<9} final")
    print("-" * 98)
    for r in results:
        mark = "" if r["ok"] else "   <-- expected " + r["expected_final"].upper()
        print(f"{r['case']:<48} {r['gates']['G1']:<6} {r['gates']['G2']:<6} "
              f"{r['gates']['G4']:<6} {r['audit']:<9} {r['final'].upper()}{mark}")
    print("=" * 98)
    print(f"G1 block_destructive · G2 guard_credentials · G4 safety_critical_gate "
          f"(threshold {__import__('os').environ.get('GATE_SAFETY_MAX_LINES', '20')} lines)")
    print(f"\naudit trail: {len(records)} record(s) → {trace}")
    print(f"  {len(blocks)} self-logged block(s) + {len(asks)} self-logged ask(s) "
          "(denied calls never reach the PostToolUse hook, so the gates log "
          f"their own verdicts) + {len(audited)} audited allow(s).")
    print("  This JSONL is the same shape dashboard.py consumes (Lab 6.6).")

    if args.check:
        print()
        all_failures = failures + trace_failures
        if all_failures:
            print("CHECK FAILED:")
            for f in all_failures:
                print(f"  - {f}")
            return 1
        print(f"CHECK OK: {len(CASES)} events × 4 gates produced the expected "
              "matrix (both payload casings, sneaky chained variants included), "
              f"and the trace holds all {EXPECTED_BLOCKS} blocks / "
              f"{EXPECTED_ASKS} asks / {EXPECTED_ALLOWS} audited allows.")
    elif failures or trace_failures:
        print("\nWARNING: matrix drifted from expectations "
              "(run with --check to fail the build):")
        for f in failures + trace_failures:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
