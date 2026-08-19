<!--
  skills/README.md — org skill library location for labs-repo.
  Course: Agent Operations (Copilot edition) · Session 4.
  NOTE: each skill here is BYTE-IDENTICAL to its copy under .github/skills/ —
  that is the path Copilot auto-discovers, while
  skills/ is the human-curated, review-gated library location a real org repo
  carries. scripts/smoke_check.py fails if the two copies drift.
-->

# skills/ — curated org skill library

| Skill | What | Session |
|---|---|---|
| `bosch-embedded-std-checker/` | BAPS training-subset checker — the Bosch Automotive Python Standard (SKILL.md + deterministic `scripts/check_standard.py` + `references/`) | 4 |

Two copies on purpose:

- **`skills/`** (here) — the *curation* location: this is what the verifier
  process (Session 4.4) reviews, signs off, and versions. Treat it as the
  source of truth for humans and PR review.
- **`.github/skills/`** — the *discovery* location: Copilot auto-loads skills
  from there at runtime.

When you package your own skill in Lab 4-A, land it in **both** places (copy,
not symlink — Windows checkouts and zip exports break symlinks), and keep them
identical. `python3 scripts/smoke_check.py` enforces the parity.
