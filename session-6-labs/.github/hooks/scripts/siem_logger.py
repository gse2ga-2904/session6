#!/usr/bin/env python3
"""siem_logger.py — observer hook: append every agent event as NDJSON for SIEM ingestion.

Course:   Agent Operations (Copilot edition) · Session 1 · Lab L1.5 (Session 2 upgrades
          this pattern into a trace emitter — see session-2/code/hooks/scripts/emit_trace.py)
Wired by: .github/hooks/siem-logger.json (SessionStart, PostToolUse, Stop)
Run:      invoked by the Copilot agent runtime with the hook event as JSON on stdin.
          Manual test:  echo '<event-json>' | python3 siem_logger.py && tail audit/siem.ndjson
          Unit tests:   pytest session-1/code/test_hooks.py -k siem -v

Design rules (Session 1.2 "performance" slide):
  * OBSERVER: always exits 0 — logging must never block or break the agent loop.
  * FAST: append to a local NDJSON file only. No network I/O in the hot path; ship the
    file to your SIEM out-of-band (forwarder, cron, log agent).
  * Privacy: logs tool names, targets and outcomes — not full prompt/response contents.
    Content capture is a policy decision (works council!) — do not enable it casually.

Config via env vars only (no secrets in code):
  SIEM_LOG_PATH  target NDJSON file (default ./audit/siem.ndjson)
"""

import datetime
import json
import os
import sys


def get_field(obj: dict, *names: str, default=None):
    """First present key among snake_case/camelCase variants (cross-harness payloads)."""
    for name in names:
        if name in obj:
            return obj[name]
    return default


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {"parse_error": True}

    tool_input = get_field(event, "tool_input", "toolInput", default={}) or {}
    record = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": get_field(event, "hook_event_name", "hookEventName", "event",
                           default="unknown"),
        "session_id": get_field(event, "session_id", "sessionId", default=None),
        "agent": get_field(event, "agent_name", "agentName", default=None),
        "tool": get_field(event, "tool_name", "toolName", default=None),
        # target only — command/file path, not full contents:
        "target": get_field(tool_input, "command", "cmd", default=None)
                  or get_field(tool_input, "file_path", "filePath", default=None),
        "outcome": get_field(event, "tool_result_status", "toolResultStatus",
                             "outcome", default=None),
        "user": os.environ.get("USER") or os.environ.get("USERNAME") or "unknown",
    }

    path = os.environ.get("SIEM_LOG_PATH", os.path.join("audit", "siem.ndjson"))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Observer: report on stderr but NEVER block the loop.
        print(f"siem_logger: non-fatal error ({exc})", file=sys.stderr)
    sys.exit(0)
