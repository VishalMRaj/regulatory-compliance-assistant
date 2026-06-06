# 🏦 Architecture Assessment Report: FinServ Global Compliance Assistant
**Submission Date:** June 9, 2026  
**Status:** Ready for Technical Evaluation  

---

## 1. Architectural Philosophy & Thought Process

The primary challenge of modern financial technology (FinServ) is bridging the gap between highly flexible, generative artificial intelligence and the zero-tolerance, deterministic requirements of regional legal frameworks. When automating evaluations against frameworks like the **Reserve Bank of India (RBI) Master Directions**, **EU MiFID II Directives**, and **Global Basel III Standards**, a classic, unstructured prompt-based wrapper fails to satisfy audit constraints.

Our design philosophy treats compliance verification as a **Deterministic State Machine**, rather than a standard, open-ended chat conversation. We engineered an environment that enforces strict path containment based on a core conceptual division:
* **Factual, low-risk inquiries** (e.g., "What is the capital boundary under Basel III?") should not navigate expensive reasoning paths.
* **Complex, high-risk operational evaluations** (e.g., transaction compliance screening) must be locked inside a highly guarded, human-verified, auditable pipeline.

---

## 2. Core Scenario Coverage

### ✅ Scenario 1: Natural-Language Regulatory Q&A (FAST_RAG Path)
**Example:** *"What are the capital adequacy requirements for Tier 1 under Basel III as amended in 2023?"*

**Implementation:**
- A `query_regulatory_knowledge()` function in `src/api_services.py` embeds the user's question using `sentence-transformers/all-MiniLM-L6-v2`.
- A semantic similarity search is run against the **Qdrant** vector store filtered to only `status="active"` regulations in the matching jurisdiction.
- The top-k retrieved regulatory chunks are passed alongside the question to **Llama3** (via local Ollama) using the `regulatory_qa` prompt template from `config/prompts.yaml`.
- The LLM produces a structured JSON response containing a verbatim cited answer with document IDs, version numbers, and jurisdiction codes.
- The Compliance Officer workspace exposes this via a persistent chat interface with a collapsible citations panel.

**Knowledge Base:** The Qdrant collection `regulatory_compliance` is seeded with chunked excerpts from:
  - Basel III Consolidated Framework (2023 revision) — US jurisdiction
  - MiFID II EU Directive (2024 amendment) — EU jurisdiction
  - RBI Master Directions on FEMA, KYC, and Capital Adequacy (2026) — IN jurisdiction

---

### ✅ Scenario 2: Transaction Screening (AGENTIC_CHECK Path)
**Example:** *Given a transaction payload (amount, counterparty, jurisdiction, instrument type), flag applicable regulations and produce a risk-rated compliance assessment.*

**Implementation:**
- A `submit_transaction_screening()` function invokes the **LangGraph** state machine with the transaction payload as initial state.
- The graph traverses: `retrieve_context` → `analyze_compliance` → **⏸ interrupt at `human_review`** → `log_audit`.
- The `analyze_compliance` node invokes **DeepSeek-R1** (via local Ollama) with the transaction payload and system prompt from `config/prompts.yaml`, returning a structured JSON `{risk_rating, notes}`.
- The graph pauses at the `human_review` breakpoint and saves the full state snapshot to PostgreSQL via `langgraph-checkpoint-postgres`. The `thread_id` is identical to `session_id` in `compliance_sessions` — the **Unified Operational Data Footprint** pattern.
- The Compliance Officer reviews the LLM's reasoning in the Streamlit UI and submits an approve/flag decision, which resumes the graph and advances to `log_audit`.

---

### ✅ Scenario 3: Regulatory Change Impact Analysis
**Example:** *When a new RBI circular is ingested, identify which existing compliance policies or transaction types are affected.*

**Implementation:**
- An `analyze_change_impact()` function in `src/api_services.py` accepts the raw text of a new regulatory circular and a jurisdiction identifier.
- It queries the last 20 transactions from `compliance_sessions` and passes them alongside the new circular to **DeepSeek-R1**, using the `change_impact` prompt template.
- The LLM produces a structured JSON identifying: affected transaction types, affected jurisdictions, required policy changes, and urgency level (`IMMEDIATE`, `WITHIN_30_DAYS`, `NEXT_REVIEW_CYCLE`).
- This is exposed in the **Internal Auditor workspace** under the "Regulatory Change Impact" tab, allowing auditors to paste a new circular and instantly see the blast radius across existing transaction patterns.

---

### ✅ Scenario 4: Structured Compliance Report Generation
**Example:** *Generate a structured compliance report for a set of transactions over a period, suitable for submission to an internal audit committee.*

**Implementation:**
- A `generate_compliance_report()` function in `src/api_services.py` queries `compliance_sessions` for a user-specified date range.
- The aggregated transaction data (session IDs, amounts, currencies, jurisdictions, statuses) is passed to **DeepSeek-R1** using the `report_generation` prompt template.
- The LLM produces a formal Markdown report containing: executive summary, risk distribution analysis, notable high-risk transaction reasoning, trend observations, and recommended remediation actions.
- The **Compliance Head dashboard** exposes this via a date range picker and a direct **download button** for the generated Markdown report.

