<!--
  traceability-log-schema.md — agent-vs-human provenance schema for ISO 26262 evidence
  Course: Bootcamp: Agent Operations for Engineering Teams — Copilot edition
  Used by: Session 6 · Pillar 6.6 and Lab 6.6 (validate your hook trace against it);
  also referenced by Session 5 · Lab 5.3 (the violation report's machine-readable twin).
  How to use: adopt as the JSONL record shape for every change that lands in a
  safety-relevant repo. The Lab 6.2 audit hook populates a subset; the rest is
  added at PR merge time by CI.
-->

# Traceability log schema — who wrote this code, and how was it verified?

## Why

AI-suggested code has **no inherent requirement trace or provenance** — ISO 26262
traceability must be imposed externally. When an assessor asks *"who authored this
change and how was it verified?"*, this log is the answer. It is also the honest
basis for the Cl. 11 argument from Session 5: the claim that Copilot's output is
*"fully examined or verified"* is only as strong as the verification evidence you
can produce per change. GitHub's audit log won't produce it for you (client-side
prompts and tool calls are not captured) — this schema is the compensating record.

## Record shape (JSONL — one record per merged change)

```json
{
  "change_id": "gw-2026-0713-004",
  "repo": "bosch-gdl/brake-controller",
  "pr_number": 106,
  "merged_at": "2026-06-30T16:41:00Z",
  "files": ["safety/brake_monitor.c"],

  "provenance": {
    "author_type": "human",
    "agent_name": null,
    "model": null,
    "session_id": null,
    "prompt_ref": null,
    "spec_ref": null
  },

  "requirement_trace": {
    "requirement_ids": ["SYS-REQ-BRK-0142"],
    "asil": "D"
  },

  "verification": {
    "static_analysis": {"tool": "Klocwork", "tool_version": "2026.1",
                        "build_id": "kw-build-4718", "result": "clean"},
    "tests": {"suite": "brake_monitor_unit", "run_id": "ci-88123", "result": "pass",
              "coverage_line_pct": 96.4},
    "review": {"reviewers": ["m.torres", "k.schmidt"], "verdict": "approved",
               "review_ref": "PR #106 review thread"}
  },

  "gates": [
    {"gate": "G4-safety-threshold", "verdict": "block",
     "ts": "2026-06-30T08:52:19Z", "resolution": "re-authored by human"}
  ]
}
```

## Field reference

| Field | Required | Notes |
|---|---|---|
| `change_id`, `repo`, `pr_number`, `merged_at`, `files` | yes | Identity of the change; `files` limited to safety-relevant paths if the PR is mixed |
| `provenance.author_type` | yes | `human` · `agent` · `human_with_agent` (pairing/completions). Be honest — `human_with_agent` is the common case and auditors respect precision |
| `provenance.agent_name` / `model` | when agent involved | The `.github/agents/*.md` name and the pinned model (from the agent register — Pillar 6.5) |
| `provenance.session_id` / `prompt_ref` | when agent involved | Links to the hook-trace JSONL (Lab 6.2). Metadata reference, not prompt content — decide prompt storage policy deliberately |
| `provenance.spec_ref` | for delegated work | The SDD spec the agent implemented (Session 5.4) |
| `requirement_trace.*` | yes for ASIL-rated files | The externally-imposed trace AI output lacks |
| `verification.static_analysis` | yes for safety-path modules | The **qualified analyzer** run — this row carries the Cl. 11 argument |
| `verification.tests` / `review` | yes | Independent signals; named human reviewers, always |
| `gates[]` | when any gate fired | Blocked/gated attempts are evidence the control system works — include them |

## Population pipeline (minimal viable)

1. **During the session:** `audit_log.py` (Lab 6.2) writes `session_id`, `tool`, `target`, `verdict` per tool call → hook-trace JSONL → SIEM.
2. **At PR merge:** a CI job assembles the record — provenance from commit trailers (e.g. `Co-authored-by:` agent trailer or the coding agent's PR metadata), analyzer/test run IDs from the pipeline, reviewers from the PR API — and appends to the repo's `traceability/` log (append-only storage).
3. **At audit time:** filter by file/requirement; every safety-relevant change answers *who / what model / which spec / which analyzer run / which humans*.

## Consistency rules

- `author_type: "agent"` **requires** `agent_name`, `model`, `session_id`, and a `verification` block with all three sub-sections — an agent change without full verification evidence should fail the CI assembly step.
- `author_type: "human_with_agent"` (the common case) **also requires** all three `verification` sub-sections present — agent-assisted code still needs recorded analysis, tests, and a named reviewer. (`validate_traceability.py` enforces this; the provenance ID fields stay mandatory only for fully autonomous `agent` changes, since completions may not name an agent.)
- Any **ASIL-rated** file (`asil` not `QM`/null) requires `verification.tests` and `verification.review` regardless of who authored it — independent evidence is the point of the trace.
- A `gates[]` block with `verdict: "block"` and no follow-up record is an open incident, not history.
- Retention: align with your safety-case retention (typically the product lifecycle — far beyond GitHub's ~180-day audit-log window; that mismatch is exactly why this log exists).
