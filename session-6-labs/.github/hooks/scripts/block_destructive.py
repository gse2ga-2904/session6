#!/usr/bin/env python3
"""block_destructive.py — PreToolUse hook: deny destructive shell commands.

*** LAB A1.2 — this is the WORKING example. Run it, read it, then extend it. ***
labs-repo ships this blocker complete: `python3 -m pytest tests/test_hooks.py -k destructive`
is green out of the box. In Activity A1.2 you (1) watch it block a live agent,
(2) find the four `WHY:` markers below — the load-bearing decisions — and
(3) add ONE deny rule of your own at the marked extension point, with a test.
Want to build it from scratch instead? Async stretch: the TODO skeleton is
preserved in the course kit at
session-1/code/hooks/scripts/block_destructive_skeleton.py.

Course:   Agent Operations (Copilot edition) · Session 1 · Activity A1.2 / Lab L1.5
Wired by: .github/hooks/block-destructive.json
Run:      invoked by the Copilot agent runtime with the hook event as JSON on stdin.
          Manual test:  echo '<event-json>' | python3 block_destructive.py ; echo $?
          Unit tests:   python3 -m pytest tests/test_hooks.py -k destructive -v   (labs-repo root)

Contract (course convention, cross-harness safe — facts as of Jul 2026):
  allow -> exit 0, no output.
  BLOCK -> emit BOTH deny signals, because surfaces differ:
           * stdout JSON `{"permissionDecision": "deny", ...}` — what Copilot
             CLI / cloud agent honor (also nested as hookSpecificOutput for
             VS Code / Claude Code JSON parsing);
           * reason on stderr + exit 2 — what VS Code (Preview) honors.
           $BLOCK_EXIT_CODE overrides the deny exit code (default 2): if the
           pre-flight live test shows your CLI build ignores stdout JSON on
           exit 2, set BLOCK_EXIT_CODE=0 so the JSON deny is parsed.
  Any crash/malformed input takes the same deny path: FAIL CLOSED.

No secrets: configuration via env vars only (PROTECTED_BRANCHES, BLOCK_EXIT_CODE).
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _trace import record_gate_decision  # noqa: E402  (sibling helper)

# Tool names that mean "execute a shell command" across harnesses.
# (Tool names differ across harnesses too — hence a set, not one string.)
SHELL_TOOL_NAMES = {"bash", "shell", "run_in_terminal", "terminal", "execute",
                    # VS Code (Preview) payload names — without these the
                    # blocker silently allows everything in the VS Code GUI:
                    "runterminalcommand", "run_terminal_command", "powershell"}

# Deny rules: (compiled regex on the command string, human-readable reason).
# NOTE: regex command-matching is inherently bypassable (quoting, aliases,
# env-var indirection). It is a client-side seatbelt; the unbypassable control
# is server-side (protected branches + required checks) — Session 6, layer 3.
# The rm rule catches BOTH short clusters (-rf, -fr) and GNU long options
# (--recursive --force), in any order.
DENY_RULES = [
    (re.compile(r"\brm\s+(?=(?:.*\s)?(?:-[a-z]*r[a-z]*\b|--recursive))"
                r"(?=(?:.*\s)?(?:-[a-z]*f[a-z]*\b|--force))", re.IGNORECASE),
     "recursive/forced delete (rm -rf / rm --recursive --force) is denied by policy"),
    # >>> A1.2 step 5 — ADD YOUR RULE HERE <<<
    # One (regex, reason) tuple for a command that is dangerous in YOUR repos
    # (ideas: chmod -R 777, writes to /etc, git clean -fdx, DROP TABLE).
    # Then prove it with one new test in tests/test_hooks.py.
]

FORCE_PUSH_RE = re.compile(r"\bgit\s+push\b(?P<rest>.*)", re.IGNORECASE)
FORCE_FLAG_RE = re.compile(r"(\s--force(-with-lease)?\b|\s-f\b)")


def get_field(obj: dict, *names: str, default=None):
    """Return the first present key among snake_case/camelCase variants.

    WHY: payload field casing differs across harnesses — Claude Code sends
    snake_case (tool_input.file_path), Copilot sends camelCase
    (toolInput.filePath). A guard that only reads one casing silently allows
    everything from the other harness. Load-bearing decision #2 of 4.
    """
    for name in names:
        if name in obj:
            return obj[name]
    return default


def protected_branches():
    raw = os.environ.get("PROTECTED_BRANCHES", "main,master,release/*")
    return [b.strip() for b in raw.split(",") if b.strip()]


def branch_is_protected(rest: str) -> bool:
    tokens = rest.split()
    for pattern in protected_branches():
        if pattern.endswith("/*"):
            prefix = pattern[:-1]  # keep the slash
            if any(t.startswith(prefix) or (":" in t and t.split(":", 1)[1].startswith(prefix))
                   for t in tokens):
                return True
        else:
            if any(t == pattern or t.endswith(":" + pattern) for t in tokens):
                return True
    # `git push --force` with no explicit remote/refspec targets the current
    # branch: fail safe and treat it as protected. `positional` is the args
    # after `push` that are not flags (i.e. a remote and/or refspec); if there
    # are none, we can't prove the target is a safe branch. The agent can
    # rephrase with an explicit safe branch to proceed.
    positional = [t for t in tokens[1:] if not t.startswith("-")]
    if not positional:
        return True
    return False


def deny(reason: str, event: dict) -> None:
    """Block the tool call — emit every deny signal the surfaces understand.

    WHY: blocking semantics are surface-dependent (Jul 2026). VS Code (Preview)
    blocks on exit 2 with the reason on stderr; Copilot CLI and cloud agent
    block on a stdout JSON `permissionDecision: "deny"` (VS Code and Claude
    Code also accept it nested under hookSpecificOutput). Emitting all of them
    makes the same script block everywhere, and the reason string reaches the
    agent either way so it self-corrects instead of retrying blindly — an
    empty reason produces retry loops. Load-bearing decision #3 of 4.
    """
    # A blocked call never reaches the PostToolUse audit hook, so log the denial
    # here (Session 6's audit-gap lesson — the trace must capture blocks).
    record_gate_decision(event, gate="block-destructive", verdict="block")
    print(json.dumps({
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }))
    print(f"BLOCKED by block_destructive hook: {reason}", file=sys.stderr)
    sys.exit(int(os.environ.get("BLOCK_EXIT_CODE", "2")))


def main() -> None:
    event = json.load(sys.stdin)

    tool_name = str(get_field(event, "tool_name", "toolName", default="")).lower()
    if tool_name not in SHELL_TOOL_NAMES:
        # WHY: matcher ENFORCEMENT IS SURFACE-DEPENDENT (Jul 2026). Copilot CLI
        # honors the config matcher (since ~v1.0.63); VS Code (Preview) parses
        # it but IGNORES it, so there the script fires on EVERY tool call —
        # reads, edits, everything. This in-script filter is the only tool
        # filter you control on every surface, and it must exit 0 fast or (on
        # surfaces without matching) every file read pays the gate's latency.
        # Load-bearing decision #1 of 4.
        sys.exit(0)

    tool_input = get_field(event, "tool_input", "toolInput", default={}) or {}
    command = str(get_field(tool_input, "command", "cmd", default=""))

    for rule, reason in DENY_RULES:
        if rule.search(command):
            deny(reason, event)

    m = FORCE_PUSH_RE.search(command)
    if m and FORCE_FLAG_RE.search(m.group("rest")) and branch_is_protected(m.group("rest")):
        deny("force-push to a protected branch is denied by policy "
             f"(protected: {', '.join(protected_branches())})", event)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # malformed JSON, unexpected payload shape, any bug
        # WHY: FAIL CLOSED — a broken guard must block, not silently allow.
        # Malformed JSON, an unexpected payload shape, or a bug in your own
        # deny rule all land here and emit the full deny signal set (stdout
        # JSON + stderr + exit code). test_fails_closed_on_malformed_json
        # pins this behavior. Load-bearing decision #4 of 4.
        reason = f"guard error ({exc})"
        print(json.dumps({
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }))
        print(f"BLOCKED by block_destructive hook: {reason}", file=sys.stderr)
        sys.exit(int(os.environ.get("BLOCK_EXIT_CODE", "2")))
