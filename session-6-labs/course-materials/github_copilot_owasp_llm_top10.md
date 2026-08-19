The **OWASP Top 10 for LLM Applications (2025)** is the most widely used security framework for Generative AI and LLM-based systems. It identifies the ten most critical security risks affecting applications that use LLMs, RAG systems, copilots, chatbots, and AI agents. ([OWASP][1])

## OWASP LLM Top 10 (2025)

| ID        | Risk                             | Description                                                                                                                                                                   |
| --------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLM01** | Prompt Injection                 | Malicious instructions manipulate the model into ignoring intended behavior or revealing information. Includes direct and indirect prompt injection attacks. ([SecPortal][2]) |
| **LLM02** | Sensitive Information Disclosure | Leakage of secrets, credentials, personal data, proprietary information, embeddings, or training data. ([OWASP Gen AI Security Project][3])                                   |
| **LLM03** | Supply Chain Vulnerabilities     | Risks originating from third-party models, datasets, plugins, agents, APIs, MCP servers, vector databases, and external AI services. ([OWASP Gen AI Security Project][3])     |
| **LLM04** | Data and Model Poisoning         | Manipulation of training, fine-tuning, or RAG data to alter model behavior or create hidden backdoors. ([OWASP Gen AI Security Project][3])                                   |
| **LLM05** | Improper Output Handling         | Failure to validate model outputs before passing them to downstream systems, potentially leading to code execution, command injection, or business logic abuse. ([OWASP][4])  |
| **LLM06** | Excessive Agency                 | Granting the model excessive permissions, tool access, or autonomous decision-making authority without adequate controls. ([OWASP][1])                                        |
| **LLM07** | System Prompt Leakage            | Exposure of hidden system prompts, policies, instructions, or internal reasoning structures that attackers can use to bypass safeguards. ([OWASP][1])                         |
| **LLM08** | Vector and Embedding Weaknesses  | Attacks against RAG systems, vector stores, embeddings, retrieval pipelines, and semantic search mechanisms. ([OWASP][4])                                                     |
| **LLM09** | Misinformation                   | Generation of inaccurate, fabricated, deceptive, or manipulated information that users may trust as factual. ([OWASP][4])                                                     |
| **LLM10** | Unbounded Consumption            | Excessive use of tokens, API calls, tool invocations, compute resources, or agent loops leading to denial of service or excessive cost. ([OWASP][1])                          |

---

# OWASP Top 10 for Agentic Applications (2026)

As AI systems evolved from chatbots into autonomous agents capable of planning, using tools, maintaining memory, and performing actions, OWASP introduced a dedicated **Agentic Top 10**. These risks focus on the unique security challenges of autonomous AI agents. ([OWASP Gen AI Security Project][5])

| ID        | Risk                                 | Description                                                                                                                                                       |
| --------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ASI01** | Agent Goal Hijacking                 | An attacker manipulates an agent's objectives so it pursues goals different from those intended by the user or system owner. ([OWASP Gen AI Security Project][6]) |
| **ASI02** | Tool Misuse                          | Agents misuse legitimate tools, APIs, or services to perform harmful, unauthorized, or unintended actions. ([OWASP Gen AI Security Project][6])                   |
| **ASI03** | Identity and Privilege Abuse         | Compromise or misuse of credentials, permissions, tokens, or identities used by agents. ([OWASP Gen AI Security Project][6])                                      |
| **ASI04** | Agentic Supply Chain Vulnerabilities | Vulnerabilities in MCP servers, plugins, tools, external agents, datasets, or third-party dependencies. ([OWASP Gen AI Security Project][6])                      |
| **ASI05** | Unexpected Code Execution            | Agent workflows enable unintended execution of commands, scripts, or code through natural language interactions. ([OWASP Gen AI Security Project][6])             |
| **ASI06** | Memory and Context Poisoning         | Malicious information inserted into agent memory or context affects future decisions and actions. ([OWASP Gen AI Security Project][6])                            |
| **ASI07** | Insecure Inter-Agent Communication   | Agents exchange untrusted or spoofed messages, causing misinformation, manipulation, or unauthorized actions. ([OWASP Gen AI Security Project][6])                |
| **ASI08** | Cascading Failures                   | Errors or malicious actions propagate through multi-agent systems, causing amplified failures across workflows. ([OWASP Gen AI Security Project][6])              |
| **ASI09** | Human-Agent Trust Exploitation       | Users place excessive trust in agent recommendations and approve harmful actions. ([OWASP Gen AI Security Project][6])                                            |
| **ASI10** | Rogue Agents                         | Agents exhibit unintended autonomous behavior, conceal actions, bypass controls, or operate outside intended objectives. ([OWASP Gen AI Security Project][6])     |

## Mapping to Cybersecurity Concerns

For a cybersecurity architecture review, the risks can be grouped as follows:

| Area                | OWASP LLM | OWASP Agentic |
| ------------------- | --------- | ------------- |
| Prompt Manipulation | LLM01     | ASI01         |
| Data Poisoning      | LLM04     | ASI06         |
| Supply Chain        | LLM03     | ASI04         |
| Privilege Abuse     | LLM06     | ASI03         |
| Code Execution      | LLM05     | ASI05         |
| RAG Security        | LLM08     | ASI06         |
| Human Factors       | LLM09     | ASI09         |
| Autonomous Behavior | LLM06     | ASI10         |
| Resource Abuse      | LLM10     | ASI08         |
| Multi-Agent Risks   | —         | ASI07, ASI08  |

A useful observation is that the **OWASP LLM Top 10** focuses on securing a model-centric application, while the **OWASP Agentic Top 10** focuses on securing autonomous systems that can **plan, remember, communicate, invoke tools, and take actions in the real world**. This makes ASI03–ASI10 particularly relevant for modern agentic frameworks such as AutoGen, CrewAI, OpenAI Agents SDK, LangGraph, Semantic Kernel Agents, MCP-based systems, and GitHub Copilot coding agents. ([OWASP Gen AI Security Project][6])

[1]: https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf?utm_source=chatgpt.com "OWASP Top 10 for"
[2]: https://secportal.io/frameworks/owasp-llm-top-10?utm_source=chatgpt.com "OWASP Top 10 for LLM Applications | 2025 Framework"
[3]: https://genai.owasp.org/llm-top-10/?cat=253&utm_source=chatgpt.com "LLMRisks – OWASP Gen AI Security Project"
[4]: https://owasp.org/www-chapter-stuttgart/assets/slides/2025-02-11_AI_Security_And_Insights_Into_OWASP_Top_10_LLM.pdf?utm_source=chatgpt.com "OWASP_Meeting Stuttgart"
[5]: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/?utm_source=chatgpt.com "OWASP Top 10 for Agentic Applications for 2026 - OWASP Gen AI Security Project"
[6]: https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/?utm_source=chatgpt.com "OWASP Top 10 for Agentic Applications - The Benchmark for Agentic Security in the Age of Autonomous AI - OWASP Gen AI Security Project"