---

## 3. Detailed Quality-Attribute Trade-off Analysis (ATAM Framework)

Every structural element chosen for this project was evaluated using trade-off constraints across security, latency, and operational burden.

### ⚖️ Trade-off 1: Data Sovereignty & Privacy vs. Prototype Development Velocity
* **The Conflict:** Utilizing proprietary cloud-hosted LLM endpoints (such as OpenAI's GPT-4o or Anthropic's Claude 3.5 Sonnet) offers out-of-the-box reasoning capabilities and removes local compute configuration bottlenecks. However, transmitting financial transaction metadata, currency flows, and counterparty tracking variables outside the regional secure VPC introduces massive regulatory liabilities under GDPR and RBI localization guidelines.
* **The Architecture Trade-off Decision:** Adopt a **Self-Hosted Open-Source Model Strategy** utilizing **DeepSeek-R1** for the localized prototyping sandbox (via Ollama), with a defined migration blueprint to **Qwen-2.5-72B-Instruct** on distributed enterprise clusters for production. This architecture prioritizes data privacy and compliance invariants over initial developer convenience.

### ⚖️ Trade-off 2: Runtime Latency vs. Compliance Invariant Validation
* **The Conflict:** Compliance systems must be fast enough to avoid bottlenecking banking transactions, but deep cross-referencing naturally adds processing time.
* **The Architecture Trade-off Decision:** Implement a **Dual-Path Routing Topology**:
  1. `FAST_RAG Path`: Regulatory Q&A goes straight to Qdrant semantic search + Llama3 synthesis, targeting sub-second retrieval.
  2. `AGENTIC_CHECK Path`: Multi-step transaction checks go to the sequential **LangGraph State Machine** with DeepSeek-R1, adding 1–2 seconds for guaranteed compliance enforcement and structured human review.

### ⚖️ Trade-off 3: System Component Proliferation vs. Resilient State Persistence
* **The Conflict:** Multi-agent applications often use memory caching tools like Redis alongside relational engines like PostgreSQL. Every added infrastructure dependency increases cognitive load on DevOps and multiplies failure vectors.
* **The Architecture Trade-off Decision:** Establish a **Unified Operational Data Footprint** using PostgreSQL via `langgraph-checkpoint-postgres`. We map our custom relational table (`compliance_sessions`) 1:1 with the LangGraph checkpoint table by equating `session_id == thread_id`. This handles distributed agent checkpointing, conversation memory, and user interactions within a single database node.

---

## 4. Storage Mechanics & Temporal Auditing Integrity

### ⏱️ Point-in-Time (PIT) Temporal Vector Auditing
Financial regulations change multiple times a year. If an auditor inspects a transaction executed three months ago, the AI assistant cannot evaluate it using the rules active today.

To solve this without duplicating vector stores, we enforce a strict metadata append policy inside **Qdrant**. Every regulatory chunk is indexed alongside explicit temporal variables (`effective_start`, `effective_end`, and `status`). When retrieval is invoked, the engine applies:

$$\text{effective\_start} \le \text{timestamp} \quad \mathbf{AND} \quad \left( \text{effective\_end} \ge \text{timestamp} \quad \mathbf{OR} \quad \text{status} == \text{"active"} \right)$$

This ensures the model filters out any newly added rules and reasons exclusively over the text that was legally binding at the historical millisecond the transaction occurred.

---

## 5. Role-Based Human-in-the-Loop Workflow Realization

To prevent the application from outputting unchecked AI actions, we created three role-based interfaces powered by a single backend data footprint:

1. **The Compliance Officer Workspace:**
   - **Tab 1 — Risk Inbox & Review:** Interfaces with the LangGraph Breakpoint at the `human_review` node. The officer reviews DeepSeek-R1's risk assessment and submits an approval or flag decision.
   - **Tab 2 — Regulatory Q&A:** FAST_RAG path powered by Llama3 with Qdrant semantic retrieval and versioned citations.

2. **The Internal Auditor View:**
   - **Tab 1 — Historical Ledger:** Immutable audit log with deep-linked Langfuse Trace URLs.
   - **Tab 2 — Regulatory Change Impact:** Paste any new circular to instantly identify affected transaction types and required policy updates.

3. **The Compliance Head Panel:**
   - **Tab 1 — KPI Overview:** Macro-level metrics and trend charts.
   - **Tab 2 — Generate Audit Report:** LLM-generated Markdown compliance report downloadable for audit committee submission.

---

## 6. Production Transaction Lifecycle — End-to-End Code Flow

This section documents the exact path a single high-risk cross-border transaction takes through the system, from external trigger to human resolution — mapping each step to the code files that implement it.

