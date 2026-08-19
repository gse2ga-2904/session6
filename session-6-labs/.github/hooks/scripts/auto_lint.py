#!/usr/bin/env python
# auto_lint.py — advisory PostToolUse hook: quick Python sanity check after agent edits.
#
# Course:   Agent Operations (Copilot edition) · Session 1 · Lab L1.5
# Wired by: .github/hooks/auto-lint.json (PostToolUse)
# Run:      invoked by the Copilot agent runtime with the hook event as JSON on stdin.
#           Manual test: echo '<event-json>' | python auto_lint.py
#
# Portability: stdlib-only Python — no bash, no shell. Hook commands must be
#           launchable from a GUI-started harness on Windows, where bash.exe is
#           not reliably on PATH; `python <script>` is the one form that works
#           on every course platform (auto_lint.sh remains as a deprecated stub).
#
# Rules:
#   * ADVISORY — always exits 0. Only the destructive blocker may exit non-zero.
#   * Filters in-script (Copilot parses but does not apply matchers): only acts on
#     edit/write-type tools touching .py files.
#   * Runs an `ast.parse` syntax check plus cheap BAPS-flavored heuristics —
#     a taste of the coding-standard mindset, not a qualified analyzer.
#     Session 5 wires the real source of truth (qualified static analyzer via MCP).
#   * Handles both payload casings: tool_input.file_path (Claude) vs .filePath (Copilot).

import ast
import json
import re
import os
import sys


def get(obj, *names, default=None):
    for n in names:
        if n in obj:
            return obj[n]
    return default


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return 0  # observers must survive malformed payloads

    tool = str(get(event, "tool_name", "toolName", default="")).lower()
    if tool not in {"edit", "write", "apply_patch", "applypatch", "create_file", "createfile",
                    # VS Code (Preview) payload names:
                    "editfiles", "edit_files", "create", "replace_string_in_file",
                    "insert_edit_into_file", "write_file"}:
        return 0  # not an edit-type tool; matchers aren't applied, so filter here

    ti = get(event, "tool_input", "toolInput", default={}) or {}
    path = get(ti, "file_path", "filePath", default="") or ""
    if not path.endswith(".py") or not os.path.isfile(path):
        return 0

    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        ast.parse(src, filename=path)
    except SyntaxError as e:
        print(f"auto_lint (advisory): {path} does not parse: "
              f"line {e.lineno}: {e.msg}")
        return 0

    # Heuristic BAPS-flavored checks — advisory only.
    notes = []
    if re.search(r"\bstruct\.unpack(_from)?\s*\(", src) and "len(" not in src:
        notes.append("struct.unpack without a visible len() check — "
                     "validate payload length first (BAPS-01)")
    if re.search(r"^\s*except\s*:", src, re.MULTILINE):
        notes.append("bare except: — safety paths must re-raise or fail "
                     "closed (BAPS-05)")
    if re.search(r"\beval\s*\(|\bexec\s*\(", src):
        notes.append("eval/exec — dynamic code execution is forbidden in "
                     "production paths (BAPS-06)")
    if notes:
        print(f"auto_lint (advisory, heuristic): {path}: " + "; ".join(notes))
    else:
        print(f"auto_lint (advisory): {path} clean (ast.parse + heuristics)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
