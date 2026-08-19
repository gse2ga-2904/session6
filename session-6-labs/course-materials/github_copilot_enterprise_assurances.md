
---

## 1. IP Indemnity (Business & Enterprise)


### What is IP indemnity?

Indemnity is a contractual commitment where GitHub agrees to defend and compensate customers if a third party claims that Copilot-generated code infringes intellectual property rights.

This is particularly important because Copilot models were trained on publicly available code repositories.

### Why does the Public Code Filter matter?

GitHub provides a **public code matching filter** that detects when a suggestion closely resembles publicly available code.

For indemnification protection, organizations are generally expected to:

* Enable the filter
* Set it to **Block**
* Prevent developers from accepting matching code verbatim

This reduces the likelihood that generated code contains copyrighted material from public repositories.

### Audit Evidence

Auditors typically request:

* Enterprise Copilot policy screenshots
* Public code filter configuration
* Legal review of GitHub indemnity terms
* Software development policy referencing Copilot use

### Risk Addressed

* Copyright infringement
* Open-source license contamination
* Software IP disputes

---

## 2. Data Handling (Business & Enterprise)

For Copilot Business and Enterprise:

* Customer prompts are not used to train GitHub foundation models.
* Code snippets are not used to improve public models.
* Data is encrypted during transmission.
* IDE completions and chat interactions have limited or no persistent storage depending on the feature being used. ([GitHub][1])

### Important Audit Distinction

Auditors often ask:

> "Is our source code used to train Copilot?"

For Business and Enterprise customers:

**No.** GitHub states that customer data is not used for model training. ([GitHub Docs][2])

### Retention Details

GitHub documents that:

* IDE completions and IDE chat prompts are generally not retained.
* Some web-based experiences may temporarily retain prompts and responses to support conversation history and service functionality. ([GitHub][1])

### Risk Addressed

* Source code leakage
* Trade secret exposure
* Training-data contamination
* Privacy concerns

---

## 3. Data Residency (GitHub Enterprise Cloud Data Residency)

### What is Data Residency?

Data residency ensures that:

* Prompts
* Source code
* Responses
* Telemetry associated with Copilot

remain within a designated geographic region during AI processing. ([GitHub Docs][3])

Currently supported regions include:

* United States
* European Union ([GitHub Docs][3])

### Why Auditors Care

Many regulations require:

* Data sovereignty
* Geographic processing restrictions
* Regional privacy controls

Examples:

* GDPR
* Schrems II considerations
* Public-sector requirements
* Financial-sector regulations

### Operational Considerations

GitHub notes:

* Data residency is a policy setting.
* It is disabled by default.
* Only approved regional models become available.
* Enabling it increases AI-credit consumption by approximately 10%. ([GitHub Docs][3])

### Audit Evidence

* Enterprise policy configuration
* Region selection documentation
* Data Processing Agreement (DPA)

---

## 4. Anthropic Models under Zero Data Retention (ZDR)

### What is Zero Data Retention?

A Zero Data Retention (ZDR) agreement means the model provider:

* Processes prompts
* Returns results
* Does not retain prompts or outputs after processing (subject to limited exceptions) ([Claude][4])

### Why This Matters

Many enterprises prohibit:

* Source code storage by third parties
* Long-term prompt retention
* External training on proprietary data

GitHub states that generally available Anthropic models used through Copilot operate under a zero-data-retention agreement. ([GitHub Docs][2])

### Auditor Questions

Typical audit questions include:

* Is customer code retained by Anthropic?
* Is customer code used for training?
* Is there contractual protection against retention?

GitHub's provider agreements are intended to address these concerns. ([GitHub Docs][2])

### Risk Addressed

* Intellectual property exposure
* Third-party data retention
* Supply-chain privacy concerns

---

## 5. Certifications

### SOC 2 Type II

Evaluates effectiveness of operational controls over time.

Covers:

* Security
* Availability
* Confidentiality
* Processing integrity

For auditors this demonstrates that controls are operating continuously rather than existing only on paper.

---

### ISO/IEC 27001

International standard for Information Security Management Systems (ISMS).

Demonstrates:

* Risk management processes
* Security governance
* Continuous improvement

Auditors frequently map this to:

* NIST CSF
* NIST 800-53
* ISO 27002

---

### GDPR and DPA

GitHub provides Data Processing Agreements that support GDPR compliance. ([GitHub][1])

This helps organizations demonstrate:

* Lawful processing
* Processor obligations
* Cross-border transfer controls
* Privacy governance

### Audit Evidence

* SOC 2 report
* ISO certificate
* DPA
* Trust Center documentation

---

## 6. FedRAMP

### What is FedRAMP?

**Federal Risk and Authorization Management Program (FedRAMP)** is the U.S. government framework for assessing and authorizing cloud services.

It is particularly relevant for:

* Federal agencies
* Defense contractors
* Government suppliers
* Critical infrastructure organizations

### GitHub Copilot and FedRAMP

GitHub provides controls that allow organizations to:

* Restrict Copilot to FedRAMP-compliant models
* Use approved model endpoints
* Enforce compliance-oriented deployment policies ([GitHub Docs][5])

When enabled:

* Only approved models can be used.
* Compliance-certified infrastructure is enforced.
* AI-credit consumption increases by approximately 10%. ([GitHub Docs][5])

### Auditor Perspective

* Security controls are documented
* Controls are independently assessed
* Continuous monitoring is performed
* Government-specific requirements are satisfied

### Risk Addressed

* Government compliance
* Public-sector procurement requirements
* NIST 800-53 alignment

---

[1]: https://github.com/features/copilot/plans?utm_source=chatgpt.com "GitHub Copilot · Plans & pricing · GitHub"
[2]: https://docs.github.com/en/enterprise-cloud%40latest/copilot/reference/ai-models/model-hosting?utm_source=chatgpt.com "Hosting of models for GitHub Copilot - GitHub Enterprise Cloud Docs"
[3]: https://docs.github.com/en/enterprise-cloud%40latest/admin/data-residency/github-copilot-with-data-residency?utm_source=chatgpt.com "GitHub Copilot with data residency - GitHub Enterprise Cloud Docs"
[4]: https://code.claude.com/docs/en/zero-data-retention?utm_source=chatgpt.com "Zero data retention - Claude Code Docs"
[5]: https://docs.github.com/en/copilot/concepts/models/fedramp-models?utm_source=chatgpt.com "FedRAMP-compliant models for GitHub Copilot - GitHub Docs"
