# Session 6 — Governance, Compliance & Measurement · Activities

> **Which repo am I in?** Your **`labs-repo`** clone — the same one from Sessions 1–5.
> Gates install into its `.github/hooks/`; the trace they produce is your dashboard
> input. Paths shown as `code/…` are the instructor's Session 6 kit.

The 6.2 lab's trace file is intentionally the input
to the 6.6 lab — morning evidence becomes afternoon metrics.

---

## Lab 6.1 — Design the access matrix for one business unit

- **Objective:** produce an enforceable role × data-classification matrix for one Bosch BU, where every cell names its enforcing control.
- **Duration:** 25 min + 5 min sponsor round (one pair presents to the room; the full pair-swap defense below is the async option if time is tight)
- **Group size:** pairs; pairs then swap to play "sponsor" for each other.
- **Setup:** `code/access-matrix-template.md` (template + filled example for a Chassis Systems BU).

**Steps**

1. Pick a BU one of you actually knows. List its 3–5 most sensitive data assets and place each in a tier: Public / Internal / Confidential / Restricted.
2. Fill the matrix: rows = role tiers (junior + agent · senior · SRE/DevOps · principal/architect), columns = data tiers. Each cell: **allow / gate / deny**.
3. For every non-deny cell, fill the **"enforced by"** column: GitHub role/repo permission, Copilot policy, MCP allowlist, content exclusion, hook, or isolation. A cell with no enforcing control must become deny — or be flagged as accepted risk.
4. Content-exclusion reality check: anywhere you relied on exclusion, annotate its limitations (not honored in CLI / cloud agent / Agent-Edit modes; 30-min propagation; semantic leakage). If the cell protects Restricted data, exclusion alone is insufficient — add a stronger layer.
5. Sponsor defense: swap with another pair. Sponsors probe two cells: "why gate and not deny?" and "what enforces this?"

- **Deliverable:** the filled matrix with enforcement column + one accepted-risk note.
- **Success criteria:** no unenforced allow/gate cells · content exclusion never the sole control on Restricted data · both sponsor challenges answered with mechanism, not intention.

**Troubleshooting**

| Symptom | Likely cause | Fix |
|---|---|---|
| Everything ends up "deny" | Over-caution kills adoption | Deny is for Restricted; use gate (approval) for Confidential and revisit after canary data |
| Cell enforced by "policy document" | Fiction | Only mechanisms count: platform permission, Copilot policy, allowlist, hook, isolation |
| Pair can't decide where the cloud agent sits for Confidential | Genuine judgment call | Either gate or deny is defensible — require the answer to name enforcement + residual risk |
| "Our BU has 9 data categories" | Over-modeling | Map them onto the 4 tiers; the matrix is a decision tool, not a data catalog |

- **Stretch goals:** add a fifth row for *service/agent identities* (MCP servers, CI bots); map each enforcement entry to the specific Copilot policy name; propose the review cadence per tier.

---

## Lab 6.2 — Implement the corporate gate set

- **Objective:** wire the mandatory-human-gate set as PreToolUse hooks and prove each gate with a live probe, producing an audit trace.
- **Duration:** 35 min + 5 min debrief
- **Group size:** solo
- **Setup:** Copilot CLI (hooks **GA** there — reference surface; VS Code hooks are Preview); your labs-repo clone — it ships everything this lab probes: the gate set in `.github/hooks/`, plus the `secrets/` (with `ci-deploy.env.example`) and `safety/` (with `brake_monitor.c`) probe targets. No directories to create.

**Steps**

1. Verify `.github/hooks/gates.json` is present in your labs-repo (labs-repo ships it — nothing to copy, and the hooks run via `python`, so no `chmod` needed). Note the variant difference: labs-repo's `gates.json` points at the same `block_destructive.py` as the S1 hook — one script, two wirings — while the instructor's S6 kit (`code/hooks/`) carries its own stricter variant of that script. Compare them; don't overwrite your labs-repo copy.
2. Read `gates.json`: three PreToolUse entries — destructive-op blocker, credential-file approval, safety-critical threshold gate — plus a PostToolUse audit logger. Note the header comment: **matchers are parsed but NOT applied** — each script does its own matching; field naming is snake_case vs camelCase across harnesses.
3. Probe 1 (block): in an agent session, request a task that leads to `rm -rf` / `git push --force`. Expect a hard block (exit code 2 semantics) and a `hook-trace.jsonl` line with `verdict:"block"`.
4. Probe 2 (gate): request an edit to `secrets/ci-deploy.env.example`. Expect an approval prompt; approve once, deny once — both must appear in the trace.
5. Probe 3 (threshold): request a change touching >20 lines under `safety/`. Expect a block with the "requires named human reviewer" message.
6. Check the permission posture: confirm the session runs at **Default Approvals** — and note why Autopilot (Preview) is banned in regulated repos.
7. Keep `hook-trace.jsonl` — it is your input for Lab 6.6. It ships **empty**, so every event in it is one your probes produced — the ≥4-event bar below measures *your* session, not shipped data.

