# Responsible AI & Data Privacy Policy

The **Reliability Cockpit for AI Agents** is designed with enterprise-grade data privacy, security, and Responsible AI principles at its foundation.

---

## 1. Data Minimization & Privacy Protection

- **Local Storage Architecture:** All execution traces, span logs, chaos injection events, and judge verdicts are stored exclusively in your local environment (`./data/reliability_cockpit.db`). Zero trace data or telemetry is transmitted to third-party telemetry collectors or remote cloud servers.
- **PII Anonymization:** Scenario inputs and order lookup payloads use synthetic, masked customer identifiers (e.g. `ORD-8821`, `USR-102`). Real customer names, credit card numbers, or live email addresses are strictly forbidden in test fixtures.
- **LLM API Payload Security:** Interactivity with external LLM endpoints (Google Gemini API) is restricted strictly to the user prompt and tool definitions. No background database contents or local file system contents are sent to the model provider.

---

## 2. Responsible AI & Safety Guardrails

- **Deterministic Tool Execution:** Tool calls (such as `process_refund` and `order_lookup`) operate under strict business rule validation. For example, high-value refunds (> Rs. 10,000) require explicit quality inspection flags and cannot be automated without policy compliance.
- **Cost & Round Limits:** To prevent runaway loops, infinite recursion, or API cost explosion, the system enforces hard caps:
  - Max Adversarial/Chaos Rounds: `5`
  - Max Session Budget Cap: `$2.00 USD`
- **Adversarial Red-Teaming Guardrails:** Prompt injection payloads (F06) and cost spiral attacks (F07) are evaluated in isolated sandboxes to analyze agent vulnerability without exposing underlying infrastructure.

---

## 3. Data Retention & Cleanup Policy

- **Trace Lifecycle:** Local trace logs are retained for auditability during active testing cycles.
- **Database Reset / Purge:** Users can purge all past evaluation data at any time by removing `./data/reliability_cockpit.db` or triggering the DB reset utility.

---

## 4. Multi-Tenancy & Access Controls

- **API Key Gate:** Production deployments enforce API key validation using the `X-API-Key` header or `DASHBOARD_SECRET_KEY` environment variable.
- **Public Upload Hygiene:** Sensitive configuration files (`.env`) are excluded via `.gitignore` to prevent secret key leakage.
