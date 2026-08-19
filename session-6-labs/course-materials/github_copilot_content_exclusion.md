# GitHub Copilot Content Exclusion

## Overview

**Content exclusion** is a GitHub Copilot governance feature that allows repository, organization, and enterprise administrators to prevent Copilot from accessing specific files or directories. Excluded content is ignored by Copilot when generating code suggestions, answering chat questions, and performing code reviews.

This feature is commonly used to protect sensitive code, proprietary intellectual property, credentials, security-related files, generated artifacts, and other content that should not be used as AI context.

### Effects of Content Exclusion

When content is excluded:

* Copilot inline code suggestions are not available within the excluded files.
* Excluded files are not used as context for suggestions generated in other files.
* Copilot Chat does not use excluded files when generating responses.
* Copilot Code Review ignores excluded files.

### Limitations

Content exclusion is not supported by all GitHub Copilot experiences. Certain agent-based capabilities, including some Agent Mode and Copilot CLI scenarios, may not honor content exclusions. Organizations should review the latest GitHub documentation before relying on content exclusion for governance or compliance requirements.

---

## Configuring Content Exclusion for a Repository

To configure content exclusion at the repository level:

1. Open the target repository in GitHub.
2. Select **Settings**.
3. Navigate to **Copilot** → **Content exclusion**.
4. Under **Paths to exclude in this repository**, add one exclusion pattern per line.
5. Save the configuration.

---

## Example Exclusion Patterns

```text
# Exclude a specific file
/src/security/secrets.json

# Exclude all configuration files
*.cfg

# Exclude all files under scripts
/scripts/**

# Exclude files beginning with 'secret'
secret*
```

GitHub supports **fnmatch/glob-style patterns**, allowing administrators to exclude:

* Individual files
* File extensions
* Directories
* Recursive directory structures

Patterns are evaluated according to GitHub's documented matching rules.

---

## Verifying the Configuration

After configuring content exclusion:

1. Reload the IDE or wait for policy synchronization.
2. Open a non-excluded file and verify that Copilot suggestions continue to work.
3. Open an excluded file and verify that Copilot suggestions are no longer available.
4. Use Copilot Chat and attempt to reference an excluded file; the file should not be used as context for responses.
5. Run a Copilot Code Review and verify that excluded files are omitted from the review context.

---

## Common Cybersecurity Use Cases

Content exclusion is particularly useful for protecting sensitive assets such as:

* Secret and credential files (`.env`, `secrets.json`)
* Cryptographic keys and certificates
* Security-sensitive source code
* Compliance and regulatory documentation
* Proprietary algorithms
* Generated artifacts and build outputs
* Internal security testing tools
* Proof-of-concept exploit code
* Incident response documentation

By excluding these assets, organizations can reduce the risk of sensitive information being incorporated into Copilot-generated suggestions, chat responses, or code review outputs.

---

## Benefits

* Protects sensitive and proprietary information.
* Supports organizational security and compliance requirements.
* Reduces the risk of AI-assisted disclosure of confidential code.
* Provides centralized governance of Copilot context sources.
* Helps enforce secure development practices across repositories.

---

## References

1. GitHub Docs – Content Exclusion for GitHub Copilot
   https://docs.github.com/en/copilot/concepts/context/content-exclusion

2. GitHub Docs – Exclude Content from GitHub Copilot
   https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot

3. GitHub Docs – GitHub Copilot Policies and Governance
   https://docs.github.com/en/copilot/concepts/policies
