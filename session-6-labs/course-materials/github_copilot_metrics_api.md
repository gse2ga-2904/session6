Below is an example Python script that retrieves data from the **GitHub Copilot Metrics API**, normalizes the response, and emits one JSON log entry per user/model/feature combination similar to your example.

The script assumes:

1. You are using **GitHub Enterprise Cloud**.
2. You have an organization-level token with permissions to access Copilot metrics.
3. You want JSON Lines (`.jsonl`) output for ingestion into a SIEM, data lake, Splunk, ELK, Azure Sentinel, etc.
4. Team information is obtained from GitHub Teams APIs because the Copilot Metrics API does not directly associate users with teams.

---

# Architecture

```text
+--------------------+
| Copilot Metrics API|
+---------+----------+
          |
          v
+--------------------+
| Metrics Collector  |
+---------+----------+
          |
          v
+--------------------+
| Team Resolution    |
| GitHub Teams API   |
+---------+----------+
          |
          v
+--------------------+
| JSONL Audit Log    |
+--------------------+
```

Example output:

```json
{
  "report_date": "2026-06-29",
  "login": "mgarcia",
  "team": "chassis-braking",
  "model": "claude-sonnet-4.6",
  "feature": "agent_mode",
  "requests": 41,
  "input_tokens": 1830000,
  "output_tokens": 122000,
  "credits": 220.0,
  "pr_number": null,
  "blocker_findings": null
}
```

---

## Python Script

```python
#!/usr/bin/env python3

"""
copilot_usage_audit.py

Collects GitHub Copilot usage metrics and produces
normalized JSON logs for audit and governance.

Requirements:
    pip install requests

Environment Variables:
    GITHUB_TOKEN
    GITHUB_ORG
"""

import os
import json
import requests
from collections import defaultdict

GITHUB_API = "https://api.github.com"

TOKEN = os.environ["GITHUB_TOKEN"]
ORG = os.environ["GITHUB_ORG"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def get_org_teams():
    """
    Build login -> team mapping.
    """

    mapping = defaultdict(list)

    teams_url = f"{GITHUB_API}/orgs/{ORG}/teams"

    while teams_url:
        r = requests.get(teams_url, headers=HEADERS)
        r.raise_for_status()

        for team in r.json():

            slug = team["slug"]

            members_url = (
                f"{GITHUB_API}/orgs/{ORG}/teams/{slug}/members"
            )

            members = requests.get(
                members_url,
                headers=HEADERS
            )

            members.raise_for_status()

            for member in members.json():
                mapping[member["login"]].append(slug)

        teams_url = None

    return mapping


def get_copilot_metrics():
    """
    Retrieves Copilot metrics.
    """

    url = (
        f"{GITHUB_API}/orgs/"
        f"{ORG}/copilot/metrics"
    )

    r = requests.get(url, headers=HEADERS)

    r.raise_for_status()

    return r.json()


def normalize_metrics(metrics, team_map):

    records = []

    for day in metrics:

        report_date = day["date"]

        for editor in day.get("copilot_ide_code_completions", []):

            for model in editor.get("models", []):

                login = model.get("user_login")

                teams = team_map.get(login, ["unknown"])

                for team in teams:

                    record = {
                        "report_date": report_date,
                        "login": login,
                        "team": team,
                        "model": model.get("name"),
                        "feature": "code_completion",
                        "requests":
                            model.get("total_engaged_users", 0),
                        "input_tokens":
                            model.get("input_tokens", 0),
                        "output_tokens":
                            model.get("output_tokens", 0),
                        "credits":
                            model.get("premium_requests", 0),
                        "pr_number": None,
                        "blocker_findings": None
                    }

                    records.append(record)

        #
        # Agent mode metrics
        #

        for agent in day.get("copilot_chat", []):

            for model in agent.get("models", []):

                login = model.get("user_login")

                teams = team_map.get(login, ["unknown"])

                for team in teams:

                    record = {
                        "report_date": report_date,
                        "login": login,
                        "team": team,
                        "model": model.get("name"),
                        "feature": "agent_mode",
                        "requests":
                            model.get("total_chats", 0),
                        "input_tokens":
                            model.get("input_tokens", 0),
                        "output_tokens":
                            model.get("output_tokens", 0),
                        "credits":
                            model.get("premium_requests", 0),
                        "pr_number": None,
                        "blocker_findings": None
                    }

                    records.append(record)

    return records


def write_jsonl(records,
                output_file="copilot_usage_audit.jsonl"):

    with open(output_file, "w", encoding="utf-8") as fp:

        for record in records:
            fp.write(json.dumps(record))
            fp.write("\n")

    print(
        f"Wrote {len(records)} records "
        f"to {output_file}"
    )


def main():

    print("Resolving teams...")
    teams = get_org_teams()

    print("Retrieving Copilot metrics...")
    metrics = get_copilot_metrics()

    print("Normalizing...")
    records = normalize_metrics(
        metrics,
        teams
    )

    write_jsonl(records)


if __name__ == "__main__":
    main()
```

---

## Example Execution

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxx
export GITHUB_ORG=my-org

python copilot_usage_audit.py
```

Generated file:

```json
{"report_date":"2026-06-29","login":"mgarcia","team":"chassis-braking","model":"claude-sonnet-4.6","feature":"agent_mode","requests":41,"input_tokens":1830000,"output_tokens":122000,"credits":220.0,"pr_number":null,"blocker_findings":null}
{"report_date":"2026-06-29","login":"jcruz","team":"vehicle-platform","model":"gpt-5","feature":"agent_mode","requests":55,"input_tokens":2210000,"output_tokens":171000,"credits":312.0,"pr_number":null,"blocker_findings":null}
```

### Extending for Audit Evidence

In many organizations, the most useful enrichment fields are:

```json
{
  "repository": "brake-controller",
  "pull_request": 1458,
  "branch": "feature/abs-improvement",
  "model": "claude-sonnet-4.6",
  "feature": "agent_mode",
  "copilot_review": true,
  "blocker_findings": 2,
  "security_findings": 1,
  "accepted_suggestions": 34,
  "rejected_suggestions": 12,
  "credits": 220.0
}
```

These additional fields can be joined from:

* Copilot Metrics API
* Pull Request API
* Code Scanning API
* Dependabot Alerts API
* GitHub Advanced Security APIs

to create a comprehensive **Copilot governance and audit trail** aligned with NIST AI RMF, OWASP LLM Top 10, and internal SDLC compliance requirements.
