# Implementing Mandatory Human Approval Gates with GitHub Copilot Hooks

## Introduction

GitHub Copilot Hooks provide a mechanism for executing custom logic at specific points during an agent's lifecycle. Hooks can be used to enforce governance, security controls, compliance requirements, audit logging, and workflow automation by executing external scripts before or after agent actions. GitHub supports several hook types, including `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `preToolUse`, and `postToolUse`. Among these, `preToolUse` is particularly powerful because it can explicitly allow or deny the execution of a tool before the action occurs.

One common enterprise use case is the implementation of **mandatory human approval gates**, where sensitive actions performed by an AI agent require explicit human authorization before execution. Examples include:

- Modifying production configuration files
- Deleting files or directories
- Executing shell commands
- Creating pull requests
- Deploying software
- Updating security policies
- Accessing regulated or sensitive repositories

By using `preToolUse` hooks, organizations can intercept the requested action, present it to a human reviewer, and either approve or deny execution according to governance requirements.

---

# Architecture

A typical human approval workflow consists of:

1. Copilot requests execution of a tool.
2. A `preToolUse` hook intercepts the request.
3. The hook sends the request details to an approval system.
4. A human reviewer approves or rejects the request.
5. The hook returns:
   - `allow` if approved.
   - `deny` if rejected.
6. Copilot proceeds or blocks the action.

```text id="69824"
Copilot Agent
      |
      v
  preToolUse Hook
      |
      v
 Approval Service
      |
      v
 Human Reviewer
      |
   +--+--+
   |     |
Approve Deny
   |     |
   v     v
Allow  Block
```

This pattern creates a deterministic security control that cannot be bypassed through prompt manipulation because the enforcement occurs outside the LLM.

---

# Example Hook Configuration

The following hook intercepts file modifications and shell commands.

File:

```text id="49518"
.github/hooks/human-approval.json
```

Configuration:

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "matcher": "bash|edit|create",
        "bash": "python3 .github/hooks/human_approval.py",
        "timeoutSec": 300
      }
    ]
  }
}
```

The matcher limits execution to:

- `bash`
- `edit`
- `create`

Other tools execute normally.

---

# Example Python Approval Script

The following example demonstrates a simple approval mechanism.

```python
#!/usr/bin/env python3

import json
import sys

payload = json.load(sys.stdin)

tool_name = payload.get("toolName")
tool_args = payload.get("toolArgs")

print("\n" + "=" * 60)
print("COPILOT ACTION REQUIRES APPROVAL")
print("=" * 60)
print(f"Tool : {tool_name}")
print("Arguments:")
print(json.dumps(tool_args, indent=2))
print("=" * 60)

response = input("Approve action? (yes/no): ").strip().lower()

if response == "yes":
    print(json.dumps({
        "permissionDecision": "allow"
    }))
    sys.exit(0)

print(json.dumps({
    "permissionDecision": "deny",
    "permissionDecisionReason":
        "Rejected by human reviewer"
}))
sys.exit(0)
```

The hook receives a JSON payload from Copilot containing information such as:

```json
{
  "sessionId": "abc123",
  "toolName": "edit",
  "toolArgs": {
    "file": "src/security.py"
  }
}
```

The script displays the requested operation and waits for a human decision before returning a valid `permissionDecision` response.

---

# Enterprise Implementation Using an Approval Service

In production environments, hooks are typically integrated with a centralized approval system instead of using terminal prompts.

Examples include:

- ServiceNow
- Jira Service Management
- GitHub Issues
- Microsoft Teams
- Slack
- Internal approval portals

Example workflow:

```python
import json
import requests
import sys

payload = json.load(sys.stdin)

approval_request = requests.post(
    "https://approval.company.com/api/request",
    json=payload
)

request_id = approval_request.json()["request_id"]

approval_status = requests.get(
    f"https://approval.company.com/api/status/{request_id}"
).json()

if approval_status["approved"]:
    print(json.dumps({
        "permissionDecision": "allow"
    }))
else:
    print(json.dumps({
        "permissionDecision": "deny",
        "permissionDecisionReason":
            "Approval denied by security reviewer"
    }))
```

This model enables separation of duties and supports compliance frameworks requiring human oversight.

---

# Using PostToolUse for Audit Logging

After approval and execution, a `postToolUse` hook can record the action for auditing purposes.

Example configuration:

```json
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      {
        "type": "command",
        "bash": "python3 .github/hooks/audit_logger.py"
      }
    ]
  }
}
```

Example audit logger:

```python
import json
from datetime import datetime
import sys

payload = json.load(sys.stdin)

entry = {
    "timestamp": datetime.utcnow().isoformat(),
    "tool": payload["toolName"],
    "result": payload["toolResult"]
}

with open("audit.log", "a") as f:
    f.write(json.dumps(entry) + "\n")
```

The resulting audit trail can be used for:

- Compliance evidence
- Security investigations
- Change management
- Operational reporting



---

# Example Governance Policies

Organizations commonly require approval for:

| Action | Required Approver |
|----------|------------------|
| Production deployment | Release Manager |
| Infrastructure changes | Platform Team |
| Security-sensitive files | Security Team |
| Database modifications | DBA Team |
| Access control changes | Security Administrator |
| Secret management operations | Security Administrator |

The hook logic can evaluate the requested action and route approval requests to the appropriate reviewer.

---

# Security Considerations

When implementing human approval gates:

1. Use `preToolUse` rather than relying solely on prompts.
2. Log all approval decisions.
3. Use authenticated approval systems.
4. Record approver identity and timestamps.
5. Apply least-privilege principles.
6. Fail closed for critical operations.
7. Protect approval APIs with strong authentication and authorization.
8. Periodically review approval records for compliance.

Because hooks execute outside the LLM and can directly allow or deny actions, they provide a stronger enforcement mechanism than prompt-based instructions or agent guidance. This makes them particularly suitable for cybersecurity, compliance, and regulated development environments.

---

# References

1. GitHub Docs – About Hooks for GitHub Copilot  
   https://docs.github.com/en/copilot/concepts/agents/hooks

2. GitHub Docs – GitHub Copilot Hooks Reference  
   https://docs.github.com/en/copilot/reference/hooks-reference

3. GitHub Docs – Customize Agent Workflows with Hooks  
   https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/use-hooks

4. Visual Studio Code Copilot Security Documentation  
   https://github.com/microsoft/vscode-docs/blob/main/docs/copilot/security.md