<!--
  What: participant lab repository — assembled template combining the artifacts
        taught across Sessions 1–6, laid out the way a real Bosch repo would
        carry them.
  Used by: participants clone this in Session 1 and keep using it through
        Session 6 (the capstone has its own starter).
  How to use: SETUP.md (participant setup) · LIVE.md (admin enablement) ·
        `make verify` (headless sanity check).
-->

# labs-repo — Agent Operations course (GitHub Copilot edition)

Your working repository for the course labs. Everything taught lands here in
the place it would live in a production repo — by Session 6 this repo *is*
the deliverable pattern you take back to your team.

## Map (what lives where, and which session teaches it)

| Path | What | Session |
|---|---|---|
| `.github/copilot-instructions.md` | repo-wide standing instructions | 1 |
| `.github/instructions/` | path-scoped rules (`applyTo` frontmatter) | 1 |
| `.github/agents/` | custom agents (reviewer, test-author, doc-syncer, security-auditor) | 1 |
| `.github/chatmodes/ci-review.chatmode.md` | CI output contract | 1 |
| `.github/prompts/review-diff.prompt.md` | prompt file (`/review-diff`) | 1 |
| `.github/hooks/` | hooks: destructive blocker, SIEM logger, auto-lint (S1) · trace emitter (S2) · corporate gate set (S6) | 1·2·6 |
| `.github/workflows/review-gate.yml` | CI gate on schema-valid reviewer output | 1 |
| `.github/workflows/agent-compliance-check.yml` | MCP-backed BAPS check on PRs (incl. coding-agent PRs) | 3 |
| `.vscode/mcp.json` | wires the GitHub MCP server + `bosch-canlog` + `mock-analyzer` | 3·5 |
| `mcp/mcp-servers.json` | harness-neutral MCP wiring (master copy; both servers run from repo-relative paths) | 3 |
| `mcp/` | the `bosch-canlog` FastMCP server + client test | 3 |
| `mcp/mock-analyzer/` | mock static analyzer for the Python CAN stack (MCP + CLI, no license needed) | 5 |
| `skills/` | curated org skill library (`bosch-embedded-std-checker`) — see `skills/README.md` | 4 |
| `.github/skills/bosch-embedded-std-checker/` | discovery copy of the same skill (auto-loaded; kept byte-identical to `skills/`) | 4 |
| `ci/` | findings schema + validator | 1 |
| `src/` | lab targets: `can_parser.py` (S1 review — not shipped; YOU add it in Lab A1.3 so the review diff is the full file), `can_scheduler.py` (S5 — seeded defects), `ring_buffer.py` (S5 test-gen) | 1·5 |
| `tests/test_hooks.py` | unit tests for the hook scripts | 1 |
| `tests/` (`test_ring_buffer.py`, `coverage.sh`, `mutation_check.py`) | ring-buffer test-gen kit: partial pytest suite ~80% coverage, pytest-cov + mutation harness | 5 |
| `scripts/smoke_check.py` | stdlib-only readiness check: layout, byte-compiles, frontmatter, hook/MCP wiring, per-session table | all |
| `docs/secrets-setup.md` | where tokens come from (never from git) | 3 |
| `secrets/` · `safety/` | Lab 6.2 gate-probe fixtures: `ci-deploy.env.example` (credential gate) and `brake_monitor.py` (safety-threshold gate) | 6 |
| `.github/workflows/pr-review.yml` | reviewer-agent PR gate (must live at repo root — Actions ignores nested copies) | 5 |
| `AGENTS.md` | agent brief, read by the coding agent too | 1 |

Note: `gates.json` (S6) points at the same `block_destructive.py` as the S1
hook — one script, two wirings. The S6 session package carries its own
stricter variant; here they are deduplicated on the S1 version.

## Quick start

```bash
make verify                     # byte-compiles the Python targets, runs hook
                                # tests, validators, analyzer selftest + smoke
python scripts/smoke_check.py   # just the readiness table (part of verify)
```

Then follow `SETUP.md`. Org-side enablement (policies, budgets) is the
admin's job — `LIVE.md`.

## House rules

- `src/can_scheduler.py` is a lab target with **intentionally seeded defects**
  — never reuse it in production, never "fix" it outside Lab 5.1/5.3.
- No secrets in git, ever (`docs/secrets-setup.md`).
- The hooks stay on; `hook-trace.jsonl` is course evidence (it ships empty — every event in it is one your session produced).
