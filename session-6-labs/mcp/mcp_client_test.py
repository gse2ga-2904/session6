#!/usr/bin/env python3
# =============================================================================
# mcp_client_test.py — client-side verification for the bosch-canlog server
#
# What:     Spawns mcp_server.py over stdio using the FastMCP client and
#           verifies the production posture end-to-end:
#             1. the trace-summary resource is readable
#             2. an unconfirmed write returns PENDING_CONFIRMATION (human gate)
#             3. a confirmed write executes and returns a ticket id
#             4. an invalid severity is DENIED
#             5. the audit log gained one JSONL line per call
#
# Used by:  Session 3 · Lab 3-B (checkpoint: "client test green") and as the
#           basis of the CI compliance check in Lab 3-C.
#
# Run:      pip install fastmcp
#           export BOSCH_MCP_TOKEN=dev-placeholder-token
#           python mcp_client_test.py
# =============================================================================

import asyncio
import json
import os
import sys

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

SERVER = "mcp_server.py"
AUDIT = os.environ.get("AUDIT_LOG_PATH", "audit.log.jsonl")


def _audit_lines() -> int:
    if not os.path.exists(AUDIT):
        return 0
    with open(AUDIT, encoding="utf-8") as f:
        return sum(1 for _ in f)


async def main() -> int:
    if not os.environ.get("BOSCH_MCP_TOKEN"):
        print("FAIL: BOSCH_MCP_TOKEN not set — see secrets-setup.md")
        return 1

    failures = 0
    lines_before = _audit_lines()

    # Spawn the server over stdio, passing our environment through explicitly
    # (secrets travel via env, never via args — and stdio children do not
    # inherit the parent env by default in all client versions).
    transport = PythonStdioTransport(SERVER, env=dict(os.environ))
    async with Client(transport) as client:
        # -- 1. resource read -------------------------------------------------
        res = await client.read_resource("canlog://TRC-2031/summary")
        body = res[0].text
        ok = "bus-off" in body and "TRC-2031" in body
        print(f"[{'ok' if ok else 'FAIL'}] resource read: canlog://TRC-2031/summary")
        failures += 0 if ok else 1

        # -- 2. human gate blocks the unconfirmed write -----------------------
        r = await client.call_tool(
            "create_defect_ticket",
            {"title": "Bus-off on BCM during cold start",
             "severity": "high", "trace_id": "TRC-2031"},
        )
        status = json.loads(r.content[0].text).get("status")
        ok = status == "PENDING_CONFIRMATION"
        print(f"[{'ok' if ok else 'FAIL'}] human gate: unconfirmed write -> {status}")
        failures += 0 if ok else 1

        # -- 3. confirmed write executes --------------------------------------
        r = await client.call_tool(
            "create_defect_ticket",
            {"title": "Bus-off on BCM during cold start",
             "severity": "high", "trace_id": "TRC-2031", "confirm": True},
        )
        payload = json.loads(r.content[0].text)
        ok = payload.get("status") == "CREATED" and "ticket" in payload
        print(f"[{'ok' if ok else 'FAIL'}] confirmed write -> {payload.get('status')}")
        failures += 0 if ok else 1

        # -- 4. invalid severity denied ---------------------------------------
        r = await client.call_tool(
            "create_defect_ticket",
            {"title": "x", "severity": "catastrophic", "confirm": True},
        )
        status = json.loads(r.content[0].text).get("status")
        ok = status == "DENIED"
        print(f"[{'ok' if ok else 'FAIL'}] invalid severity -> {status}")
        failures += 0 if ok else 1

    # -- 5. audit trail grew (>= 4 new lines: 1 read + 3 writes) --------------
    new_lines = _audit_lines() - lines_before
    ok = new_lines >= 4
    print(f"[{'ok' if ok else 'FAIL'}] audit log: +{new_lines} JSONL lines in {AUDIT}")
    failures += 0 if ok else 1

    print("\nRESULT:", "ALL CHECKS PASSED" if failures == 0 else f"{failures} FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
