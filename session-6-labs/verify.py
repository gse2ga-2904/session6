#!/usr/bin/env python3
"""verify.py — student kit verification. No `make` needed.

Run from the kit root:  python3 verify.py   (Windows/Git Bash: python verify.py)

Checks, headless, no Copilot seat, no network:
  1. src/can/can_parser.py byte-compiles — only once it exists (you add it in A1.3)
  2. hook unit tests are green (pytest — REQUIRED; if missing, this fails
     loudly and prints the exact install command for this same interpreter)
  3. the findings schema and the three hook JSON configs parse

block_destructive.py ships COMPLETE — the tests are green from the first run.
A failure is a real regression (often the deny rule you added in the A1.2
async step, or a broken fail-closed path). Fix it; don't skip it.

Exit code: 0 = passed (skips are named), 1 = a real failure.
"""

import json
import subprocess
import sys
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# This kit ships in every session, so the banner names whichever session it
# was built for: the folder is session-<N>-labs/.
_m = re.match(r"session-(\d+)-labs$", HERE.name)
SESSION = _m.group(1) if _m else "?"
PY = sys.executable
failures: list[str] = []
skips: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    print(f"Session {SESSION} kit verify · {HERE}\n")

    # 1. can_parser (arrives in A1.3 on your feature branch)
    parser = HERE / "src" / "can" / "can_parser.py"
    if parser.exists():
        r = subprocess.run([PY, "-m", "py_compile", str(parser)],
                           capture_output=True, text=True)
        check("build: src/can/can_parser.py byte-compiles", r.returncode == 0,
              r.stderr.strip()[:200])
    else:
        print("SKIP build — src/can/can_parser.py not present (arrives in A1.3)")

    # 2. hook unit tests — pytest is REQUIRED for Session 1, so a missing
    # install is a loud failure with the exact fix, not a quiet skip.
    # Note: we invoke via `-m pytest` with THIS interpreter (sys.executable),
    # so PATH problems with a bare `pytest` command can never bite here.
    if subprocess.run([PY, "-c", "import pytest"], capture_output=True).returncode == 0:
        r = subprocess.run([PY, "-m", "pytest", "tests/test_hooks.py", "-q"],
                           cwd=HERE, capture_output=True, text=True)
        check("hook unit tests (pytest)", r.returncode == 0,
              (r.stdout.strip().splitlines() or [""])[-1])
    else:
        exe = PY if " " not in PY else f'"{PY}"'
        check("hook unit tests (pytest)", False, "pytest is not installed for this Python")
        print(f"""
  FIX — run exactly this (installs pytest for the same Python running this script):
      {exe} -m pip install pytest
  If pip reports 'externally-managed-environment' or a permission error, use:
      {exe} -m pip install --user pytest
  Then re-run:  {exe} verify.py
  (Always use the `python3 -m ...` module form — bare `pytest`/`pip` commands
   depend on PATH and are the #1 cause of 'command not found'.)""")

    # 3. schema + hook configs parse
    try:
        json.loads((HERE / "ci" / "findings.schema.json").read_text())
        check("ci/findings.schema.json parses", True)
    except Exception as exc:  # noqa: BLE001
        check("ci/findings.schema.json parses", False, str(exc))
    for name in ("block-destructive", "siem-logger", "auto-lint"):
        path = HERE / ".github" / "hooks" / f"{name}.json"
        try:
            json.loads(path.read_text())
            check(f".github/hooks/{name}.json parses", True)
        except Exception as exc:  # noqa: BLE001
            check(f".github/hooks/{name}.json parses", False, str(exc))

    print()
    if failures:
        print(f"verify: FAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    if skips:
        print(f"verify: passed ({len(skips)} skipped: " + "; ".join(skips) + ")")
    else:
        print(f"verify: all Session {SESSION} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
