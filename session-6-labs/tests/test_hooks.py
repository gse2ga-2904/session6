#!/usr/bin/env python3
"""test_hooks.py — unit tests for the Session 1 hook scripts.

Course: Agent Operations (Copilot edition) · Session 1 · Activity A1.2 / Lab L1.5
Run:    python3 -m pytest tests/test_hooks.py -v   (from the labs-repo root)
        (subset: -k destructive / -k siem · always `python3 -m pytest`: immune to PATH)

The point (Session 1.2 slide "Performance, testing, failure modes"): a hook script is
just a program reading JSON on stdin. Feed it fixture events, assert on exit code and
stderr — no agent required. Fixtures deliberately cover BOTH payload casings
(snake_case = Claude Code, camelCase = Copilot) because the scripts must accept both.

NOTE: block_destructive.py ships COMPLETE — these tests are green out of the box.
Lab A1.2 step 5 asks you to ADD one deny rule and one test of your own below
(copy an existing TestDestructiveBlocker test, change the command). If you take
the async stretch and rebuild from the skeleton
(course kit: session-1/code/hooks/scripts/block_destructive_skeleton.py), the
destructive tests go red until your TODOs are done — that's the exercise.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
BLOCKER = HERE.parent / ".github" / "hooks" / "scripts" / "block_destructive.py"
SIEM = HERE.parent / ".github" / "hooks" / "scripts" / "siem_logger.py"

EXIT_ALLOW = 0
EXIT_BLOCK = 2


def run_hook(script: Path, event, env=None) -> subprocess.CompletedProcess:
    """Run a hook script exactly as the agent runtime would: JSON on stdin."""
    payload = event if isinstance(event, str) else json.dumps(event)
    full_env = {**os.environ, **(env or {})}
    # Keep test runs side-effect free: the blocker's gate-decision trace
    # (.github/hooks/scripts/_trace.py) must not append to hook-trace.jsonl.
    full_env.setdefault("HOOK_TRACE_FILE", os.devnull)
    return subprocess.run(
        [sys.executable, str(script)],
        input=payload, capture_output=True, text=True, timeout=10, env=full_env,
    )


def shell_event(command: str, casing: str = "snake") -> dict:
    if casing == "camel":
        return {"hookEventName": "PreToolUse", "toolName": "shell",
                "toolInput": {"command": command}}
    return {"hook_event_name": "PreToolUse", "tool_name": "bash",
            "tool_input": {"command": command}}


# ---------------------------------------------------------------- destructive blocker

class TestDestructiveBlocker:
    def test_blocks_rm_rf(self):
        r = run_hook(BLOCKER, shell_event("rm -rf /"))
        assert r.returncode == EXIT_BLOCK
        assert "BLOCKED" in r.stderr  # readable reason the agent can learn from

    def test_blocks_rm_fr_reversed_flags(self):
        r = run_hook(BLOCKER, shell_event("rm -fr build/"))
        assert r.returncode == EXIT_BLOCK

    def test_blocks_rm_rf_camelcase_payload(self):
        # Copilot sends camelCase fields — the caveat from slide 1.2.
        r = run_hook(BLOCKER, shell_event("rm -rf src/", casing="camel"))
        assert r.returncode == EXIT_BLOCK

    def test_blocks_force_push_to_main(self):
        r = run_hook(BLOCKER, shell_event("git push --force origin main"))
        assert r.returncode == EXIT_BLOCK
        assert "protected" in r.stderr.lower()

    def test_blocks_short_force_flag(self):
        r = run_hook(BLOCKER, shell_event("git push -f origin master"))
        assert r.returncode == EXIT_BLOCK

    def test_blocks_force_push_release_wildcard(self):
        r = run_hook(BLOCKER, shell_event("git push --force origin release/2026.07"))
        assert r.returncode == EXIT_BLOCK

    def test_allows_safe_command(self):
        r = run_hook(BLOCKER, shell_event("cat config.yaml"))
        assert r.returncode == EXIT_ALLOW

    def test_allows_plain_push(self):
        r = run_hook(BLOCKER, shell_event("git push origin feature/can-parser"))
        assert r.returncode == EXIT_ALLOW

    def test_allows_force_push_to_feature_branch(self):
        r = run_hook(BLOCKER, shell_event("git push --force origin feature/spike"))
        assert r.returncode == EXIT_ALLOW

    def test_ignores_non_shell_tools_fast(self):
        # On VS Code matchers are ignored, so the script sees read/edit events too
        # and must exit 0 immediately (performance slide).
        event = {"hook_event_name": "PreToolUse", "tool_name": "read",
                 "tool_input": {"file_path": "src/can_parser.py"}}
        r = run_hook(BLOCKER, event)
        assert r.returncode == EXIT_ALLOW


    def test_deny_emits_portable_json_decision(self):
        # Blocking semantics differ per surface (Jul 2026): VS Code blocks on
        # exit 2 + stderr; Copilot CLI / cloud agent block on stdout JSON
        # permissionDecision="deny". The deny path must emit BOTH signals.
        r = run_hook(BLOCKER, shell_event("rm -rf /"))
        d = json.loads(r.stdout)
        assert d["permissionDecision"] == "deny"
        assert d["permissionDecisionReason"]
        assert d["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_block_exit_code_env_override(self):
        # Pre-flight escape hatch: if the live CLI ignores stdout JSON when the
        # exit code is 2, BLOCK_EXIT_CODE=0 lets the JSON deny be parsed.
        r = run_hook(BLOCKER, shell_event("rm -rf /"), env={"BLOCK_EXIT_CODE": "0"})
        assert r.returncode == 0
        assert json.loads(r.stdout)["permissionDecision"] == "deny"


    def test_blocks_vscode_payload_tool_name(self):
        # VS Code (Preview) sends its own tool names (e.g. runTerminalCommand)
        # — a filter that only knows CLI names silently allows everything in
        # the VS Code GUI. This pins the VS Code name.
        event = {"hookEventName": "PreToolUse", "toolName": "runTerminalCommand",
                 "toolInput": {"command": "rm -rf build/"}}
        r = run_hook(BLOCKER, event)
        assert r.returncode == EXIT_BLOCK
        assert json.loads(r.stdout)["permissionDecision"] == "deny"

    def test_fails_closed_on_malformed_json(self):
        # A crashing guard must BLOCK, not silently allow.
        r = run_hook(BLOCKER, "this is not json {")
        assert r.returncode == EXIT_BLOCK

    def test_protected_branches_env_override(self):
        env = {"PROTECTED_BRANCHES": "develop"}
        r = run_hook(BLOCKER, shell_event("git push --force origin develop"), env=env)
        assert r.returncode == EXIT_BLOCK
        r2 = run_hook(BLOCKER, shell_event("git push --force origin qa-lane"), env=env)
        assert r2.returncode == EXIT_ALLOW


# ---------------------------------------------------------------------- SIEM logger

class TestSiemLogger:
    def test_appends_ndjson_record(self, tmp_path):
        log = tmp_path / "siem.ndjson"
        event = {"hook_event_name": "PostToolUse", "session_id": "s-123",
                 "tool_name": "bash", "tool_input": {"command": "pytest"},
                 "tool_result_status": "ok"}
        r = run_hook(SIEM, event, env={"SIEM_LOG_PATH": str(log)})
        assert r.returncode == 0
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["event"] == "PostToolUse"
        assert rec["tool"] == "bash"
        assert rec["target"] == "pytest"
        assert rec["session_id"] == "s-123"

    def test_accepts_camelcase_payload(self, tmp_path):
        log = tmp_path / "siem.ndjson"
        event = {"hookEventName": "PostToolUse", "sessionId": "s-456",
                 "toolName": "edit", "toolInput": {"filePath": "src/can_parser.py"}}
        r = run_hook(SIEM, event, env={"SIEM_LOG_PATH": str(log)})
        assert r.returncode == 0
        rec = json.loads(log.read_text().strip())
        assert rec["tool"] == "edit"
        assert rec["target"] == "src/can_parser.py"

    def test_never_blocks_even_on_garbage(self, tmp_path):
        # Observer contract: exit 0 no matter what.
        r = run_hook(SIEM, "not json at all",
                     env={"SIEM_LOG_PATH": str(tmp_path / "x.ndjson")})
        assert r.returncode == 0

    def test_does_not_log_full_file_contents(self, tmp_path):
        # Privacy rule: targets and outcomes, not contents.
        log = tmp_path / "siem.ndjson"
        secret_body = "SUPER_SECRET_CALIBRATION_BLOB"
        event = {"hook_event_name": "PostToolUse", "tool_name": "write",
                 "tool_input": {"file_path": "src/x.py", "content": secret_body}}
        run_hook(SIEM, event, env={"SIEM_LOG_PATH": str(log)})
        assert secret_body not in log.read_text()
