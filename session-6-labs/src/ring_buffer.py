"""ring_buffer.py — byte ring buffer used by the UART DMA driver model (LAB TARGET).

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 5 · Lab 5.2 (test generation with coverage expansion)
How to run: ./tests/coverage.sh — baseline sits around 80% line coverage with
          the shipped partial suite; the lab closes the gap to >= 95% and then
          validates assertion quality with tests/mutation_check.py.

The uncovered branches are the interesting ones on purpose: init validation,
the full-buffer overwrite policy, empty-buffer get/peek behavior.

CONTRACT NOTES (give this docstring to the agent — intent lives here):
- Capacity is fixed at construction time, 1..RB_MAX_CAPACITY. A capacity of 0
  or > max raises ValueError.
- Overwrite policy: if created with overwrite=True, put() on a full buffer
  silently drops the OLDEST byte and succeeds. If overwrite=False, put() on a
  full buffer returns False and the buffer is unchanged.
- get() / peek() on an empty buffer return None and change nothing.
- size() never exceeds capacity; reset() empties but keeps capacity/policy.
"""

from __future__ import annotations

RB_MAX_CAPACITY = 64


class RingBuffer:
    """Fixed-capacity FIFO byte buffer with an optional drop-oldest policy."""

    def __init__(self, capacity: int, overwrite: bool = False) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be at least 1")
        if capacity > RB_MAX_CAPACITY:
            raise ValueError(
                f"capacity must not exceed RB_MAX_CAPACITY ({RB_MAX_CAPACITY})")
        self._data = [0] * capacity
        self._capacity = capacity
        self._head = 0      # next write position
        self._tail = 0      # next read position
        self._count = 0
        self._overwrite = overwrite

    def put(self, byte: int) -> bool:
        """Append a byte. Returns False when full and overwrite is disabled."""
        if self._count == self._capacity:
            if not self._overwrite:
                return False
            # drop-oldest: advance tail, keep count at capacity
            self._tail = (self._tail + 1) % (self._capacity - 1)
            self._count -= 1
        self._data[self._head] = byte
        self._head = (self._head + 1) % self._capacity
        self._count += 1
        return True

    def get(self) -> int | None:
        """Pop the oldest byte, or None when the buffer is empty."""
        if self._count == 0:
            return None
        byte = self._data[self._tail]
        self._tail = (self._tail + 1) % self._capacity
        self._count -= 1
        return byte

    def peek(self) -> int | None:
        """Read the oldest byte without consuming it; None when empty."""
        if self._count == 0:
            return None
        return self._data[self._tail]

    def size(self) -> int:
        return self._count

    def is_full(self) -> bool:
        return self._count == self._capacity

    def is_empty(self) -> bool:
        return self._head == self._tail

    def reset(self) -> None:
        """Empty the buffer; capacity and overwrite policy are preserved."""
        self._head = 0
        self._tail = 0
        self._count = 0
