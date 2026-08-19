#!/usr/bin/env python3
"""
mutation_check.py — quick mutation-testing smoke check for the ring_buffer lab

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 5 · Lab 5.2 (evals mindset: a test that can't fail isn't a test)
          labs-repo copy: the module under test lives in ../src/ring_buffer.py.
How to run:
    python3 mutation_check.py                 # full-suite verdict per mutant
    python3 mutation_check.py --per-test      # also attribute kills per test case
    python3 mutation_check.py --keep-going    # don't stop on a surviving mutant

What it does:
    1. Parses ring_buffer.py with `ast` and generates mutants by flipping ONE
       operator at a time: '<' -> '<=', '>' -> '>=', '+' -> '-', '==' -> '!=',
       'and' -> 'or'.
    2. Writes the mutant to a temp copy next to a copy of the test suite (the
       suite imports the module beside it first, so the mutant wins).
    3. Runs pytest. A mutant is KILLED if the suite fails; a mutant that
       SURVIVES means no test observes that behavior — your assertions are
       decoration on that path.
    4. With --per-test, runs each test case separately (pytest node ids) so the
       lab rule can be enforced: EVERY kept test must kill at least one mutant.

This is NOT full mutation testing (see mutmut/cosmic-ray for that) — it is a
ten-minute independent signal for assertion quality, which is the point of the
lesson: verify with ground truth, never with the model's self-assessment.

Requirements: Python 3.10+, pytest (same as coverage.sh). Stdlib otherwise.
Exit code: 0 = all applicable mutants killed; 1 = survivors; 2 = fatal.
"""

from __future__ import annotations

import argparse
import ast
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "src" / "ring_buffer.py"
TEST = HERE / "test_ring_buffer.py"   # override with --test (e.g. your expanded suite)

# One-flip operator table: (name, from-AST-op, to-AST-op)
OPERATOR_FLIPS = [
    ("lt-to-lte", ast.Lt, ast.LtE),
    ("gt-to-gte", ast.Gt, ast.GtE),
    ("add-to-sub", ast.Add, ast.Sub),
    ("eq-to-noteq", ast.Eq, ast.NotEq),
    ("and-to-or", ast.And, ast.Or),
]


class _Flip(ast.NodeTransformer):
    """Flip the `target`-th occurrence (0-based) of `src_op` to `dst_op`."""

    def __init__(self, src_op, dst_op, target: int):
        self.src_op, self.dst_op, self.target = src_op, dst_op, target
        self.seen = 0
        self.line = None

    def _maybe_flip(self, node, ops_attr: str):
        ops = getattr(node, ops_attr)
        if isinstance(ops, list):     # Compare.ops
            new = []
            for op in ops:
                if isinstance(op, self.src_op):
                    if self.seen == self.target:
                        new.append(self.dst_op())
                        self.line = node.lineno
                        self.seen += 1
                        continue
                    self.seen += 1
                new.append(op)
            setattr(node, ops_attr, new)
        else:                         # BinOp.op / BoolOp.op
            if isinstance(ops, self.src_op):
                if self.seen == self.target:
                    setattr(node, ops_attr, self.dst_op())
                    self.line = node.lineno
                self.seen += 1
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        return self._maybe_flip(node, "ops")

    def visit_BinOp(self, node):
        self.generic_visit(node)
        return self._maybe_flip(node, "op")

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        return self._maybe_flip(node, "op")


def count_sites(tree: ast.AST, src_op) -> int:
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            n += sum(isinstance(op, src_op) for op in node.ops)
        elif isinstance(node, (ast.BinOp, ast.BoolOp)):
            n += isinstance(node.op, src_op)
    return n


