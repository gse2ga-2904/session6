#!/usr/bin/env python3
# =============================================================================
# check_standard.py — deterministic BAPS-subset scanner (training grade)
#
# What:     stdlib `ast` walk for the Bosch Automotive Python Standard (BAPS,
#           MISRA-style) training subset (see ../references/baps-rules-subset.md).
#           Deliberately simple: the pedagogical point is that the SKILL calls a
#           deterministic script instead of letting the model improvise rule
#           checks. NOT a qualified analyzer — at Bosch you would wire this to
#           Klocwork/Coverity for real compliance.
#
# Used by:  Session 4 · Lab 4-A (the /bosch:embedded-std-checker skill runs it),
#           Lab 4-C (adversarial review target), and Session 3's CI workflow.
#
# Run:      python check_standard.py --format table   file1.py file2.py ...
#           python check_standard.py --format markdown --output report.md src/
#           python check_standard.py --format count    src/     # mandatory count
#           python check_standard.py --format json     file.py  # findings JSON
#
# Exit code: 0 always for table/markdown/json (reporting tool); the CI workflow
#           enforces failure from the count. No network, no writes outside
#           --output. Stdlib only.
#
# JSON output matches the shared finding schema: {severity, rule, line, msg}.
# =============================================================================

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass

# BAPS rule catalog: id -> (severity, message). "mandatory" fails CI.
RULES = {
    "BAPS-01": ("mandatory",
                "payload/signal unpacked without a length check before the "
                "slice/struct.unpack"),
    "BAPS-02": ("advisory",
                "mutable module-global state is mutated after init "
                "(thread-safety)"),
    "BAPS-03": ("mandatory",
                "dispatch over frame/message type has no explicit else "
                "(unknown case unhandled)"),
    "BAPS-05": ("mandatory",
                "bare except / swallowed exception on a safety path "
                "(must re-raise or fail closed)"),
    "BAPS-06": ("mandatory",
                "eval/exec/dynamic import in a production path"),
}

_LEN_NAME_RE = re.compile(r"\b(dlc|len|length|size|count|nbytes)\b", re.I)


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    severity: str  # "mandatory" | "advisory"
    message: str


def _iter_functions(tree):
    """Yield every function/method node in the module."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _has_length_guard(func) -> bool:
    """True if the function performs any length check before a payload access."""
    for node in ast.walk(func):
        # a call to len(...)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "len":
            return True
        # a comparison against a length-shaped name (dlc/length/size/...)
        if isinstance(node, ast.Compare):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and _LEN_NAME_RE.search(sub.id):
                    return True
    return False


def _is_unpack(call) -> bool:
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr in ("unpack", "unpack_from"):
        return True
    return False


def _check_baps01(tree, path, findings):
    """Every struct.unpack in a function with no length guard."""
    for func in _iter_functions(tree):
        if _has_length_guard(func):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Call) and _is_unpack(node):
                sev, msg = RULES["BAPS-01"]
                findings.append(Finding(path, node.lineno, "BAPS-01", sev, msg))


def _module_globals(tree):
    """Return {name: lineno} for module-level names bound to a mutable object."""
    out = {}
    mutable_ctor = {"list", "dict", "set", "bytearray", "deque", "defaultdict"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            val = node.value
            mutable = isinstance(val, (ast.List, ast.Dict, ast.Set)) or (
                isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id in mutable_ctor)
            if not mutable:
                continue
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    out[tgt.id] = node.lineno
    return out


def _check_baps02(tree, path, findings):
    """Module-global mutable mutated inside a function (append/subscript/global)."""
    globals_ = _module_globals(tree)
    if not globals_:
        return
    mutated = set()
    for func in _iter_functions(tree):
        declared_global = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Global):
                declared_global.update(node.names)
        for node in ast.walk(func):
            # name.append(...) / name.pop() / name.clear() / name[...] = ...
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id in globals_ \
                    and node.func.attr in ("append", "extend", "insert", "pop",
                                           "clear", "update", "add",
                                           "popitem", "setdefault"):
                mutated.add(node.func.value.id)
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) \
                    else [node.target]
                for tgt in targets:
                    if isinstance(tgt, ast.Subscript) and \
                            isinstance(tgt.value, ast.Name) and \
                            tgt.value.id in globals_:
                        mutated.add(tgt.value.id)
                    if isinstance(tgt, ast.Name) and tgt.id in declared_global \
                            and tgt.id in globals_:
                        mutated.add(tgt.id)
    for name in sorted(mutated, key=lambda n: globals_[n]):
        sev, msg = RULES["BAPS-02"]
        findings.append(Finding(path, globals_[name], "BAPS-02", sev,
                                f"{msg}: '{name}'"))


def _check_baps03(tree, path, findings):
    """if/elif dispatch chain (>=1 elif) whose terminal branch has no else."""
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if id(node) in seen:
            continue
        # walk the elif chain
        elif_count = 0
        cur = node
        chain = [cur]
        while len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
            cur = cur.orelse[0]
            chain.append(cur)
            elif_count += 1
        for c in chain:
            seen.add(id(c))
        # dispatch = at least one elif, all tests are comparisons, no final else
        if elif_count >= 1 and not cur.orelse and \
                all(isinstance(c.test, (ast.Compare, ast.BoolOp)) for c in chain):
            sev, msg = RULES["BAPS-03"]
            findings.append(Finding(path, node.lineno, "BAPS-03", sev, msg))


def _swallows(handler) -> bool:
    """True if the handler body silently swallows (only pass/... and no raise)."""
    body = handler.body
    if any(isinstance(n, ast.Raise) for n in ast.walk(handler)):
        return False
    return all(
        isinstance(n, ast.Pass) or
        (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
        for n in body)


def _check_baps05(tree, path, findings):
    """Bare `except:` OR an except handler that silently swallows on a path."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and \
                (node.type is None or _swallows(node)):
            sev, msg = RULES["BAPS-05"]
            findings.append(Finding(path, node.lineno, "BAPS-05", sev, msg))


