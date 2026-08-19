# GitHub Copilot Policy System

GitHub Copilot governance policies are organized into three primary categories:

1. Feature Policies
2. Privacy Policies
3. Model Policies

These policies allow Enterprise and Business administrators to control Copilot functionality, data handling, and model availability across organizations and enterprises.

---

# 1. Feature Policies

Feature policies control which Copilot capabilities, interfaces, and services users can access.

| Feature Policy | Description |
|---------------|-------------|
| Copilot in GitHub.com | Enables Copilot features directly within the GitHub web interface. |
| Copilot Chat in the IDE | Enables Copilot Chat in supported IDEs such as VS Code and JetBrains. |
| Copilot Chat in GitHub Mobile | Enables Copilot Chat functionality in the GitHub Mobile application. |
| Copilot Chat Agent Mode in the IDE | Allows the use of Agent Mode within Copilot Chat. |
| Copilot CLI | Enables GitHub Copilot CLI capabilities. |
| GitHub Copilot App | Allows use of Copilot extensions and applications integrated with GitHub. |
| Copilot Code Review | Enables AI-assisted pull request code reviews. |
| Copilot Cloud Agent | Enables cloud-hosted coding agents and delegated tasks. |
| GitHub Spark | Enables access to GitHub Spark capabilities. |
| Copilot Can Search the Web | Allows Copilot to retrieve information from web sources. |
| MCP Servers in Copilot | Enables Model Context Protocol (MCP) server integrations. |
| Copilot-Generated Commit Messages | Allows Copilot to generate commit messages automatically. |
| Editor Preview Features | Grants access to preview and experimental editor features. |
| Allow Members Without a Copilot License to Use Copilot Code Review in GitHub.com | Permits code review functionality for users without assigned Copilot licenses. |

---

# 2. Privacy Policies

Privacy policies govern how data is processed, stored, and used by Copilot.

| Privacy Policy | Description |
|---------------|-------------|
| Suggestions Matching Public Code | Controls whether suggestions matching public code are allowed. |
| Semantic Indexing for Non-GitHub Repositories | Controls semantic indexing of repositories outside GitHub. |
| Copilot Metrics API | Controls access to Copilot usage and metrics data through APIs. |

Privacy policies generally follow the most restrictive policy when multiple organizational policies apply to a user.

---

# 3. Model Policies

Model policies govern which AI models are available to users.

| Model Policy | Description |
|-------------|-------------|
| Default Model Availability | Defines the default set of models available to users. |
| Availability of Individual Models | Allows administrators to enable or disable specific models. |
| Targeted Model Rules | Restricts model access to specific organizations or user groups. |
| Default Availability for Newly Released Models | Controls whether newly released models are automatically available. |

---

# Policy Categories Summary

| Category | Number of Policies |
|-----------|------------------|
| Feature Policies | 14 |
| Privacy Policies | 3 |
| Model Policies | 3-4 |
| Total | Approximately 20 |

---

# References

- GitHub Docs: Copilot Policies
  https://docs.github.com/en/copilot/concepts/policies

- GitHub Docs: Managing Policies and Features
  https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-organization/manage-policies

- GitHub Blog: Target Copilot Models to Organizations with Model Rules
  https://github.blog/changelog/2026-05-26-target-copilot-models-to-organizations-with-model-rules/

---

## Notes

- Feature policies determine which Copilot capabilities are available to users.
- Privacy policies govern security, compliance, and data handling.
- Model policies control access to foundation models and future model releases.
- Organizations and enterprises can combine these policies to implement governance, security, and compliance requirements for GitHub Copilot deployments.