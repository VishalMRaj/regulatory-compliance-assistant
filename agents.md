# 🛡️ System Development Principles & Coding Guardrails
---

## 1. Code Style & "Human-Written" Professionalism

To maintain professional software engineering standards and eliminate typical AI generation patterns, follow these rules:

* **Zero Obvious Commenting:** Do not include comments that describe *what* standard Python syntax is doing (e.g., avoid `# loop through items` or `# initialize dictionary`). Comments must only be used to explain the structural or financial *why* behind complex regulatory logic or atypical workarounds.
* **Granular Functional Decomposition:** Monolithic blocks of code or deeply nested loops (greater than 2 levels) are strictly prohibited. Break operations down into clean, single-responsibility utility functions with explicit type hinting.
* **Production Logging over Prints:** Never use raw `print()` statements for application tracing. Utilize Python’s built-in `logging` module. Ensure log messages are structured, categorized by severity levels (`INFO`, `WARNING`, `ERROR`), and contain zero sensitive customer data or PII.

---

## 2. Architecture & Modularity Boundaries

The application must be completely modular and config-driven to isolate environmental variables from underlying logic patterns.

* **Strict Config-Driven Execution:** Hardcoded strings, model endpoints, collection names, thresholds, or API tokens inside functional code are forbidden. All variables must reside in `config/config.yaml`, and prompt templates must be isolated inside `config/prompts.yaml`.
* **The Config Loader Wrapper:** Implement a dedicated initialization component (`src/config_loader.py`) that reads configuration files at startup, instantiates parameters into native read-only data structures, and acts as the single source of truth for the workspace.
* **State Management Isolation:** In the `AGENTIC_CHECK` path, nodes must never mutate the shared `ComplianceGraphState` using side-channel parameters. State shifts must happen exclusively by returning explicitly declared dictionary keys back to the LangGraph edge runner.

---

## 3. Error Handling & Defensive Programming

Financial compliance engines must handle edge conditions gracefully without crashing or returning silent failures.

* **Typed Custom Exceptions:** Do not use generic, blank catch-all statements (e.g., `except Exception:`). Design explicit, descriptive custom error classes mapping to structural vulnerabilities, such as:
  * `VectorStoreConnectionError`
  * `PayloadValidationError`
  * `InferenceTimeoutError`
  * `StaleRegulatoryVersionError`
* **Graceful Degradation for Ambiguity:** If transaction payloads contain corrupted, incomplete, or ambiguous variables, the system must not halt execution. Instead, the logic must flag a special `AMBIGUOUS_DATA_INPUT` warning in the graph state, escalate the `risk_rating` to `HIGH`, and route the case directly to the `human_review` node with an explanation of what data is missing.

---

## 4. Database & Payload Mapping Invariants

When interacting with the local self-hosted **Qdrant** database, ensure perfect integration with historical Point-in-Time (PIT) auditing requirements.

* **Metadata Integrity:** Every vector payload inserted into the `regulatory_compliance` collection must strictly match the tracking keys specified in the design records. No chunk may be written without the following structured JSON fields:
  ```json
  {
    "text": "Raw regulatory string excerpt...",
    "doc_id": "Regulatory-Framework-ID",
    "version": "X.Y",
    "status": "active" or "superseded",
    "effective_start": "YYYY-MM-DD",
    "effective_end": "YYYY-MM-DD" or null,
    "jurisdiction": "IN" or "EU" or "US"
  }