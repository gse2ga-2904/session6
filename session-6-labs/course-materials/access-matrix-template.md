<!--
  access-matrix-template.md — two-axis authorization matrix (role × data classification)
  Course: Bootcamp: Agent Operations for Engineering Teams — Copilot edition
  Used by: Session 6 · Lab 6.1 (design the matrix for one business unit)
  How to use: copy the blank template, fill it for YOUR business unit, then check
  it against the filled example below. Rule: a cell with no enforcing mechanism
  is policy fiction — it becomes "deny" or a documented accepted risk.
-->

# Access matrix — template + filled example

## Legend

- **allow** — the role (and its agents) may use Copilot surfaces against this data tier.
- **gate** — allowed only through an explicit control: human approval hook, PR-only
  access, restricted model list, or a scoped MCP allowlist.
- **deny** — no Copilot surface may touch this tier for this role. Enforced, not requested.

Data tiers: **Public** · **Internal** · **Confidential** · **Restricted**
(Restricted for automotive: safety-critical calibration data, customer IP under NDA,
credentials/key material, homologation evidence.)

## Blank template

| Role ↓ / Data → | Public | Internal | Confidential | Restricted |
|---|---|---|---|---|
| Junior + agent | | | | |
| Senior engineer | | | | |
| SRE / DevOps | | | | |
| Principal / architect | | | | |

**Enforcement register** (one row per non-deny cell — mechanisms only):

| Cell | Decision | Enforced by (mechanism, not intention) | Residual risk |
|---|---|---|---|
| | | | |

Valid mechanisms: GitHub role/repo permission · Copilot policy (Feature / Privacy /
Models) · MCP allowlist · content exclusion (**see caveat below**) · PreToolUse hook ·
isolation (worktree / container / Actions sandbox / microVM) · protected branch or
environment.

> **Content-exclusion caveat (annotate every cell that relies on it):** not honored in
> Copilot CLI, the cloud coding agent, or Agent/Edit modes of Chat; up to 30-minute
> propagation; semantic information may still leak via IDE context. Best-effort — never
> the sole control on Confidential or Restricted data.

---

## Filled example — Chassis Systems Control BU (braking software group)

Assets placed: brake-controller application code (Confidential) · calibration
parameter sets (Restricted) · HIL bench credentials (Restricted) · internal tooling
(Internal) · open-source forks (Public).

| Role ↓ / Data → | Public | Internal | Confidential | Restricted |
|---|---|---|---|---|
| Junior + agent | allow | allow | **gate** | **deny** |
| Senior engineer | allow | allow | allow | **gate** |
| SRE / DevOps | allow | allow | **gate** | **gate** |
| Principal / architect | allow | allow | allow | **gate** |

**Enforcement register:**

| Cell | Decision | Enforced by | Residual risk |
|---|---|---|---|
| Junior × Confidential | gate | Repo read via team permission; agent sessions at Default Approvals (never Autopilot — org policy); PRs to `main` require senior review; cloud agent **disabled** for these repos via org Feature policy | Junior can still paste code into chat manually — covered by training + audit hooks |
| Junior × Restricted | deny | No repo permission (calibration + bench-cred repos are separate, team-gated); MCP allowlist excludes bench servers | None inside GitHub; physical bench access governed separately |
| Senior × Restricted | gate | Repo access yes, but: PreToolUse credential/calibration hooks require named approval; Models policy pins Anthropic GA (zero-data-retention); content exclusion on `calibration/**` as a completion-surface extra (caveat noted — not the control) | Semantic leakage via IDE context; accepted + reviewed quarterly |
| SRE × Confidential | gate | Deploy-scoped PAT; agent use allowed in CI only inside read-only containers; protected environments for anything touching release artifacts | CI misconfiguration; mitigated by required checks |
| SRE × Restricted | gate | Bench credentials only via environment secrets (never in repos); hook blocks `secrets/` edits; egress proxy on self-hosted runners | Secret sprawl outside GitHub — SIEM watch |
| Principal × Confidential | allow | Full repo permission; audit hooks → SIEM on all agent sessions | Standard insider risk — audit trail |
| Principal × Restricted | gate | Same hooks as senior + calibration changes require 2-person review (CODEOWNERS) | Collusion — accepted |
| All × Public/Internal | allow | Org-default Copilot policies; public-code filter **Block** org-wide (IP-indemnity posture) | Low |

**Accepted-risk note (example):** junior chat-paste of Confidential snippets cannot be
technically prevented on B/E surfaces; compensating controls = onboarding training,
prompt-audit hooks on managed machines, quarterly review of hook traces. Signed off:
BU security officer, 2026-07-01.
