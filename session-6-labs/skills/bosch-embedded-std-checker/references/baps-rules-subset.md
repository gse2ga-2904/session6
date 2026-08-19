<!-- =========================================================================
baps-rules-subset.md — training reference for /bosch:embedded-std-checker

What:    The Bosch Automotive Python Standard (BAPS, MISRA-style) — an
         ILLUSTRATIVE 8-rule training subset, written in our own words for
         course purposes. This is NOT a certified standard and must not be
         used for certification work. At Bosch, the qualified analyzer with a
         licensed rule set is the source of truth.
Used by: Session 4 · Lab 4-A/4-C (loaded on demand by the skill — progressive
         disclosure level 3) and cited by scripts/check_standard.py findings.
Run:     Nothing to run; reference content only.
========================================================================== -->

# BAPS — the course coding standard (training subset)

> **Scope disclaimer:** illustrative training subset for automotive Python
> code (CAN stacks, node monitors, safety gates). For real compliance:
> qualified analyzer + your BU's certified rule set. Severity below is the
> *training* classification used by `check_standard.py` (mandatory findings
> fail CI; advisory findings inform).

| # | Rule (paraphrased) | Training severity | Auto-checked |
|---|---|---|---|
| BAPS-01 | Every buffer/payload access is length-checked before slicing or unpacking (`struct.unpack` on external data needs a `len()` guard) | **mandatory** | yes |
| BAPS-02 | No mutable module-global state mutated after init (thread-safety) | advisory | yes |
| BAPS-03 | Every dispatch over frame/message type handles the unknown case explicitly (no missing default/else) | **mandatory** | yes |
| BAPS-04 | All loops over external input are bounded | advisory | no — analyzer territory |
| BAPS-05 | No bare `except:`; exceptions in safety paths re-raise or fail closed | **mandatory** | yes |
| BAPS-06 | No `eval`/`exec`/dynamic imports in production paths | **mandatory** | yes |
| BAPS-07 | Shared state accessed from threads/callbacks is lock-protected (no check-then-act without a lock) | **mandatory** | no — analyzer territory |
| BAPS-08 | Public functions in safety modules have type hints and docstring contracts | advisory | no — analyzer territory |

## Remediation patterns (for the skill's suggestion diffs)

- **BAPS-01:** validate `len(payload)` against the declared size (DLC, header
  length field) *before* the slice or `struct.unpack`; reject or clamp on
  mismatch — never trust an externally supplied length.
- **BAPS-02:** move module-global mutables into a class or pass them
  explicitly; if the state is genuinely shared, add a `threading.Lock` and
  document the ownership.
- **BAPS-03:** add an `else` (or `case _:` in a `match`) that reports the
  unexpected value as a fault (`nm_report_fault(...)`) — an empty else needs
  a comment explaining why ignoring is safe.
- **BAPS-05:** catch the narrowest exception that can actually occur; in
  safety paths, fail closed (treat the sample as a fault) and re-raise or
  log — never return the permissive value from an except block.
- **BAPS-06:** replace dynamic code with a static dispatch table; if plugin
  loading is unavoidable, allowlist the module names.
- **BAPS-07:** hold one lock across the check *and* the act; never
  `if queue: queue.pop()` across threads without it.
