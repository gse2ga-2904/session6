---
applyTo: "src/can/**/*.py"
---

<!--
firmware.instructions.md — example path-scoped Copilot instructions (applyTo).
Course: Agent Operations (Copilot edition) · Session 1 · 1.4 instructions stack.
Install: copy to <repo>/.github/instructions/firmware.instructions.md (GA).
The applyTo frontmatter scopes these rules to the CAN-stack sources only — the
rest of the repo does not pay the context cost.
-->

# Safety-critical Python rules (CAN-stack scope)

- BAPS mindset — the Bosch Automotive Python Standard (MISRA-style). Every
  deviation needs a justifying comment.
- No mutable module-global state mutated after initialization (module-level
  lists/dicts are frozen after `*_init` functions).
- Every buffer slice or `struct.unpack` requires an explicit length check
  against the declared size on the line(s) immediately above.
- External input (CAN DLC, UDS lengths) is untrusted: validate range before use.
- Every dispatch over frame/message type handles the unknown case explicitly
  (BAPS-03) — no `if/elif` chain without an `else`.
- No magic numbers: use named constants from `src/can/constants.py`.
- State shared with driver callbacks is lock-protected — no check-then-act
  without holding the lock (BAPS-07).
- Reminder: these instructions guide the assistant; the qualified static analyzer
  remains the source of truth for compliance evidence (ISO 26262-8 Cl. 11).
