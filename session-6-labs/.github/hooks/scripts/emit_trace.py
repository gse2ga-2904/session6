#!/usr/bin/env python3
"""emit_trace.py — observer hook: forward each agent lifecycle event to the local collector.

Course:   Agent Operations (Copilot edition) · Session 2 · Activity A2.3 / Lab L2.5.
Wired by: .github/hooks/emit-trace.json (all eight lifecycle events).
Run:      invoked by the Copilot agent runtime with the hook event as JSON on stdin.
          Plumbing smoke test (no agent needed):
              python3 emit_trace.py --self-test
Backend:  session-2/code/trace-collector.py must be running; endpoint from
          TRACE_COLLECTOR_URL (default http://127.0.0.1:8787/v1/events).

Design rules (same as the Session 1 SIEM logger, tightened for telemetry):
  * OBSERVER: always exits 0. Telemetry must never block or slow the agent loop.
  * FIRE-AND-FORGET: single POST, 0.5 s timeout, drop the event on any failure.
  * Cross-harness payloads: accepts snake_case and camelCase field names.
  * Token fields are forwarded when the payload provides them and left null when it
    doesn't — the report marks them "unknown" rather than inventing numbers.
  * Privacy: forwards tool names, targets, outcomes, timings, token counts — not
    full prompt/response contents.

Attribute naming loosely follows the OTel GenAI spirit; those conventions are still
EXPERIMENTAL (mid-2026) — pin versions when you productionize.
"""

import datetime
import json
import os
import sys
import urllib.request
import uuid


def get_field(obj: dict, *names: str, default=None):
    for name in names:
        if name in obj:
            return obj[name]
    return default


def build_event(raw: dict) -> dict:
    tool_input = get_field(raw, "tool_input", "toolInput", default={}) or {}
    usage = get_field(raw, "usage", "tokenUsage", "token_usage", default={}) or {}
    return {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": get_field(raw, "hook_event_name", "hookEventName", "event",
                           default="unknown"),
        "session_id": get_field(raw, "session_id", "sessionId", default="unknown"),
        "span_id": uuid.uuid4().hex[:12],
        "parent_agent": get_field(raw, "agent_name", "agentName", default=None),
        "subagent": get_field(raw, "subagent_name", "subagentName", default=None),
        "tool": get_field(raw, "tool_name", "toolName", default=None),
        "target": get_field(tool_input, "command", "cmd", default=None)
                  or get_field(tool_input, "file_path", "filePath", default=None),
        "outcome": get_field(raw, "tool_result_status", "toolResultStatus", "outcome",
                             default=None),
        "error": get_field(raw, "error", "errorMessage", default=None),
        "tokens_in": get_field(usage, "input_tokens", "inputTokens", default=None),
        "tokens_out": get_field(usage, "output_tokens", "outputTokens", default=None),
        "model": get_field(raw, "model", "modelName", default=None),
    }


def post(event: dict) -> bool:
    url = os.environ.get("TRACE_COLLECTOR_URL", "http://127.0.0.1:8787/v1/events")
    data = json.dumps(event).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=0.5):
            return True
    except Exception:
        return False  # drop the event; never retry in the hot path


def main() -> None:
    if "--self-test" in sys.argv:
        fixture = {"hook_event_name": "PostToolUse", "session_id": "selftest",
                   "tool_name": "bash", "tool_input": {"command": "pytest -q"},
                   "tool_result_status": "ok",
                   "usage": {"input_tokens": 1200, "output_tokens": 80}}
        ok = post(build_event(fixture))
        print("self-test:", "event delivered" if ok
              else "collector unreachable (is trace-collector.py running?)")
        return

    try:
        raw = json.load(sys.stdin)
    except Exception:
        raw = {"parse_error": True}
    post(build_event(raw))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"emit_trace: non-fatal error ({exc})", file=sys.stderr)
    sys.exit(0)
