<!-- =========================================================================
secrets-setup.md — secrets handling for the Session 3 labs

What:    How to provide the tokens the bosch-canlog MCP server and the CI
         workflow expect — in training (env vars) and in production
         (HashiCorp Vault / AWS Secrets Manager).
Used by: Session 3 · Lab 3-B and Lab 3-C. Read before running mcp_server.py.
Run:     Follow the "Training setup" section; the rest is reference.
========================================================================== -->

# Secrets setup — Session 3

**Prime directive:** no secret ever appears in code, prompts, committed JSON,
or slides. The server *fails fast at startup* if a required secret is missing —
that is deliberate.

## Secrets used in this session

| Name | Consumed by | Purpose | Training value |
|---|---|---|---|
| `BOSCH_MCP_TOKEN` | `mcp_server.py`, CI workflow | Service token for the MCP server | any placeholder, e.g. `dev-placeholder-token` |
| `TRACKER_TOKEN` | `mcp_server.py` (confirmed writes) | Downstream ticket-tracker credential | optional; falls back to `BOSCH_MCP_TOKEN` in training |
| `AUDIT_LOG_PATH` | `mcp_server.py` (not a secret) | Where the JSONL audit log is written | defaults to `./audit.log.jsonl` |

## Training setup (env vars — dev fallback only)

```bash
# macOS/Linux — run in the SAME terminal that launches VS Code or the tests
export BOSCH_MCP_TOKEN="dev-placeholder-token"
python session-3/code/mcp_server.py --selftest
python session-3/code/mcp_client_test.py
```

```powershell
# Windows PowerShell
$env:BOSCH_MCP_TOKEN = "dev-placeholder-token"
```

In VS Code, prefer the `inputs` prompt in `.vscode/mcp.json`
(see `mcp-config-vscode.json`): VS Code asks once and stores the value in its
secret storage — it never lands in the repo.

For CI (Lab 3-C): repository → Settings → Secrets and variables → Actions →
new repository secret `BOSCH_MCP_TOKEN`. The workflow reads it as
`${{ secrets.BOSCH_MCP_TOKEN }}`.

## Production pattern 1 — HashiCorp Vault

```bash
# One-time: store the secret
vault kv put secret/bosch/mcp service_token="<real-token-from-your-vault-admin>"

# At service start: fetch into the process environment (never onto disk)
export BOSCH_MCP_TOKEN="$(vault kv get -field=service_token secret/bosch/mcp)"
```

Better: give the MCP server a Vault AppRole/agent sidecar and replace the
`vault()` helper in `mcp_server.py` with an `hvac` client call, so secrets are
fetched at call time with a short TTL and are rotatable without redeploys.

## Production pattern 2 — AWS Secrets Manager

```bash
export BOSCH_MCP_TOKEN="$(aws secretsmanager get-secret-value \
  --secret-id bosch/mcp/service-token \
  --query SecretString --output text)"
```

Or in code (replace the `vault()` helper): `boto3.client("secretsmanager")
.get_secret_value(SecretId=...)` with an IAM role scoped to exactly that
secret — least privilege applies to the server itself, not just its callers.

## Rules that survive the training room

1. **Env vars are the dev fallback, not the destination.** Production = Vault
   or ASM with rotation and per-service scoping.
2. **Never pass the client's token downstream.** The MCP authorization spec
   forbids token passthrough; the server exchanges for its *own* scoped
   credential (`TRACKER_TOKEN`), which is the confused-deputy defense.
3. **Audit the access, hash the payload.** The audit log stores an args hash,
   not raw arguments — logs must not become the new secret leak.
4. **If a secret ever appears in a prompt, treat it as burned** and rotate it.