def generate_mutants(source: str) -> list[tuple[str, str]]:
    """Return [(name, mutated_source)] — one operator flip per mutant."""
    tree = ast.parse(source)
    mutants: list[tuple[str, str]] = []
    for name, src_op, dst_op in OPERATOR_FLIPS:
        for k in range(count_sites(tree, src_op)):
            flipper = _Flip(src_op, dst_op, k)
            mutated = flipper.visit(copy.deepcopy(tree))
            ast.fix_missing_locations(mutated)
            label = f"{name}-L{flipper.line}" if flipper.line else f"{name}-{k}"
            mutants.append((label, ast.unparse(mutated)))
    return mutants


def run_tests(workdir: Path, node_id: str | None = None) -> bool:
    """True = suite passed (mutant SURVIVED that run)."""
    target = TEST.name + (f"::{node_id}" if node_id else "")
    # PYTHONDONTWRITEBYTECODE: a cached .pyc validates on (mtime-second, size),
    # and a one-character operator flip keeps both — the stale baseline
    # bytecode would silently run instead of the mutant.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    shutil.rmtree(workdir / "__pycache__", ignore_errors=True)
    res = subprocess.run(
        [sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider"],
        cwd=workdir, capture_output=True, timeout=60, env=env)
    return res.returncode == 0


def list_tests(workdir: Path) -> list[str]:
    res = subprocess.run(
        [sys.executable, "-m", "pytest", TEST.name, "-q", "-p",
         "no:cacheprovider", "--collect-only"],
        cwd=workdir, capture_output=True, text=True)
    tests = []
    for line in res.stdout.splitlines():
        if "::" in line and not line.startswith(" "):
            tests.append(line.strip().split("::", 1)[1])
    return tests


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1].strip())
    ap.add_argument("--per-test", action="store_true",
                    help="attribute kills to individual test cases (slower)")
    ap.add_argument("--keep-going", action="store_true",
                    help="report all mutants even after a survivor is found")
    ap.add_argument("--test", type=Path, default=None,
                    help="alternative test suite (default: test_ring_buffer.py; "
                         "the lab's expanded suite or solutions/ suite goes here)")
    args = ap.parse_args()

    global TEST
    if args.test is not None:
        TEST = args.test.resolve()

    if not TEST.is_file():
        print(f"FATAL: test suite not found: {TEST}")
        return 2
    original = SOURCE.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="mutcheck-") as tmp:
        workdir = Path(tmp)
        shutil.copy(TEST, workdir / TEST.name)

        # Sanity baseline: unmutated code must pass.
        (workdir / "ring_buffer.py").write_text(original, encoding="utf-8")
        if not run_tests(workdir):
            print("FATAL: baseline tests fail on UNMUTATED code — fix the "
                  "suite before mutating (run ./coverage.sh first).")
            return 2

        mutants = generate_mutants(original)
        tests = list_tests(workdir) if args.per_test else []
        kills_per_test: dict[str, int] = {t: 0 for t in tests}
        survivors: list[str] = []

        print(f"baseline OK — {len(mutants)} mutants to try\n")
        for name, mutated in mutants:
            (workdir / "ring_buffer.py").write_text(mutated, encoding="utf-8")

            if run_tests(workdir):
                survivors.append(name)
                print(f"  [SURVIVED] {name:25s} <-- no test observes this behavior")
                if not args.keep_going and not args.per_test:
                    break
            else:
                print(f"  [killed]  {name}")
                if args.per_test:
                    for t in tests:
                        if not run_tests(workdir, node_id=t):
                            kills_per_test[t] += 1

        print("\n== verdict ==")
        if survivors:
            print(f"{len(survivors)} mutant(s) SURVIVED: {', '.join(survivors)}")
            print("Lab rule: add or strengthen tests until every mutant above "
                  "is killed.")
        else:
            print(f"all {len(mutants)} applicable mutant(s) killed — assertion "
                  "quality looks real.")

        if args.per_test:
            print("\nkills per test (every kept test must kill >= 1 mutant):")
            for t, k in sorted(kills_per_test.items(), key=lambda kv: kv[1]):
                flag = "  <-- DECORATION? delete or strengthen" if k == 0 else ""
                print(f"  {k:3d}  {t}{flag}")

        return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
