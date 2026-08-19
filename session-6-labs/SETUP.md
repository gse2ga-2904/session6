<!--
  SETUP.md — participant setup for labs-repo (15 minutes, Session 1 opening).
  Admin-side enablement lives in LIVE.md — if a step here fails with a policy
  error, flag the instructor; do not debug org policy from your seat.
-->

# Participant setup

> **All commands in this course run in a bash shell.** On Linux/macOS that is
> your normal terminal; on Windows it is **Git Bash** (installed with Git for
> Windows). Do not use PowerShell or cmd.exe for the labs.

## 0. Prerequisites

Everyone needs:

- GitHub account in the class org with a **Copilot Business/Enterprise seat**
- **VS Code** with the Copilot extension, signed in to that account
- **Copilot CLI** installed and authenticated (hooks are GA there). Needs Node.js ≥ 20 —
  on Windows: `winget install -e --id OpenJS.NodeJS.LTS`, then in a **new** Git Bash window
  `npm install -g @github/copilot` (verify the package name against current GitHub docs) and log in
- Python 3.10+ (3.11 recommended), `make`, git — **no compiler needed**
- The Python test toolchain: `python3 -m pip install pytest pytest-cov fastmcp` (Windows/Git Bash: `python -m pip …`; always module form — bare `pip`/`pytest` may not be on PATH)

### Windows (managed Bosch laptop) — Git Bash required

Stock Windows has neither `python3` nor bash, so the course standardizes on
**Git for Windows (Git Bash)** as the shell and plain `python` as the
interpreter. Install, in this order (use the company portal versions where
IT provides them):

1. **Git for Windows** (includes Git Bash):
   ```
   winget install --id Git.Git -e
   ```
