<!--
copilot-instructions.md — example repo-wide Copilot custom instructions.
Course: Agent Operations (Copilot edition) · Session 1 · 1.4 instructions stack / Lab L1.5.
Install: copy to <repo>/.github/copilot-instructions.md — Copilot auto-applies it to
         every chat request in the repo (GA). Keep it short: this file is context on
         every request; a bloated instructions file is a caching and attention tax
         (Session 2.1/2.2).
-->

# Project instructions — powertrain-sandbox

## What this repo is
Sandbox for the Agent Operations course: a small automotive embedded codebase
(CAN frame handling, diagnostics) written in Python, used as the target for
review and test agents.

## Conventions
- Language: Python 3.10+ everywhere — the CAN stack under `src/`, tooling under `tools/`.
- Tests live in `/tests`; run with `python -m pytest tests/ -q`.
- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`). Never force-push.
- BAPS mindset (the Bosch Automotive Python Standard, MISRA-style) in
  `src/can/` — the path-scoped rules in
  `.github/instructions/firmware.instructions.md` apply there.

## Boundaries
- Never modify `/vendor`, generated files (`*_gen.py`), or `.github/hooks/`.
- No mutable module-global state mutated after initialization in CAN-stack code.
- Secrets come from environment variables only; never write credentials to files.

## Review expectations
- Review output must be machine-readable JSON when running in the `ci-review`
  chat mode (schema: `ci/findings.schema.json`).
- Prefer small, verifiable steps; run the tests after any code change.
