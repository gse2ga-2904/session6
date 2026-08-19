#!/usr/bin/env python3
# =============================================================================
# mcp_server.py — "bosch-canlog" corporate MCP tool server (FastMCP)
#
# What:     A production-posture MCP server exposing a CAN-log query service:
#           read-only *resources* for trace data and a human-gated *tool*
#           that creates defect tickets. Demonstrates the four production
#           concerns taught in Session 3.3:
#             1. resources vs tools (reads are resources; writes are tools)
#             2. human gate on every write (two-phase confirm)
#             3. secrets from a vault helper — never literals in code/config
#             4. structured JSONL audit logging for every call
#
# Used by:  Session 3 · Lab 3-B ("Build the bosch-canlog MCP server") and
#           reused by the CI compliance check in Lab 3-C.
#
# Run:      pip install fastmcp
#           export BOSCH_MCP_TOKEN=dev-placeholder-token   # see secrets-setup.md
#           python mcp_server.py                # serve over stdio
#           python mcp_server.py --selftest     # quick sanity check, no client
#
# Wire into VS Code: see mcp-config-vscode.json (.vscode/mcp.json).
# Test:     python mcp_client_test.py
#
# NOTE: All data is synthetic training data. All secrets are placeholders
#       resolved via environment variables (Vault/ASM in production —
#       see secrets-setup.md).
# =============================================================================

import hashlib
import json
import os
import sys
import time

from fastmcp import FastMCP

# -----------------------------------------------------------------------------
# 1) Secrets — vault helper.
#    Production: HashiCorp Vault / AWS Secrets Manager (see secrets-setup.md).
#    Training:   environment variables. NEVER hard-code a secret here or in
#    any committed mcp.json.
# -----------------------------------------------------------------------------
def vault(secret_name: str) -> str:
    """Fetch a secret. Env-var fallback for the training environment."""
    value = os.environ.get(secret_name)
    if not value:
        raise RuntimeError(
            f"Secret '{secret_name}' not set. Follow secrets-setup.md — "
            "do not paste secrets into code."
        )
    return value


SERVICE_TOKEN = vault("BOSCH_MCP_TOKEN")  # fail fast at startup if unset

# -----------------------------------------------------------------------------
# 2) Audit logging — one structured JSONL line per call.
#    GitHub's audit logs do NOT capture client-side prompts or local tool
#    calls; this file is what your SIEM ingests to close that gap.
# -----------------------------------------------------------------------------
AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit.log.jsonl")


def audit(kind: str, name: str, args: dict, decision: str) -> None:
    line = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actor": os.environ.get("MCP_ACTOR", "training-user"),
        "kind": kind,                       # "read" | "write"
        "name": name,                       # tool/resource name
        "args_sha256": hashlib.sha256(
            json.dumps(args, sort_keys=True).encode()
        ).hexdigest()[:16],                 # hash, not raw args (may hold PII)
        "decision": decision,               # "ok" | "pending" | "denied"
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


# -----------------------------------------------------------------------------
# Synthetic CAN trace store (stands in for the real log service / analyzer
# defect feed). Comment fields are deliberately included: they are *untrusted
# content* — an indirect-prompt-injection ingestion point (Session 3.2).
# -----------------------------------------------------------------------------
TRACES = {
    "TRC-2031": {
        "bus": "CAN1 (500 kbit/s)",
        "duration_s": 42.7,
        "frames": 18432,
        "events": [
            {"t": 12.402, "id": "0x18FF50E5", "event": "bus-off", "node": "BCM"},
            {"t": 12.911, "id": "0x18FF50E5", "event": "recovery", "node": "BCM"},
        ],
        "error_frames": 37,
        "comment": "Captured during cold-start bench test, rig B4.",
    },
    "TRC-2044": {
        "bus": "CAN2 (250 kbit/s)",
        "duration_s": 300.0,
        "frames": 91021,
        "events": [],
        "error_frames": 0,
        "comment": "Nominal endurance run.",
    },
}

# In-memory ticket tracker stub (stands in for Jira/ALM).
_TICKETS: list[dict] = []

mcp = FastMCP(
    "bosch-canlog",
    instructions=(
        "CAN-log query service for Bosch training. Trace summaries and error "
        "listings are read-only resources. Creating defect tickets is a gated "
        "write: the first call returns PENDING_CONFIRMATION and must be "
        "re-issued with confirm=true after explicit human approval."
    ),
)

