#!/usr/bin/env bash
#
# coverage.sh — run the ring_buffer pytest suite with coverage
#
# Course:   Agent Operations for Engineering Teams — Copilot edition
# Used by:  Session 5 · Lab 5.2 (test generation with coverage expansion)
#           labs-repo copy: the module under test lives in ../src/ring_buffer.py
# How to run:
#     ./coverage.sh          run tests, print the line-coverage gap list
#     ./coverage.sh html     additionally generate an HTML report in ./cov-html/
#     ./coverage.sh clean    remove coverage artifacts
#
# Requirements: Python 3.10+ with pytest and pytest-cov:
#     pip install pytest pytest-cov
# No other toolchain — everything runs on stock Python.
#
# The interesting output is the coverage "gap list" (the Missing column):
# feed the uncovered lines to the agent (step 3 of the lab) — never ask it to
# guess what is untested.

set -euo pipefail
cd "$(dirname "$0")"

PY=${PY:-python3}

if [[ "${1:-}" == "clean" ]]; then
    rm -rf cov-html .coverage .coverage.* .pytest_cache __pycache__
    echo "cleaned."
    exit 0
fi

if ! "$PY" -c "import pytest" 2>/dev/null; then
    echo "ERROR: pytest not found — cannot run the coverage lab." >&2
    echo "Install the test toolchain:  pip install pytest pytest-cov" >&2
    echo "Or run this lab in GitHub Codespaces, which has unrestricted pip." >&2
    exit 1
fi
if ! "$PY" -c "import pytest_cov" 2>/dev/null; then
    echo "ERROR: pytest-cov not found — line coverage needs it." >&2
    echo "Install it:  pip install pytest-cov" >&2
    exit 1
fi

ARGS=(--cov=ring_buffer --cov-report=term-missing)
if [[ "${1:-}" == "html" ]]; then
    ARGS+=(--cov-report=html:cov-html)
fi

echo "== run + coverage =="
"$PY" -m pytest test_ring_buffer.py -q "${ARGS[@]}"

echo
echo "Uncovered lines in ring_buffer.py are in the 'Missing' column above —"
echo "feed that gap list to the agent (never ask it to guess what is untested)."
if [[ "${1:-}" == "html" ]]; then
    echo "HTML report: $(pwd)/cov-html/index.html"
else
    echo "(run './coverage.sh html' for the annotated per-line report)"
fi
