#!/usr/bin/env python3
"""
_trace.py — shared helper so PreToolUse GATES self-record their verdicts.

Course:   Agent Operations (Copilot edition) · Session 6 · Lab 6.2.
Why this exists: a PreToolUse gate that exits 2 BLOCKS the tool call, so the
tool never runs and the PostToolUse audit hook (audit_log.py) never fires for
it. Without this, the blocks a student triggers would be missing from
hook-trace.jsonl — contradicting the deck's "log always, even blocked ones."
Each gate calls record_gate_decision() right before it blocks/asks, so denials
land in the SAME trace file the dashboard consumes.

Record shape matches audit_log.py (event, tool, target, verdict, actor, …) plus
a `gate` field naming which control fired. Metadata only — no prompt/content.
"""

import getpass
import json
import os
from datetime import datetime, timezone

TRACE_FILE = os.environ.get("HOOK_TRACE_FILE", "hook-trace.jsonl")


def _get(d: dict, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default


def record_gate_decision(event: dict, gate: str, verdict: str) -> None:
    """Append one gate-decision line (verdict = 'block' | 'ask'). Never raises —
    logging must not break the gate's own decision."""
    try:
        tool_input = _get(event, "tool_input", "toolInput", default={}) or {}
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user": getpass.getuser(),
            "actor": "agent",
            "event": _get(event, "hook_event_name", "hookEventName",
                          default="PreToolUse"),
            "session_id": _get(event, "session_id", "sessionId", default=None),
            "tool": _get(event, "tool_name", "toolName", default="unknown"),
            "target": _get(tool_input, "file_path", "filePath", "path", default=None)
                      or (_get(tool_input, "command", default="") or "")[:120] or None,
            "gate": gate,
            "verdict": verdict,   # "block" | "ask"
        }
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # a logging failure must never change the gate's verdict
