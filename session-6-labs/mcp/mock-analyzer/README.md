<!--
  What: mock static analyzer for embedded Python — FastMCP server + offline CLI.
  Used by: Session 5 · Labs 5.1/5.3, and copied into the Session 7 capstone
        starter as mcp/mock-analyzer (project F needs no analyzer license).
  How to use: see "Run" below; findings schema mirrors what a qualified
        analyzer's MCP server would emit.
-->

# mock-analyzer — BAPS/CWE findings without an analyzer license

A training-grade static analyzer for the course's CAN-stack Python code. It
emits findings in the **same JSON shape** a qualified analyzer's MCP server
would feed Copilot Chat, so everything downstream — the remediation loop, the
capstone's compliance pipeline, PR comments — works identically whether the
source of truth is this mock or a real qualified analyzer behind MCP.

**Posture (repeat it in class):** this is an ast/heuristic engine, *not* a
qualified tool. In production — at Bosch you'd wire this to the qualified
analyzer (Klocwork/Coverity class) — that tool is the source of truth, per
ISO 26262-8 Cl. 11. Copilot has no native coding-standard awareness and no
tool qualification; it is remediation labor, never the verdict.

## Run

```bash
python3 server.py --selftest          # no dependencies, no network
python3 server.py path/to/file.py    # direct analysis, JSON to stdout

# As an MCP server (requires fastmcp + token):
pip install fastmcp
export ANALYZER_TOKEN=dev-placeholder-token    # never a literal in git
python3 server.py                     # stdio transport
python3 server.py --http              # Streamable HTTP on 127.0.0.1:8391
```

MCP tools exposed: `analyze_file(path)`, `analyze_source(code, filename)`
(inline snippets/patches), and `list_checkers()`. MCP resource:
`analyzer://ruleset` (checker catalog + mandatory severities).

`--selftest` additionally analyzes the repo's seeded target when present
(`src/can_scheduler.py` here; `src/can_gateway/can_gateway.py` in the
capstone copy) and asserts ≥4 findings with ≥2 mandatory.

## Checkers

| Checker | Detects | Severity |
|---|---|---|
| `CONC.SHARED_UNPROTECTED` | callback/task shared module state: unprotected RMW (critical) or lock-less mutation (warning) — BAPS-02/07 | critical/warning |
| `ABV.TAINTED` | `struct.unpack` buffer/length from unvalidated input — BAPS-01 | critical |
| `DISPATCH.NO_DEFAULT` | frame-type `if/elif` chain without an `else` — BAPS-03 | error |
| `EXC.SWALLOWED` | bare `except:` (error) / broad except that passes (warning) — BAPS-05 | error/warning |
| `DYN.CODE` | `eval`/`exec`/dynamic import in production paths — BAPS-06 | critical |
| `LOOP.UNBOUNDED` | `while True` over external input without a break — BAPS-04 | warning |
| `LV.UNUSED_RESULT.SUSPICIOUS` | `(?)`-marked residue operations | review |

"Mandatory" findings = severity `critical` or `error`; the remediation loop and
CI gates fail on those. Mutations are considered protected when they sit inside
a `with <lock>:` block.

`findings.json` is a cached run against `../../src/can_scheduler.py` so
material stays diffable without executing anything.