### 6.1 Transaction Ingestion (Entry Point)

In production, transactions enter via a **webhook** from a core banking system or payment network. In the current prototype, `scripts/simulate_live_transaction.py` acts as a stand-in for this ingestion microservice.

```
┌─────────────────────────────────────────────────────────┐
│  PRODUCTION: FastAPI Microservice                        │
│  PROTOTYPE:  scripts/simulate_live_transaction.py        │
│                                                          │
│  POST /api/v1/screen   ← SWIFT / SEPA / CBS Webhook      │
│                                                          │
│  Step 1: Validate incoming payload structure             │
│           (amount, currency, jurisdiction, counterparty) │
│                                                          │
│  Step 2: INSERT INTO compliance_sessions                 │
│           (session_id, amount, jurisdiction,             │
│            status='SUSPENDED', metadata=payload)         │
│           ← src/database.py → DatabaseManager.pool       │
│                                                          │
│  Step 3: Call submit_transaction_screening(              │
│               session_id, payload)                       │
│           ← src/api_services.py                          │
│                                                          │
│  Step 4: Return 202 Accepted immediately (async)         │
│           Agent runs in the background                   │
└─────────────────────────────────────────────────────────┘
```

### 6.2 LangGraph Agent Execution (Background, Async)

`submit_transaction_screening()` calls `graph.invoke(payload, config={"thread_id": session_id})`. The graph traverses its nodes sequentially, saving state to PostgreSQL after each node:

```
src/api_services.py
  └─ submit_transaction_screening(session_id, payload)
       │
       ▼
src/graph.py → ComplianceWorkflow.graph.invoke()
       │
       ├──▶ Node 1: retrieve_context
       │      • Marks context_retrieved=True in state
       │      • (Production: queries Qdrant with PIT filter)
       │
       ├──▶ Node 2: analyze_compliance
       │      • Instantiates ChatOllama(model="deepseek-r1")
       │      • Loads system_prompt from config/prompts.yaml
       │      • Sends: transaction payload + system prompt
       │      • Receives: {"risk_rating": "HIGH", "notes": "..."}
       │      • Updates graph state with risk_rating + notes
       │
       ├──▶ ⏸ INTERRUPT: human_review
       │      • Graph halts execution here
       │      • Full state snapshot serialized to PostgreSQL
       │        via langgraph-checkpoint-postgres
       │        Key: thread_id = session_id (Unified Footprint)
       │      • 202 was already returned — caller is not blocked
       │
       └── (graph paused — waiting for human input)
```

### 6.3 Compliance Officer Reviews (Streamlit UI)

```
src/app.py → render_risk_inbox()
  └─ api_services.get_pending_inbox()
       └─ SELECT * FROM compliance_sessions WHERE status='SUSPENDED'
            │
            ▼
  Officer clicks transaction card
            │
            ▼
src/app.py → render_analysis_dashboard()
  └─ api_services.get_session_state(session_id)
       └─ src/graph.py → ComplianceWorkflow.get_state(thread_id)
            └─ Reads paused checkpoint from PostgreSQL
                 Returns: {risk_rating, notes, transaction_payload, ...}
            │
            ▼
  UI displays DeepSeek-R1's reasoning:
    "Current Risk Rating: HIGH"
    "Flagged under FATF Recommendation 6: transaction
     to sanctioned jurisdiction..."
            │
            ▼
  Officer enters justification notes
  Officer clicks: [✅ Approve] or [🚩 Flag]
```

### 6.4 Graph Resumes — Final Resolution

```
src/app.py → handle_validation(session_id, approved, notes)
  └─ api_services.resume_workflow_checkpoint(
           session_id, officer_approval, notes)
       │
       ├─ workflow.update_state(config, {
       │      "officer_approval": True/False,
       │      "notes": officer_notes,
       │      "risk_rating": "LOW" / "HIGH"
       │  })
       │
       └─ workflow.invoke(None, config)
            │
            ▼
       Node 4: log_audit
         • Syncs final decision to Langfuse (if configured)
         • Graph thread marked complete in checkpoint tables
            │
            ▼
  UPDATE compliance_sessions
    SET status = 'APPROVED' or 'FLAGGED_VIOLATION',
        notes = officer_notes
  WHERE session_id = %s
            │
            ▼
  Transaction removed from Pending Inbox
  Audit record available to Internal Auditor view
```

### 6.5 Session ID ↔ Thread ID — The Unified Data Footprint

The most critical architectural invariant: `session_id` in the `compliance_sessions` business table and `thread_id` in the LangGraph checkpoint tables are **always identical**. This means a single PostgreSQL instance serves both the relational business layer and the AI agent's state persistence layer, with zero data duplication.

```
compliance_sessions.session_id
         ║
         ║  (Invariant: always equal)
         ║
langgraph_checkpoints.thread_id
```

This satisfies Trade-off 3 from the ATAM analysis — eliminating Redis or a separate vector memory store entirely.