# -----------------------------------------------------------------------------
# 3) RESOURCES — read-only data. No side effects, ever.
# -----------------------------------------------------------------------------
def _trace_summary(trace_id: str) -> str:
    """Read-only summary of a CAN trace: bus, duration, frame/event counts."""
    audit("read", "trace_summary", {"trace_id": trace_id}, "ok")
    trace = TRACES.get(trace_id)
    if trace is None:
        return f"Unknown trace '{trace_id}'. Known: {', '.join(sorted(TRACES))}"
    return json.dumps(
        {
            "trace_id": trace_id,
            "bus": trace["bus"],
            "duration_s": trace["duration_s"],
            "frames": trace["frames"],
            "error_frames": trace["error_frames"],
            "events": trace["events"],
            "comment": trace["comment"],
        },
        indent=2,
    )


# Register with the server. (The undecorated _trace_summary stays callable
# for the --selftest path regardless of FastMCP version internals.)
mcp.resource("canlog://{trace_id}/summary")(_trace_summary)

# Lab 3-B step 5 asks participants to add:
#   mcp.resource("canlog://{trace_id}/errors")  -> error frames only.


# -----------------------------------------------------------------------------
# 4) TOOLS — side effects, behind a human gate.
#    Two-phase confirm: call #1 (confirm=False) returns PENDING_CONFIRMATION;
#    the client shows it to the human; call #2 (confirm=True) executes.
#    (Spec-native alternative since rev 2025-06-18: elicitation — stretch goal.)
# -----------------------------------------------------------------------------
def _create_defect_ticket(
    title: str,
    severity: str,
    trace_id: str = "",
    confirm: bool = False,
) -> dict:
    """Create a defect ticket in the tracker (WRITE — requires confirmation).

    severity: one of 'low' | 'medium' | 'high' | 'safety-relevant'.
    First call must be made with confirm=false; execute only after a human
    has approved the returned summary by re-calling with confirm=true.
    """
    args = {"title": title, "severity": severity, "trace_id": trace_id}

    if severity not in ("low", "medium", "high", "safety-relevant"):
        audit("write", "create_defect_ticket", args, "denied")
        return {"status": "DENIED", "reason": f"invalid severity '{severity}'"}

    if not confirm:  # ---- HUMAN GATE ----
        audit("write", "create_defect_ticket", args, "pending")
        return {
            "status": "PENDING_CONFIRMATION",
            "action": f"Create {severity} defect ticket: '{title}'"
            + (f" (trace {trace_id})" if trace_id else ""),
            "instruction": "Ask the user to approve, then re-call with confirm=true.",
        }

    # Downstream auth: the server's own scoped credential — never the
    # client's token (token passthrough is forbidden by the MCP auth spec).
    _tracker_token = vault("TRACKER_TOKEN") if os.environ.get("TRACKER_TOKEN") \
        else SERVICE_TOKEN  # training fallback
    ticket = {
        "id": f"BOSCH-{1000 + len(_TICKETS) + 1}",
        "title": title,
        "severity": severity,
        "trace_id": trace_id,
    }
    _TICKETS.append(ticket)
    audit("write", "create_defect_ticket", args, "ok")
    return {"status": "CREATED", "ticket": ticket}


create_defect_ticket = mcp.tool(name="create_defect_ticket")(_create_defect_ticket)


# -----------------------------------------------------------------------------
# Self-test (no MCP client needed) and entry point
# -----------------------------------------------------------------------------
def _selftest() -> int:
    print("selftest: resource read …", end=" ")
    assert "bus-off" in _trace_summary("TRC-2031")
    print("ok")
    print("selftest: gate blocks unconfirmed write …", end=" ")
    r = _create_defect_ticket(title="t", severity="high")
    assert r["status"] == "PENDING_CONFIRMATION"
    print("ok")
    print("selftest: confirmed write executes …", end=" ")
    r = _create_defect_ticket(title="t", severity="high", confirm=True)
    assert r["status"] == "CREATED"
    print("ok")
    print("selftest: audit lines written …", end=" ")
    assert os.path.exists(AUDIT_LOG_PATH)
    print(f"ok ({AUDIT_LOG_PATH})")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    mcp.run()  # stdio transport; promote to Streamable HTTP for shared deploys
