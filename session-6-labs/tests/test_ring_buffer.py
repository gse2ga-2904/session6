"""test_ring_buffer.py — PARTIAL pytest suite for ring_buffer.py (~80% line coverage).

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 5 · Lab 5.2 — this is the STARTING suite. Your job: feed the
          pytest-cov gap list (`--cov-report=term-missing`) to Copilot,
          generate tests for the uncovered branches, keep only tests that run
          + pass + add coverage, then run mutation_check.py to prove every
          kept test can fail.
How to run: ./tests/coverage.sh   (pytest + pytest-cov)

Deliberately NOT covered here (the lab's targets):
  - constructor rejection paths (capacity 0, capacity > RB_MAX_CAPACITY)
  - full-buffer behavior for BOTH overwrite policies
  - get() / peek() on an empty buffer
  - wrap-around across the capacity boundary
  - reset() preserving capacity/policy (only "empties" is tested)
"""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
# Import order matters: a mutant copy dropped next to this file by
# mutation_check.py must win over the real module in ../src.
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from ring_buffer import RingBuffer  # noqa: E402


@pytest.fixture
def rb():
    return RingBuffer(8, overwrite=False)


def test_starts_empty(rb):
    assert rb.is_empty()
    assert not rb.is_full()
    assert rb.size() == 0


def test_put_increases_size(rb):
    assert rb.put(0x41)
    assert rb.size() == 1
    assert not rb.is_empty()


def test_get_returns_fifo_order(rb):
    assert rb.put(0x01)
    assert rb.put(0x02)
    assert rb.put(0x03)

    assert rb.get() == 0x01
    assert rb.get() == 0x02
    assert rb.get() == 0x03
    assert rb.is_empty()


def test_peek_does_not_consume(rb):
    assert rb.put(0x7E)

    assert rb.peek() == 0x7E
    assert rb.size() == 1   # still there


def test_fills_to_capacity(rb):
    for i in range(8):
        assert rb.put(i)
    assert rb.is_full()
    assert rb.size() == 8


def test_reset_empties_buffer(rb):
    assert rb.put(0x10)
    assert rb.put(0x20)
    rb.reset()
    assert rb.is_empty()
    assert rb.size() == 0


# DELIBERATELY WEAK (Lab 5.2 demo — "delete it live"): this test exercises
# put() but asserts nothing about observable state (size, order, contents).
# It passes no matter how the counters or indices are mutated, so
# `mutation_check.py --per-test` flags it with "<-- DECORATION? delete or
# strengthen": it executes lines without verifying behavior. Coverage counts
# it; mutation testing exposes it. Strengthen or delete it in the lab.
def test_put_some_bytes_runs_without_error(rb):
    for i in range(4):
        rb.put(i)   # return value ignored; no assertion on state
    assert True     # asserts nothing real — that's the point
