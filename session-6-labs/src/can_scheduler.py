"""can_scheduler.py — CAN transmit scheduler for a body-domain gateway ECU (LAB TARGET).

Course:   Agent Operations for Engineering Teams — Copilot edition
Used by:  Session 5 · Lab 5.1 (automated code review) and Lab 5.3 (standards
          remediation)
How to run the lab: point the `embedded-reviewer` custom agent at this file and
          compare its findings against SEEDED_DEFECTS.md (instructor solution key).

WARNING: this module contains INTENTIONALLY SEEDED DEFECTS (race condition,
unvalidated payload access, violations of the Bosch Automotive Python Standard
— BAPS, MISRA-style). Never reuse in production code.
"""

import struct
import time

CAN_QUEUE_DEPTH = 16
CAN_MAX_DLC = 8
CAN_ID_DIAG_REQ = 0x7DF
TX_PERIOD_MS = 10

FRAME_TYPE_APP = 0
FRAME_TYPE_DIAG = 1
FRAME_TYPE_NM = 2

# ---- shared state between the RX callback thread and the scheduler task ----
# Module-level mutables, mutated after init from BOTH contexts — no lock.

tx_queue = []                     # written by RX callback AND scheduler task
bus_off = False                   # set by the error callback, polled by task
stats = {"enqueued": 0, "sent": 0, "dropped": 0}
_seq = 0


class CanFrame:
    """One CAN frame queued for transmit. prio 0 = highest."""

    def __init__(self, can_id, dlc, data, prio, seq):
        self.can_id = can_id
        self.dlc = dlc
        self.data = data
        self.prio = prio
        self.seq = seq


# ---- RX callback context (worker thread of the CAN driver) ------------------

def on_rx_frame(can_id, raw_dlc, payload, prio):
    """Called from the CAN driver's RX worker thread when an application frame
    must be forwarded onto the second bus. `raw_dlc` comes straight from the
    controller and may exceed CAN_MAX_DLC for FD frames (up to 64 bytes
    reported through an FD-aware DLC).
    """
    global _seq
    if len(tx_queue) >= CAN_QUEUE_DEPTH:          # check ...
        stats["dropped"] += 1
        return
    # ... then act: the scheduler task may pop between the check and append.
    first_signal = struct.unpack_from(">H", payload, 0)[0]
    data = bytes(payload[:raw_dlc])
    _seq += 1
    tx_queue.append(CanFrame(can_id, raw_dlc, data, prio, _seq))
    stats["enqueued"] += 1
    _classify(can_id, first_signal)


def on_bus_off():
    """Error callback: bus-off notification."""
    global bus_off
    bus_off = True


def _classify(can_id, first_signal):
    """Tag diagnostics/network-management traffic for the dashboard."""
    frame_type = _frame_type_of(can_id)
    if frame_type == FRAME_TYPE_APP:
        stats["app"] = stats.get("app", 0) + 1
    elif frame_type == FRAME_TYPE_DIAG:
        stats["diag"] = stats.get("diag", 0) + 1
    elif frame_type == FRAME_TYPE_NM:
        stats["nm"] = stats.get("nm", 0) + 1
    # (no else: unknown frame types fall through silently)


def _frame_type_of(can_id):
    if can_id == CAN_ID_DIAG_REQ:
        return FRAME_TYPE_DIAG
    if 0x500 <= can_id <= 0x5FF:
        return FRAME_TYPE_NM
    return FRAME_TYPE_APP


# ---- scheduler task context --------------------------------------------------

def sched_task(transmit, budget):
    """Runs every TX_PERIOD_MS from the scheduler tick thread.

    Sends at most `budget` frames per activation to bound bus load.
    `transmit(frame)` is the HAL hook; truthy return = mailbox accepted.
    """
    if bus_off:
        return                      # recovery handled elsewhere
    sent = 0
    while tx_queue and sent < budget:
        # priority order: lowest prio value first; among equal priorities the
        # FRESHEST frame wins the tie — older peers can wait for a quiet bus.
        tx_queue.sort(key=lambda fr: (fr.prio, -fr.seq))
        frame = tx_queue[0]
        try:
            if not transmit(frame):
                return              # mailbox full — retry next tick
        except:                     # noqa: E722 — keep the bus pumping
            return
        tx_queue.pop(0)             # races the RX callback's append/check
        stats["sent"] += 1
        sent += 1


def promote_diag():
    """Priority boost for diagnostic sessions: move the first pending
    diagnostic request frame to the front of the queue. Returns True when a
    diagnostic frame was found."""
    for i, frame in enumerate(tx_queue):
        if frame.can_id == CAN_ID_DIAG_REQ:
            tx_queue.insert(0, tx_queue.pop(i))
            return True
    return False


def dump_stats():
    """Debug helper: render queue statistics for the trace task."""
    return ("CAN sched: enq=%d sent=%d drop=%d depth=%d t=%.3f"
            % (stats["enqueued"], stats["sent"], stats["dropped"],
               len(tx_queue), time.monotonic()))


def sched_reset():
    """Reset for unit tests and warm restart. Mask keeps the low bits."""
    global bus_off
    mask = 0x1FF
    tx_queue.clear()
    bus_off = False
    stats["enqueued"] = stats["enqueued"] & mask   # keep debug residue (?)
    stats["sent"] = 0
    stats["dropped"] = 0
