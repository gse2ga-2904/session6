#!/usr/bin/env python3
"""validate_findings.py — CI gate: validate reviewer output against the findings schema.

Course: Agent Operations (Copilot edition) · Session 1 · Activity A1.4 / Lab L1.5.
Run:    python3 ci/validate_findings.py review.json
        python3 ci/validate_findings.py review.json --fail-on high   # stretch goal
Exit:   0 = schema-valid (and no findings at/above --fail-on level, if given)
        1 = invalid output or gate tripped

Deliberately dependency-free (no jsonschema package): it hand-validates the small
contract in ci/findings.schema.json so the lab needs no pip installs. The schema file
remains the canonical contract for tooling that does use a real validator.

Tolerance: strips a single ```/```json fence pair with a WARNING — models sometimes
add fences despite the chat mode. CI tolerates it once; the warning tells you to
tighten the mode. Everything else is strict.
"""

import argparse
import json
import sys

SEVERITIES = ("high", "med", "low")
REQUIRED = ("severity", "rule", "line", "msg")
SEV_RANK = {"low": 0, "med": 1, "high": 2}


def strip_fences(text: str) -> tuple[str, bool]:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines), True
    return t, False


def validate(findings) -> list[str]:
    errors = []
    if not isinstance(findings, list):
        return ["top level must be a JSON array"]
    for i, f in enumerate(findings):
        where = f"finding[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{where}: must be an object")
            continue
        for key in REQUIRED:
            if key not in f:
                errors.append(f"{where}: missing required key '{key}'")
        extra = set(f) - set(REQUIRED)
        if extra:
            errors.append(f"{where}: unexpected keys {sorted(extra)}")
        if "severity" in f and f["severity"] not in SEVERITIES:
            errors.append(f"{where}: severity '{f['severity']}' not in {SEVERITIES}")
        if "line" in f and (not isinstance(f["line"], int) or isinstance(f["line"], bool)
                            or f["line"] < 1):
            errors.append(f"{where}: line must be an integer >= 1")
        if "rule" in f and (not isinstance(f["rule"], str) or not 1 <= len(f["rule"]) <= 32):
            errors.append(f"{where}: rule must be a string of 1..32 chars")
        if "msg" in f and (not isinstance(f["msg"], str) or not 1 <= len(f["msg"]) <= 500):
            errors.append(f"{where}: msg must be a string of 1..500 chars")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="reviewer output file (JSON)")
    ap.add_argument("--fail-on", choices=SEVERITIES, default=None,
                    help="also fail if any finding at/above this severity exists")
    args = ap.parse_args()

    raw = open(args.file, encoding="utf-8").read()
    text, fenced = strip_fences(raw)
    if fenced:
        print("WARNING: markdown fences stripped — tighten the ci-review chat mode",
              file=sys.stderr)

    try:
        findings = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"FAIL: not valid JSON ({exc})", file=sys.stderr)
        return 1

    errors = validate(findings)
    if errors:
        print("FAIL: schema violations:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: schema valid · {len(findings)} finding(s)")

    if args.fail_on is not None:
        threshold = SEV_RANK[args.fail_on]
        hits = [f for f in findings if SEV_RANK[f["severity"]] >= threshold]
        if hits:
            print(f"GATE: {len(hits)} finding(s) at severity >= {args.fail_on} — red",
                  file=sys.stderr)
            return 1
        print(f"GATE: no findings at severity >= {args.fail_on} — green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