_DYNAMIC = {"eval", "exec", "__import__"}


def _check_baps06(tree, path, findings):
    """eval/exec/__import__/importlib.import_module calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in _DYNAMIC:
                sev, msg = RULES["BAPS-06"]
                findings.append(Finding(path, node.lineno, "BAPS-06", sev, msg))
            elif isinstance(f, ast.Attribute) and f.attr == "import_module":
                sev, msg = RULES["BAPS-06"]
                findings.append(Finding(path, node.lineno, "BAPS-06", sev, msg))


def scan_file(path: str) -> list[Finding]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError as e:
        return [Finding(path, 0, "-", "advisory", f"could not read file: {e}")]
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return [Finding(path, e.lineno or 0, "-", "advisory",
                        f"could not parse (not valid Python 3.10+): {e.msg}")]

    findings: list[Finding] = []
    _check_baps01(tree, path, findings)
    _check_baps02(tree, path, findings)
    _check_baps03(tree, path, findings)
    _check_baps05(tree, path, findings)
    _check_baps06(tree, path, findings)
    findings.sort(key=lambda f: (f.line, f.rule))
    return findings


def render(findings: list[Finding], fmt: str) -> str:
    mand = sum(1 for f in findings if f.severity == "mandatory")
    adv = len(findings) - mand
    files = len({f.path for f in findings})
    if fmt == "count":
        return str(mand)
    if fmt == "json":
        return json.dumps(
            [{"severity": f.severity, "rule": f.rule, "line": f.line,
              "msg": f.message, "file": f.path} for f in findings], indent=2)
    if not findings:
        return ("No findings — clean against the training subset."
                if fmt == "markdown" else "No findings.")
    n = len(findings)
    header = (f"{n} finding{'s' if n != 1 else ''} "
              f"({mand} mandatory, {adv} advisory) in {files} file(s).")
    if fmt == "markdown":
        rows = "\n".join(
            f"| `{f.path}` | {f.line} | {f.rule} | **{f.severity}** | {f.message} |"
            for f in findings)
        return (f"{header}\n\n| file | line | rule | severity | finding |\n"
                f"|---|---|---|---|---|\n{rows}")
    width = max(len(f.path) for f in findings)
    rows = "\n".join(
        f"{f.path:<{width}}  L{f.line:<5} {f.rule:<8} {f.severity:<9} {f.message}"
        for f in findings)
    return f"{header}\n{rows}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bosch training BAPS-subset scanner")
    ap.add_argument("files", nargs="+",
                    help="Python sources to scan (a directory scans its *.py "
                         "recursively, e.g. `check_standard.py src/`)")
    ap.add_argument("--format", choices=["table", "markdown", "count", "json"],
                    default="table")
    ap.add_argument("--output", help="write the report to this file instead of stdout")
    args = ap.parse_args()

    paths: list[str] = []
    for path in args.files:
        if os.path.isdir(path):
            paths.extend(sorted(
                os.path.join(root, name)
                for root, _dirs, names in os.walk(path) for name in names
                if name.endswith(".py")))
        else:
            paths.append(path)

    findings: list[Finding] = []
    scanned = skipped = 0
    for path in paths:
        if path.endswith(".py"):
            findings.extend(scan_file(path))
            scanned += 1
        else:
            skipped += 1
    findings.sort(key=lambda f: (f.path, f.line, f.rule))

    if scanned == 0 and skipped > 0 and args.format != "count":
        msg = (f"No Python files to scan ({skipped} non-.py file(s) skipped — "
               "this scanner is Python-only).")
        if args.output:
            open(args.output, "w", encoding="utf-8").write(msg + "\n")
        else:
            print(msg)
        return 0

    report = render(findings, args.format)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report + "\n")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
