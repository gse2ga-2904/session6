#!/usr/bin/env python3
"""
safety_critical_gate.py — PreToolUse gate: block above-threshold changes in
safety-critical paths (requires a named human reviewer instead).

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 6 · Lab 6.2 (corporate gate set), wired via ../gates.json
How to run: not directly — the harness pipes the tool-call JSON to stdin.
Probe it: ask the agent for a change touching > 20 lines under safety/;
expect a block explaining the named-reviewer requirement.

Policy encoded here (adapt thresholds to your BU):
  - ANY agent edit under a safety-critical path is gated;
  - small edits (<= MAX_LINES changed lines) pass with a warning (the
    PostToolUse audit hook still records them);
  - larger edits are BLOCKED: they must arrive as a human-authored (or
    human-co-authored) PR with a named reviewer per CODEOWNERS.
This is the client-side seatbelt; the unbypassable version of the same rule
lives server-side (protected branches + CODEOWNERS + required checks), which
is also what bounds the cloud agent — client hooks do not run there.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _trace import record_gate_decision  # noqa: E402  (sibling helper)

SAFETY_PREFIXES = (
    "safety/", "src/safety/", "asil/", "src/brake/", "calibration/",
)
MAX_LINES = int(os.environ.get("GATE_SAFETY_MAX_LINES", "20"))


def get(d: dict, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default


def changed_lines(tool_input: dict) -> int:
    """Conservative size estimate of an edit, across harness input shapes.

    HONEST LIMITATION: for an Edit with both old and new text we return the
    line DELTA (added minus removed, plus a small floor for in-place changes).
    For a full-file write (only `content`) we return the whole file's line
    count — which OVER-counts, so a 1-line change to a 500-line safety file
    trips the gate. That is deliberately conservative for safety-critical
    paths (fail toward requiring a human), but say it out loud rather than
    pretending 'lines in the new blob' == 'lines changed'.
    """
    old = get(tool_input, "old_string", "oldString", "old_text", "oldText")
    new = get(tool_input, "new_string", "newString", "new_text", "newText")
    if isinstance(old, str) and isinstance(new, str):
        # a replacement: net line change, with a floor of 1 for same-size edits
        return max(1, abs(new.count("\n") - old.count("\n")),
                   min(new.count("\n") + 1, old.count("\n") + 1))
    for field in ("new_string", "newString", "content", "new_text", "newText", "code"):
        val = get(tool_input, field)
        if isinstance(val, str):
            return val.count("\n") + 1   # full-file write: conservative over-count
    return 0


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool = (get(event, "tool_name", "toolName", default="") or "").lower()
    tool_input = get(event, "tool_input", "toolInput", default={}) or {}
    path = (get(tool_input, "file_path", "filePath", "path", default="") or "")

    if tool not in ("edit", "write", "create_file", "str_replace", "apply_patch",
                    # VS Code (Preview) payload names:
                    "editfiles", "edit_files", "create", "createfile",
                    "replace_string_in_file", "insert_edit_into_file", "write_file"):
        return 0
    if not path:
        return 0

    # Normalize a single leading "./" without lstrip("./") (which would strip
    # leading dots from any dotpath).
    rel = path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    if not rel.startswith(SAFETY_PREFIXES):
        return 0

    n = changed_lines(tool_input)
    if n <= MAX_LINES:
        sys.stderr.write(
            f"NOTE: small agent edit ({n} lines) in safety-critical path '{rel}' "
            "allowed — recorded for audit; PR review per CODEOWNERS still required.\n"
        )
        return 0

    record_gate_decision(event, gate="G4-safety-threshold", verdict="block")
    sys.stderr.write(
        f"BLOCKED by safety-critical gate: {n} changed lines in '{rel}' exceeds the "
        f"{MAX_LINES}-line agent threshold (governance runbook, gate G4).\n"
        "Changes of this size in safety-critical code require a human author or "
        "co-author and a named reviewer via the normal PR flow. The agent may "
        "propose the change as a patch file for human application instead.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
