# AI Usage & Contribution Disclosure

**Project**: Industrial Safety Monitoring System (SAFEGUARD)  
**Author / Candidate**: Gudepu Rakshitha Reddy  
**Date**: October 2026  

---

## 1. AI Tooling & Purpose

During the development of the Industrial Safety Monitoring System, modern AI coding assistants (including Google DeepMind Antigravity and LLM-assisted pair programming tools) were utilized as productivity and design accelerators:

- **Architecture Exploration**: Brainstorming relational entity models and ISA-18.2 compliance rules.
- **Boilerplate & Test Generation**: Generating parameterized pytest cases, edge-case generation scenarios, and mock DDL definitions.
- **Component Styling & Layout**: Refining CSS styling for Streamlit navigation, responsive typography, and card grids.

---

## 2. Engineering Oversight & Human Contribution

All AI-suggested code, schemas, and configurations were subject to strict manual review, architectural decision-making, and empirical verification by the candidate:

1. **Domain Logic Formulation**:
   - The candidate established the activation-denominated policy for acknowledgement metrics (ensuring that unacknowledged alarms correctly diminish compliance scores rather than being omitted from denominators).
   - Designed the exact lifecycle state machines (`ACTIVE > ACKNOWLEDGED > CLEARED` and `OPEN > INVESTIGATING > CLOSED`).
2. **Deterministic Data Integrity**:
   - Implemented fixed-seed stream decoupling (`SEED = 20261022`) to guarantee cross-platform idempotency and bit-for-bit reproducible dataset compilation.
3. **Anomaly Detection & Harness Design**:
   - Hand-crafted the 5 negative scenario injection rules (`ACK_BEFORE_ALARM`, `INTERLOCK_STATE_MISMATCH`, `INCIDENT_WITHOUT_VALID_TRIGGER`, `DUPLICATE_ALARM_REPLAY`, `CLOSED_WITHOUT_VERIFICATION`) and the corresponding negative controls to ensure zero false positives.
4. **Code Review & Quality Control**:
   - Refactored UI CSS to prevent container clipping and remove redundant Streamlit widgets.
   - Pinned dependency bounds for Python 3.12/3.14 environments.
   - Audited every pandas query and join for data leakage.

---

## 3. Verification & Validation Framework

To ensure 100% correctness without relying on unverified AI outputs, the following validation framework is permanently embedded into the project:

- **Static Schema Assertions**: `src/validate_data.py` (94 automated checks verifying referential integrity, types, and chronological causality).
- **Edge-Case Benchmarking**: `src/validate_edge_cases.py` (asserts 100% precision and 100% recall on injected anomalies vs ground truth).
- **Unit & Integration Suite**: `tests/` (69 pytest unit tests verifying schema, generators, metrics, filters, lifecycle states, exports, and UI components).
