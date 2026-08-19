<!--
  budget-alerts-setup.md — FinOps runbook: budgets and alerts for GitHub AI Credits
  Course: Bootcamp: Agent Operations for Engineering Teams — Copilot edition
  Used by: Session 6 · Pillar 6.6 (audit, metrics & cost) — take-home runbook
  How to use: hand to the org admin; steps are performed in GitHub billing
  settings (enterprise or organization). Facts dated July 2026 — billing UI
  labels move; verify against the live docs before publishing internally.
-->

# Budget & alert setup for Copilot AI Credits — runbook

## 1. The billing model in five lines (since 1 June 2026)

- Copilot billing is **usage-based via GitHub AI Credits**: **1 credit = $0.01**, cost = model token rates × tokens consumed.
- Each plan includes a monthly allowance — Business **$19/seat**, Enterprise **$39/seat** — **pooled across the org** (Jun–Aug 2026 promo bumps: $30/$70).
- **Code completions and Next Edit Suggestions are unlimited and not billed.** Chat, CLI, agent mode, the cloud coding agent, Spaces and code review consume credits; cloud agent and code review on private repos also consume **Actions minutes**.
- **Auto model selection** grants a **10% discount**; **data residency (GHEC-DR)** costs **+10%** credit consumption.
- Legacy "premium requests" apply only to annual subscribers who stayed on the old model — treat as legacy.

## 2. Set budgets (admin, ~15 min)

1. **Enterprise/org settings → Billing & licensing → Budgets and alerts.**
2. Create a budget per **cost center** (recommended granularity: one per BU or product line — this is what makes `dashboard.py`'s per-user attribution roll up cleanly). Per-user budgets are available for outlier control.
3. Set the monthly credit amount. Starting heuristic for an engineering BU adopting agent mode: included pooled credits × 1.5, revisited after one canary cycle with real data.
4. Decide the **hard-stop behavior**: budgets can either alert-only or stop usage at 100%. For regulated teams during rollout, alert-only at first (a hard stop mid-remediation is its own risk) — revisit after two clean months.

## 3. Alerts — 75 / 90 / 100

Budgets fire notifications at **75%, 90% and 100%** of the configured amount.

Route them deliberately:

| Threshold | Who | Expected action |
|---|---|---|
| 75% | Team lead + FinOps channel | Check `dashboard.py` attribution — is one user/workflow the driver? |
| 90% | Team lead + org admin | Throttle non-essential agent workloads; pre-approve overage or raise budget |
| 100% | Org admin + sponsor | Post-mortem entry; adjust next month's budget or usage policy |

## 4. Attribution & review cadence

- Credits are **pooled**, so attribution is your job: pull the **usage metrics API** NDJSON (1-day reports for spike hunting, 28-day for trends) and run `dashboard.py` — spend by user, by model, plus the governance signals.
- Monthly review agenda (15 min): top spenders (≈5% of users often drive most agent spend — verify, don't assume), model mix (is expensive-model usage justified?), spend per merged PR trend, and override rate from the hook traces.
- Remember the FinOps context from the deck: agentic workflows consume roughly **5–30× the tokens** of a single chat query, and multi-agent fan-out runs ~**15×** chat cost — budget alerts are how experimentation stays affordable rather than forbidden.

## 5. Checklist

- [ ] Budgets exist per cost center (not one org-wide bucket).
- [ ] 75/90/100 alerts route to named owners (not a dead mailbox).
- [ ] Usage metrics policy enabled; NDJSON pull scripted (feeds `dashboard.py`).
- [ ] Hard-stop decision documented per cost center.
- [ ] Monthly attribution review on the calendar with the team lead + FinOps.
- [ ] Legacy Metrics API consumers migrated (it **closed Apr 2026**).
