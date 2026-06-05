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

## 2. Detailed Quality-Attribute Trade-off Analysis (ATAM Framework)

Every structural element chosen for this project was evaluated using trade-off constraints across security, latency, and operational burden.

### ⚖️ Trade-off 1: Data Sovereignty & Privacy vs. Prototype Development Velocity
* **The Conflict:** Utilizing proprietary cloud-hosted LLM endpoints (such as OpenAI's GPT-4o or Anthropic's Claude 3.5 Sonnet) offers out-of-the-box reasoning capabilities and removes local compute configuration bottlenecks. However, transmitting financial transaction metadata, currency flows, and counterparty tracking variables outside the regional secure VPC introduces massive regulatory liabilities under GDPR and RBI localization guidelines.
* **The Architecture Trade-off Decision:** Adopt a **Self-Hosted Open-Source Model Strategy** utilizing **DeepSeek-R1-7B** for the localized prototyping sandbox, with a defined migration blueprint to **Qwen-2.5-72B-Instruct** on distributed enterprise clusters for production. This architecture prioritizes data privacy and compliance invariants over initial developer convenience.

### ⚖️ Trade-off 2: Runtime Latency vs. Compliance Invariant Validation
* **The Conflict:** Compliance systems must be fast enough to avoid bottlenecking banking transactions, but deep cross-referencing naturally adds processing time.
* **The Architecture Trade-off Decision:** Implement a **Dual-Path Routing Topology**. We use a responsive entry-point classification model (**Llama-3-8B**) to separate incoming traffic:
  1. `FAST_RAG Path`: Direct informational searches go straight to a single vector lookup, yielding sub-second responses.
  2. `AGENTIC_CHECK Path`: Multi-step transaction checks go to a sequential **LangGraph State Machine**. Although this adds 1-2 seconds of latency overhead due to step serialization and validation loops, it guarantees absolute compliance enforcement and structural zero-hallucination guardrails.

### ⚖️ Trade-off 3: System Component Proliferation vs. Resilient State Persistence
* **The Conflict:** Multi-agent applications often use memory caching tools like Redis for performance states, alongside traditional relational engines like PostgreSQL for application tables. However, every added infrastructure dependency increases the cognitive load on DevOps, multiplies failure vectors, and complicates disaster recovery footprints.
* **The Architecture Trade-off Decision:** Establish a **Unified Operational Data Footprint** using PostgreSQL via `langgraph-checkpoint-postgres`. We map our custom relational table (`compliance_sessions`) 1:1 with the underlying binary state snapshot table by equating `session_id == thread_id`. This choice allows us to handle distributed agent checkpointing, conversation memory, and user interactions within a single database node, reducing infrastructure overhead while maintaining complete resilience.

---

## 3. Storage Mechanics & Temporal Auditing Integrity

### ⏱️ Point-in-Time (PIT) Temporal Vector Auditing
Financial regulations change multiple times a year. If an auditor inspects a transaction executed three months ago, the AI assistant cannot evaluate it using the rules active today. 

To solve this without duplicating vector stores, we enforce a strict metadata append policy inside **Qdrant**. Documents are indexed alongside explicit temporal variables (`effective_start`, `effective_end`, and `status`). When retrieval is invoked, the engine applies an absolute logical expression:

$$\text{effective\_start} \le \text{timestamp} \quad \mathbf{AND} \quad \left( \text{effective\_end} \ge \text{timestamp} \quad \mathbf{OR} \quad \text{status} == \text{"active"} \right)$$

This ensures the model filters out any newly added rules and reasons exclusively over the text that was legally binding at the historical millisecond the transaction occurred.

---

## 4. Role-Based Human-in-the-Loop Workflow Realization

To prevent the application from outputting unchecked AI actions, we created three role-based interfaces powered by a single backend data footprint:

1. **The Compliance Officer Workspace:** Interfaces with a **LangGraph Breakpoint** at the `human_review` node. When a transaction triggers an anomaly flag, the graph halts execution and saves its variables to the Postgres checkpointer. The UI rehydrates this state, presenting the officer with an interactive task card where they must append review text and click a physical validation button to resume and clear the system thread.
2. **The Internal Auditor View:** Features an immutable ledger workspace. It drops the chat module entirely and provides a structured table linking transaction histories directly to deep-linked **Langfuse Trace Graph URLs** to visually prove exactly how the underlying LLM tokens arrived at a compliance decision.
3. **The Compliance Head Panel:** An executive overview monitoring screen displaying macro-level key performance indicators (SLA processing times, regional failure densities, policy parameter limits) to manage system health trends across global endpoints.