#!/usr/bin/env python3
"""
audit_log.py — PostToolUse hook: append every agent tool call to hook-trace.jsonl.

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 6 · Lab 6.2 (gate set) — and its output is the INPUT to
          Lab 6.6 (dashboard.py) and the SIEM-shipping pattern.
How to run: not directly — the harness pipes the tool-result JSON to stdin.
Output:   one JSON line per event appended to hook-trace.jsonl (repo root, or
          $HOOK_TRACE_FILE). Ship this file to your SIEM.

WHY THIS EXISTS (the audit gap, verbatim from the deck): GitHub's audit log
(`action:copilot`, ~180-day retention) captures plan/policy/seat changes and
website agent activity — it does NOT capture client-side prompts or tool calls
from the IDE/CLI. This hook is the compensating control: identity + tool +
target + verdict + timestamp, without storing prompt content (metadata-only by
default — deliberately, to avoid copying sensitive code into logs).
"""

import getpass
import json
import os
import sys
from datetime import datetime, timezone

TRACE_FILE = os.environ.get("HOOK_TRACE_FILE", "hook-trace.jsonl")


def get(d: dict, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never break the session over logging

    tool_input = get(event, "tool_input", "toolInput", default={}) or {}
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": getpass.getuser(),
        "actor": "agent",
        "event": get(event, "hook_event_name", "hookEventName", default="PostToolUse"),
        "session_id": get(event, "session_id", "sessionId", default=None),
        "tool": get(event, "tool_name", "toolName", default="unknown"),
        # target metadata only — no prompt content, no file content:
        "target": get(tool_input, "file_path", "filePath", "path", default=None)
                  or (get(tool_input, "command", default="") or "")[:120] or None,
        # verdict, if a gate populated one upstream (blocked calls surface as
        # PreToolUse denials; harnesses that report them here get recorded too):
        "verdict": get(event, "permission_decision", "permissionDecision", default="allow"),
    }

    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # logging must never block the tool result

    return 0


if __name__ == "__main__":
    sys.exit(main())