2. **Python 3.11** — from the company software portal if listed, otherwise:
   ```
   winget install --id Python.Python.3.11 -e
   ```
   During/after install make sure `python --version` prints 3.11.x **inside a
   new Git Bash window** (the installer's "Add to PATH" option must be on).
3. **make**:
   ```
   winget install --id ezwinports.make -e
   ```
   Then confirm in a *new* Git Bash window: `make --version`.

After installing, run `python scripts/smoke_check.py` (step 2 below) — it
verifies the Git Bash + python/git/make baseline and tells you exactly what
is still missing. If winget installs are blocked by IT policy, use the
**GitHub Codespaces fallback** (below) for the affected labs — see the
support matrix.

Makefiles default to `python3` internally (for Linux); on Windows run them as
`make PY=python <target>` — or just `make PY=python verify`.

### Linux / macOS

One extra requirement: **`python` (not just `python3`) must resolve to
Python 3**, because the hook configs and MCP configs launch `python` so they
also work on Windows. On Ubuntu/Debian:

```bash
sudo apt install python-is-python3
```

On macOS or with pyenv/asdf, any mechanism that puts a Python 3 `python` on
PATH is fine. `smoke_check.py` verifies this.

### pip through the corporate proxy

The Python extras (`python3 -m pip install pytest pytest-cov fastmcp` (Windows/Git Bash: `python -m pip …`; always module form — bare `pip`/`pytest` may not be on PATH)) must traverse the
Bosch proxy: set `HTTPS_PROXY`/`HTTP_PROXY` per your IT instructions (or use
`pip install --proxy http://<proxy>:<port> ...`). If pip is fully blocked,
the core labs still work: `make verify` skips the pytest/fastmcp checks with
a note instead of failing, and Codespaces has no proxy.

### GitHub Codespaces fallback

Anything your local machine can't do — blocked installs, blocked pip — runs
in **GitHub Codespaces**: open your labs repo on github.com → `Code` →
`Codespaces` → `Create codespace`. It is a full Linux box with python/make
preinstalled and unrestricted `apt-get`/`pip`.

### Per-lab support matrix

| Lab / session                                   | Windows + Git Bash (local) | Codespaces | Room image |
|-------------------------------------------------|----------------------------|------------|------------|
| S1 hooks + custom agents (A1.2, L1.5)            | yes                        | yes        | yes        |
| S1 CI review gate (Actions)                      | yes (runs on GitHub)       | yes        | yes        |
| S2 trace emitter / metrics / credits             | yes                        | yes        | yes        |
| S3 MCP server labs (3-A, 3-B) — needs `pip install fastmcp` | yes (pip via proxy)  | yes        | yes        |
| S3 coding-agent workflow (3-C)                   | yes (runs on GitHub)       | yes        | yes        |
| S4 skill build + suite install (4-A, 4-B, 4-C)   | yes                        | yes        | yes        |
| S5 test-gen: coverage lab (`coverage.sh`) — needs `pip install pytest pytest-cov` | yes (pip via proxy) | yes | yes |
| S5 mutation lab (`mutation_check.py`) — needs `pip install pytest` | yes (pip via proxy) | yes | yes |
| S5 remediation loop / mock analyzer              | yes                        | yes        | yes        |
| S6 gate set + governance dashboard               | yes                        | yes        | yes        |
| S7 capstone (Python targets + analyzer)          | yes                        | yes        | yes        |

"Room image" = the pre-imaged classroom machines, which carry the full
toolchain. When a row says Codespaces, that is the supported path — don't
burn lab time fighting a blocked installer.

## 1. Get your repo

Create your personal repo from this template (`Use this template` → name it
`labs-<your-handle>`), then clone it. Don't fork — you want your own Actions.

**The `<course>` placeholder.** Activity sheets copy files from
`<course>/session-N/code/...`. That refers to the **course materials repo**
(slides, per-session code kits, activities), which is separate from this labs
repo: clone it once, next to your labs clone (e.g. `~/work/copilot-course`
beside `~/work/labs-<your-handle>`). Wherever an activity says `<course>`,
substitute the root of that clone. Your instructor gives you its URL in
Session 1.

## 2. Sanity check (offline — no Copilot needed)

```bash
make verify                     # full check: byte-compiles, hook tests,
                                # validators, analyzer selftest, smoke check
                                # (Windows/Git Bash: make PY=python verify)
python scripts/smoke_check.py   # or just the readiness table + env probes
```

`smoke_check.py` (stdlib-only) verifies the repo layout, byte-compiles the
Python lab targets, validates the hook/agent/skill wiring, and prints a
per-session readiness table (S1–S6). If anything is NOT READY, fix your local
toolchain now, before the labs need it — and tell the instructor if a *file*
is missing (that's a template problem, not yours).

Which folder matters for which session: see the map table in `README.md` —
every artifact lives where a production repo would carry it, and the table
says which session teaches it.

## 3. Token for the MCP labs (Session 3)

```bash
export BOSCH_MCP_TOKEN=dev-placeholder-token
```

Any placeholder value works in training — the server only checks presence.
Read `docs/secrets-setup.md` for the *why* (it is the point of the lab).
For MCP over VS Code, `.vscode/mcp.json` prompts for the token and stores it
in secret storage — never commit a token.

## 4. Confirm the Copilot surfaces (in-class, Session 1)

1. **Chat + agent mode** work on this repo in VS Code; the model picker shows
   the Claude models.
2. **Custom agents** appear (agents dropdown → `embedded-reviewer` etc.).
3. **Hooks**: from a Copilot CLI session in the repo, ask for something that
   leads to `rm -rf` — expect a block and a new line in `hook-trace.jsonl`.
   (VS Code hooks are Preview; the CLI is the GA surface for this demo.)
4. **MCP** (Session 3 onward): the `bosch-canlog` server shows up in the MCP
   list; if it doesn't, the org policy is likely disabled — that's LIVE.md
   territory, tell the instructor.

## 5. What you'll add during the course

Each session's lab commits more of the pattern into *your* copy: refined
agents and instructions (S1), trace hooks + eval set (S2), your own MCP
resource (S3), a packaged skill (S4), remediation evidence (S5), and the
governance gate set + dashboard inputs (S6). By the end, this repo is your
take-home reference implementation.