- **Deliverable:** working gate set + `hook-trace.jsonl` containing ≥4 events (block, approve, deny, block) — all produced by your own probes.
- **Success criteria:** two demonstrated blocks + one demonstrated approval prompt · every probe logged · you can explain what bounds the *cloud* agent instead (protected branches/environments — client hooks don't run there).

**Troubleshooting**

| Symptom | Likely cause | Fix |
|---|---|---|
| Hook never fires | Wrong location or JSON invalid | `.github/hooks/*.json` in repo root (or `~/.copilot/hooks`); validate JSON; restart the session |
| Gate blocks everything including reads | Script matches too broadly | Remember matchers aren't applied — tighten the *script's* own command/path matching |
| Script gets empty tool input | Field-name mismatch | Check snake_case vs camelCase (`tool_input.file_path` vs `filePath`); the kit scripts try both |
| Works in CLI, not in VS Code | VS Code hooks are Preview | Expected; note it as a status finding. CLI is the reference surface for this lab |
| Approval prompt not shown, action just runs | Session in Bypass Approvals / Autopilot | Switch to Default Approvals; re-run the probe |
| No Copilot? | Seat/policy blocked | `make verify` in `course-materials` proves the gate verdicts offline (`run_gates_demo.py` pipes the same probe events through the scripts) |

- **Stretch goals:** add a fifth gate for hardware/bench access paths; make the audit logger ship lines to a mock SIEM endpoint (local HTTP listener); replicate one gate server-side as a required CI check so a client bypass still can't merge.

---

## Lab 6.3 — Worktree-based parallel agent setup

- **Objective:** run two custom agents in parallel, one git worktree each, and demonstrate that the worktree is the collision boundary.
- **Duration:** 20 min (flex block — may compress to a shared demo)
- **Group size:** pairs
- **Setup:** lab repo; two defined custom agents (reuse `embedded-reviewer` plus any W3/W4 agent).
- **Prerequisite:** git ≥ 2.40 is required for this worktree lab — check with `git --version` yourself (the labs-repo smoke check does *not* probe the git version).

**Steps**

1. Create two worktrees: `git worktree add ../wt-review feature/review-pass` and `git worktree add ../wt-tests feature/test-pass`.
2. Start agent A in `wt-review` (review/annotation task) and agent B in `wt-tests` (test-writing task on the same module) — separate sessions, separate context windows, running concurrently.
3. Proof of isolation: have both agents touch the same file in their own worktree; show the working copies diverge with zero collision, and each branch holds only its own changes.
4. Merge like humans: open a PR from each branch; resolve the (intentional) overlap in review, not on disk.
5. Classify the boundary: write one sentence on what worktrees do isolate (working-copy collisions) and what they do not (privileges, filesystem outside the tree, network) — and which isolation level from the decision tree each of your two agents actually needed.

- **Deliverable:** two branches + two PRs + the one-sentence boundary classification.
- **Success criteria:** both agents ran concurrently without touching each other's tree · overlap resolved in PR review · boundary sentence names worktrees as collision isolation, not a security sandbox.

**Troubleshooting**

| Symptom | Likely cause | Fix |
|---|---|---|
| `worktree add` refuses: branch checked out | Same branch in two trees | One branch per worktree — create a fresh branch per agent |
| Agents "see" each other's changes | Both launched in the main checkout | Verify each session's cwd is inside its own worktree before starting |
| Merge conflict panic | The overlap is intentional | That's step 4 — resolve in the PR; single-threaded writes at merge time is the lesson |
| Disk clutter after the lab | Worktrees left behind | `git worktree remove ../wt-review` (and `prune`) |
| No Copilot? | Seat/policy blocked | Do the worktree mechanics (steps 1, 3–5) by hand — the isolation boundary is the lesson; `make verify` in `course-materials` proves the S6 machinery offline |

- **Stretch goals:** add a third parallel *read-only* research agent and note it needs no worktree at all (parallel reads are safe); script worktree create/cleanup as SessionStart/Stop hooks; try the same task via cloud delegation and compare isolation properties (ephemeral Actions sandbox vs local worktree).

---

## Activity 6.4 — Map your artifact to the frameworks (paper, 10 min)

- **Objective:** express one Session 5 artifact in auditor language: one control each from NIST AI RMF, ISO/IEC 42001, OWASP (LLM or Agentic), and ISO 26262/ASPICE.
- **Duration:** 10 min + 1 readout
- **Group size:** solo or pairs
- **Steps:** pick an artifact (the 5.3 remediation loop maps richest) → one line per framework: *artifact → control → evidence you could show*. EU AI Act: note whether Article 50 transparency (binding Aug 2 2026) touches it; recall the high-risk deferral is proposed, not law.
- **Deliverable:** four mapping lines.
- **Success criteria:** each line names a real control and a producible piece of evidence — not "we comply".
- **Stretch goal:** identify the ONE framework question your team could not answer today; park it as a capstone item.

---

## Activity 6.5 — Sketch the 8-week rollout (async capstone homework)

- **Objective:** an 8-week canary → rolling → blue/green plan for one BU with rollback and champion structure.
- **Duration:** async — kicked off in ~2 min in-room; completed as capstone homework before Session 7
- **Group size:** pairs (same BU as Lab 6.1 for continuity)
- **Steps:** weeks 1–2 canary (name the non-critical repo, the volunteers, the weekly post-mortem owner) → weeks 3–6 rolling (the BU, monthly review, which anomaly alerts) → weeks 7–8 blue/green prep (which org policy is your "flag"; who may flip it) → add the agent-register column: every agent shipped, owner, permissions, review date.
- **Deliverable:** one-page plan skeleton.
- **Success criteria:** rollback is a named policy flip, not "we'll figure it out" · champions named by role · anti-patterns (all-hands launch, mandate without ground support) demonstrably avoided.
- **Stretch goal:** add the two metrics from 6.6 you'd watch weekly during canary and the thresholds that trigger rollback.

---

## Lab 6.6 — Live dashboard from usage metrics + hook traces

- **Objective:** produce a governance report combining GitHub's usage-metrics NDJSON with your own morning hook trace — spend vs budget, gate activity, override rate, agent-vs-human provenance.
- **Duration:** ~25 min
- **Group size:** solo
- **Setup:** `code/dashboard.py` + fixtures `code/fixtures/sample-usage-metrics.ndjson` and `code/fixtures/sample-hook-trace.jsonl`; your own `hook-trace.jsonl` from Lab 6.2 (it shipped empty — your probes filled it); `code/fixtures/hook-trace-sample.jsonl` is a realistic demo trace if yours is thin; Python 3.10+ (stdlib only).

**Steps**

1. Run on fixtures: `python3 dashboard.py` — read the console report: credits by user/model, % PRs with AI review, gate blocks, override rate, budget bar with 75/90/100 thresholds.
2. Swap in your own trace: `python3 dashboard.py --hook-trace session-6-labs/hook-trace.jsonl` — your morning probes now appear as gate/override events. Every event you see is one you produced (the file ships empty). If your 6.2 run was cut short, demo with `--hook-trace fixtures/hook-trace-sample.jsonl` and say so in your observations.
3. Generate the HTML report: `python3 dashboard.py --html report.html` and open it.
4. Interpret: which user/model drives spend? Is the override rate a trust signal or a mis-scoped gate? Which events would you ship to the SIEM verbatim, and which only as metadata?
5. Note the source-of-truth facts in the header comment: usage metrics API is GA (NDJSON, 1-day/28-day, ~1-year retention, metrics policy required); the **legacy Metrics API closed Apr 2026**; the audit log does **not** capture client-side prompts — your JSONL is the compensating evidence.
6. Connect to ISO 26262: open `code/traceability-log-schema.md` and check which schema fields your trace already populates and which are missing.

- **Deliverable:** `report.html` + three written observations (spend driver, override interpretation, SIEM decision).
- **Success criteria:** dashboard runs on fixtures AND on your own trace · budget alert logic explained · at least one missing traceability field identified.

**Troubleshooting**

| Symptom | Likely cause | Fix |
|---|---|---|
| `JSONDecodeError` on the NDJSON | File treated as one JSON doc | NDJSON = one JSON object per line; don't pretty-print the fixture |
| Own trace shows zero events | Wrong path or empty 6.2 run | Point `--hook-trace` at the file the 6.2 audit logger wrote (it ships empty on purpose); re-run one probe if empty, or fall back to `fixtures/hook-trace-sample.jsonl` for the mechanics |
| Numbers look implausibly large | Fixture is synthetic | Correct — fixtures are labeled synthetic; the shapes, not the magnitudes, are the lesson |
| Want live org data | Metrics policy / permissions | Requires the metrics policy enabled + appropriate token scopes; out of scope in-room — the runbook is `budget-alerts-setup.md` |

- **Stretch goals:** add a per-cost-center rollup (the credits are pooled — attribute them); add a trend line for override rate across days; extend `dashboard.py` to validate every trace line against `traceability-log-schema.md` and report schema coverage.
