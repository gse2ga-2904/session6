# Session 6 — START HERE

Agent Operations for Engineering Teams · Tec de Monterrey × Bosch GDL

**This folder is self-contained.** It is a clean, known-good working repo with
everything Session 6 needs. It does not depend on any earlier session's folder,
and nothing you do here can break a later one — each session ships its own kit.

## What's inside

| Path | What it is |
|---|---|
| `activities.md` | The **self-paced guide** for this session. Work through it alongside the slides. |
| `slides/session-6.html` | The session slides — open in any browser, arrow keys, works offline. |
| `course-materials/` | The instructor's samples you **copy from**. Never edit these. |
| everything else | **Yours to edit and commit** — hooks, agents, tests, src. |

## Setup (in this order — each step unblocks the next)

All commands run in **bash** (Git Bash on Windows — not PowerShell/cmd).
Python 3.10+; no `make`, no compiler.

```bash
# 1 · Python check + test runner (once)
python3 -m pip install pytest
python3 verify.py                    # must pass before you start

# 2 · make this folder a git repo (the zip ships without .git — needed
#     for branch/diff steps AND for Copilot to treat it as a repository)
git init -b main && git add -A && git commit -m "session 6 starting point"

# 3 · Copilot CLI — REQUIRED for the agent hooks (no CLI = no hooks)
npm install -g @github/copilot      # needs Node.js ≥ 20
copilot --version                    # confirm, then log in on first run

# 4 · start Copilot FROM THIS FOLDER — hook configs load at CLI start
copilot
```

**Using VS Code instead of the CLI (most people's daily surface):** the SAME
`.github/hooks/*.json` configs work in the VS Code Copilot extension (agent
hooks are **Preview** there). Differences that matter: VS Code loads hook
files automatically **when you save them** (no restart needed); manage them
with `/hooks` in chat or Command Palette → "Chat: Configure Hooks"; see
execution logs in Output panel → "GitHub Copilot Chat Hooks"; your org's
enterprise policy can disable hooks entirely. **Visual Studio (the Windows
IDE) does NOT support agent hooks** — use VS Code or the CLI there.

**About the hooks (read this before debugging):** the files in
`.github/hooks/*.json` are **Copilot agent hooks** — they fire on the
agent's tool calls during a Copilot session. They are NOT git commit hooks;
`.git/hooks/` is a different, unrelated mechanism and will stay empty.
If agent hooks don't fire: (1) restart `copilot` from this folder (configs
load at start), (2) `python3 -m json.tool .github/hooks/*.json` must pass,
(3) every config needs top-level `"version": 1` (this kit ships it),
(4) update the CLI: `npm update -g @github/copilot`. Quick proof without
any agent: `echo '{"tool_name":"bash","tool_input":{"command":"rm -rf x"}}' |
python3 .github/hooks/scripts/block_destructive.py` → a JSON deny + BLOCKED line.

## Carrying your own work forward

Because each session is its own folder, your files from earlier sessions do
**not** appear here automatically — that is deliberate (a broken folder can't
cascade). If you want to continue with your own work, copy it across, e.g.:

```bash
cp ../session-5-labs/docs/adoption-plan.md docs/   # the course-long deliverable
```

Anything the session genuinely needs is already in this kit.
