<!--
AGENTS.md — cross-vendor agent instructions file ("README for agents").
Course: Agent Operations (Copilot edition) · labs-repo (used Sessions 1–6).
Install: repo root (nested AGENTS.md per subdirectory also supported).
Notes:  read by 30+ tools including Copilot's coding agent; root or nested
        per directory.
        Do NOT confuse with .agent.md (a custom-agent persona definition in
        .github/agents/) — different file, different job.
        Treat entries as reviewed memory: settled facts only, with a verified date.
-->

# AGENTS.md — labs-repo (powertrain-sandbox)

## Build & test
- Verify everything headless: `make verify`
- Byte-compile + import-check the lab targets: `make build`
- Hook unit tests: `python -m pytest tests/test_hooks.py -v`
- Lint (advisory): `python .github/hooks/scripts/auto_lint.py` runs automatically
  after agent edits via hooks.

## Architecture facts (settled decisions only)
- CAN frame parsing is centralized in `src/can_parser.py` (the file first
  appears in Lab A1.3, committed on a feature branch as the review target);
  do not add parsers elsewhere. <!-- last_verified: 2026-07-14 -->
- `src/can_scheduler.py` contains INTENTIONALLY SEEDED DEFECTS (Session 5 lab
  target) — review it, never "clean it up" outside that lab.
  <!-- last_verified: 2026-07-14 -->
- The coding-standard compliance verdict comes from the analyzer/scanner
  (`.github/skills/bosch-embedded-std-checker`), never from model judgment
  alone. <!-- last_verified: 2026-07-14 -->

## Working rules for agents
- Work on a feature branch; never commit to `main` directly; never force-push.
- Python code under `src/`: BAPS mindset (the Bosch Automotive Python
  Standard, MISRA-style) — no mutable module-global state after init, every
  buffer slice or `struct.unpack` needs an explicit length check first.
- After edits: run the tests. Do not mark work complete with failing tests.
- Do not touch `/vendor`, `*_gen.py`, or `.github/hooks/`.
- Secrets are environment variables only (`BOSCH_MCP_TOKEN` — see
  `docs/secrets-setup.md`); never write credentials to files.

## Maintenance of this file
- Only settled decisions belong here — no in-flight proposals (they rot).
- Each fact carries a `last_verified` comment; owner reviews quarterly.
