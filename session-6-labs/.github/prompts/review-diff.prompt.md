---
description: Run the embedded reviewer on the current branch diff and save findings.
---

<!--
review-diff.prompt.md — example Copilot prompt file (the slash-command analogue, GA).
Course: Agent Operations (Copilot edition) · Session 1 · 1.4 determinism levers.
Install: copy to <repo>/.github/prompts/review-diff.prompt.md; invoke by name from
         Copilot Chat. Pairs with the ci-review chat mode and the embedded-reviewer
         agent — prompt file supplies the task, mode supplies the contract.
-->

Review the diff between `main` and the current branch using the embedded-reviewer
agent conventions:

1. Compute the diff (`git diff main...HEAD`).
2. Review ONLY changed Python code for unvalidated input, concurrency and
   BAPS-style issues, per `.github/agents/embedded-reviewer.agent.md`.
3. Output the findings as a JSON array per `ci/findings.schema.json` — no fences,
   no prose. Empty diff → `[]`.
