The **NIST AI Risk Management Framework (AI RMF) 1.0** organizes AI risk management into four continuous functions:

* **Govern** – establish policies, oversight, accountability, and culture.
* **Map** – understand the AI system, context, stakeholders, and risks.
* **Measure** – assess, test, monitor, and quantify risks.
* **Manage** – prioritize and respond to identified risks. ([NIST][1])

The **NIST Generative AI Profile (NIST AI 600-1)** extends the AI RMF specifically for Generative AI and identifies **12 risk areas that are unique to or significantly amplified by GenAI systems**. ([NIST][2])

## The 12 Generative AI Risk Areas

| #  | Risk Area                                  | Description                                                                                                                                                                                             |
| -- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **CBRN Information or Capabilities**       | Models may provide information, designs, procedures, or assistance related to chemical, biological, radiological, or nuclear threats, lowering the barrier to dangerous activities. ([Modulos Docs][3]) |
| 2  | **Confabulation**                          | Generation of false, fabricated, or misleading information presented as if it were factual. Commonly known as hallucinations. ([Modulos Docs][3])                                                       |
| 3  | **Dangerous, Violent, or Hateful Content** | Production of content that encourages violence, self-harm, illegal activities, extremism, harassment, or hate speech. ([Modulos Docs][3])                                                               |
| 4  | **Data Privacy**                           | Exposure, inference, memorization, or leakage of sensitive information such as PII, health data, financial data, or confidential enterprise information. ([Modulos Docs][3])                            |
| 5  | **Environmental Impact**                   | High energy consumption, carbon footprint, water usage, and other environmental costs associated with training and operating large AI models. ([Modulos Docs][3])                                       |
| 6  | **Harmful Bias and Homogenization**        | Reinforcement of societal biases, unfair outcomes, discrimination, and reduction of diversity in generated content or decision support. ([Modulos Docs][3])                                             |
| 7  | **Human-AI Configuration**                 | Risks arising from inappropriate human reliance on AI, overtrust, automation bias, anthropomorphism, or unclear allocation of responsibility between humans and AI. ([Modulos Docs][3])                 |
| 8  | **Information Integrity**                  | Generation and large-scale dissemination of misinformation, disinformation, manipulated content, deepfakes, or content lacking provenance and authenticity. ([Modulos Docs][3])                         |
| 9  | **Information Security**                   | Use of GenAI to facilitate cyberattacks, malware creation, phishing, vulnerability discovery, or attacks against AI systems themselves. ([Modulos Docs][3])                                             |
| 10 | **Intellectual Property (IP)**             | Risks involving copyright infringement, trade secrets, proprietary data, licensing violations, and ownership disputes over generated content. ([Modulos Docs][3])                                       |
| 11 | **Obscene, Degrading, or Abusive Content** | Generation of sexually explicit, abusive, exploitative, degrading, or otherwise harmful content, including content involving vulnerable populations. ([Modulos Docs][3])                                |
| 12 | **Value Chain and Component Integration**  | Risks introduced through third-party models, datasets, plugins, APIs, open-source components, supply-chain dependencies, and external service providers. ([Modulos Docs][3])                            |

## Grouping the Risks for Security and Governance

For cybersecurity and AI governance practitioners, the 12 risks are often viewed in four broader categories:

### 1. Safety Risks

* CBRN Information
* Dangerous Content
* Obscene/Abusive Content
* Human-AI Configuration

These focus on preventing direct harm to individuals and society.

### 2. Trustworthiness Risks

* Confabulation
* Information Integrity
* Harmful Bias and Homogenization

These affect whether users can trust AI-generated outputs.

### 3. Security and Privacy Risks

* Information Security
* Data Privacy
* Intellectual Property

These are particularly relevant to enterprise security, compliance, and cybersecurity programs.

### 4. Operational and Ecosystem Risks

* Environmental Impact
* Value Chain and Component Integration

These address sustainability, third-party dependencies, and supply-chain concerns.

## Relationship to AI RMF Functions

The GenAI Profile does not replace the AI RMF. Instead, it maps mitigation activities for these 12 risks into the four AI RMF functions:

| AI RMF Function | Example Question                                            |
| --------------- | ----------------------------------------------------------- |
| **Govern**      | Who is accountable for GenAI risks?                         |
| **Map**         | Which of the 12 risks apply to this use case?               |
| **Measure**     | How are those risks tested and quantified?                  |
| **Manage**      | What controls, monitoring, and mitigations are implemented? |

The NIST GenAI Profile provides hundreds of recommended actions that organizations can use to manage these risks throughout the AI lifecycle. ([NIST][2])

For a cybersecurity audience, the three most relevant categories are usually **Information Security**, **Data Privacy**, and **Information Integrity**, while **Human-AI Configuration** has become increasingly important because many incidents arise from users placing excessive trust in AI-generated outputs. ([Modulos Docs][3])

[1]: https://www.nist.gov/itl/ai-risk-management-framework?utm_source=chatgpt.com "AI Risk Management Framework | NIST"
[2]: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence?utm_source=chatgpt.com "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile | NIST"
[3]: https://docs.modulos.ai/frameworks/nist-ai-rmf/generative-ai-profile?utm_source=chatgpt.com "NIST AI RMF Generative AI Profile (NIST AI 600-1) — 12 Official Risk Categories and Operationalization | Modulos Docs"
