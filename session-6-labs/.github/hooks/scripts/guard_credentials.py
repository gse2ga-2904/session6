#!/usr/bin/env python3
"""
guard_credentials.py — PreToolUse gate: require human approval on credential files.

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 6 · Lab 6.2 (corporate gate set), wired via ../gates.json
How to run: not directly — the harness pipes the tool-call JSON to stdin.
Probe it: ask the agent to edit secrets/ci-deploy.env.example; expect an
approval decision rather than a silent edit.

Behavior: for edits/writes touching credential paths, emit the JSON
permission decision "ask" (surfaces that support hook JSON output show an
approval prompt). On surfaces that ignore hook stdout, the conservative
fallback below blocks instead (exit 2). Fail posture, stated precisely:
fails CLOSED on a matched credential path (ask/block), but fails OPEN on
unparseable stdin (returns 0) so a malformed event never wedges every edit.
Reads snake_case and camelCase fields; does its own matching.
"""

import fnmatch
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _trace import record_gate_decision  # noqa: E402  (sibling helper)

# NOTE on glob semantics: Python fnmatch is NOT gitignore-style — `**` behaves
# the same as `*`, and `*` DOES span `/`. So `*.pem` already matches nested
# `a/b/foo.pem`, and the `**/` prefixes below are belt-and-suspenders, not
# recursive globbing. The list is deliberately loose (fail toward matching —
# correct for a security gate). Dedupe if you like; over-matching is safe here.
CREDENTIAL_GLOBS = [
    "secrets/*", "secrets/**", "**/secrets/**",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "**/*credential*", "**/*.env", "**/*.env.*",
    "**/id_rsa*", "**/known_hosts",
    ".github/workflows/*deploy*",   # deploy workflows hold secret wiring
]

# Set GATE_CRED_MODE=block to force fail-closed behavior everywhere.
MODE = os.environ.get("GATE_CRED_MODE", "ask")


def get(d: dict, *names, default=None):
    for n in names:
        if n in d:
            return d[n]
    return default


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

    # Normalize a single leading "./"; do NOT lstrip("./") — that strips the
    # dot off dotdirs like ".github", defeating the deploy-workflow glob.
    rel = path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    hit = next((g for g in CREDENTIAL_GLOBS
                if fnmatch.fnmatch(rel, g) or fnmatch.fnmatch("/" + rel, g)), None)
    if hit is None:
        return 0

    reason = (
        f"Credential-path gate: '{rel}' matches '{hit}'. "
        "Credential creation/rotation/exposure requires explicit human approval "
        "(governance runbook, gate G2)."
    )

    if MODE == "ask":
        # Record the ask (blocked/gated calls don't reach the PostToolUse hook).
        record_gate_decision(event, gate="G2-credential-path", verdict="ask")
        # JSON decision output: harnesses that support it show an approval prompt.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            }
        }))
        return 0

    record_gate_decision(event, gate="G2-credential-path", verdict="block")
    sys.stderr.write("BLOCKED (fail-closed mode): " + reason + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
