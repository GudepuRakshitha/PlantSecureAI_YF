# SAFEGUARD — Industrial Safety Monitoring & Intelligence System

A full-stack, enterprise-grade industrial safety monitoring platform engineered to ingest plant sensor telemetry, monitor safety interlocks, analyze alarm lifecycles, and track operator acknowledgement SLAs across distributed manufacturing facilities.

Developed by **Gudepu Rakshitha Reddy**  
*Computer Science Engineer | AI/ML Specialist | Project Developer*

---

## System Overview

Industrial plants operate hundreds of critical machines protected by automated safety zones and interlocks. When operational anomalies occur, alarm management systems must deliver actionable, timely notifications to operators while preventing alarm floods and chattering.

**SAFEGUARD** delivers end-to-end operational visibility:
- **Master Data & Asset Modeling**: Tracks 4 industrial plants, 12 safety zones, 60 heavy machines (presses, robots, conveyors, pumps, motors), and 120 safety interlocks.
- **Alarm Intelligence & Event Ingestion**: Evaluates 50,000 alarm event activations across 200 alarm definitions with sub-second timestamps and state transition logs (`ACTIVE > ACKNOWLEDGED > CLEARED`).
- **ISA-18.2 Aligned Metrics**: Employs activation-denominated compliance calculations to accurately penalize unacknowledged alarms, with mean, median, and p95 response time distributions.
- **Anomaly & Pattern Detection**: Identifies chattering alarms ($\ge 3$ triggers in 60 min), alarm floods ($\ge 10$ alarms in 10 min), and routine SLA breaches.
- **Edge-Case Safety Verification**: Evaluates 5 critical safety anomalies (pre-activation acknowledgements, impossible interlock states, ungrounded incidents, duplicate alarm replays, and unverified closures) with 100% precision and recall against isolated ground truth.
- **Incident & Corrective Action Traceability**: Manages end-to-end incident workflows (`OPEN > INVESTIGATING > CLOSED`) with verified corrective action audits.
- **Interactive Multi-View Dashboard**: Executive overview, real-time alarm monitoring, acknowledgement compliance, incident tracking, exception analysis, database browser, and integrated developer portfolio.

---

## Key Performance Indicators (Baseline Population)

| Metric | Measured Value | Standard / Target |
|---|:---:|:---:|
| **Total Alarm Activations** | 50,000 | 30-day baseline (Oct 2026) |
| **Monitored Plants & Machines** | 4 Plants · 60 Machines | Distributed across 12 safety zones |
| **Overall Acknowledgement Rate** | 90.06% | Activation-denominated |
| **On-Time Acknowledgement Compliance** | 72.20% | Within alarm SLA limit |
| **Routine SLA Breaches** | 8,930 (17.86%) | Delayed response |
| **Unacknowledged Alarms** | 4,969 (9.94%) | Non-compliant activations |
| **Median Response Time** | 4.0 min (p95: 13.0 min) | Mean: 4.49 min |
| **Open & Investigating Incidents** | 58 Incidents | Linked to corrective action pipelines |
| **Edge-Case Anomaly Detection** | 100% Precision / 100% Recall | Zero false positives on negative controls |

---

## Quickstart & Installation

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12+ (tested on Python 3.12 & 3.14)
- Git

### 2. Environment Setup
```bash
# Clone repository
git clone https://github.com/GudepuRakshitha/yottaflex_industrial-safety-monitoring-system.git
cd yottaflex_industrial-safety-monitoring-system

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Run Validations & Test Suite
```bash
# Run baseline data integrity assertions (94 checks)
python src/validate_data.py

# Run edge-case scenario detection benchmark (40 checks, 1.00 Precision / 1.00 Recall)
python src/validate_edge_cases.py

# Execute full pytest unit & smoke test suite (69 tests)
python -m pytest tests -v
```

### 4. Compile Database & Launch Dashboard
```bash
# Compile relational SQLite database with views and indexes
python src/build_database.py

# Launch the interactive Streamlit monitoring dashboard
streamlit run dashboard/app.py
```
*The dashboard will be available at: `http://localhost:8501`*

---

## Architecture & Codebase Layout

```
├── dashboard/
│   ├── app.py              # Main Streamlit application and page orchestrator
│   ├── components.py       # Reusable UI widgets, KPI cards, and charts
│   ├── profile.py          # Developer Portfolio & Profile view
│   └── theme.py            # Visual design tokens, Plotly styling, and CSS
├── data/
│   ├── plants.csv          # Master plant locations and statuses
│   ├── machines.csv        # 60 machines with safety zones and types
│   ├── safety_zones.csv    # 12 safety zones with risk levels
│   ├── interlocks.csv      # 120 safety interlocks with operational states
│   ├── alarm_definitions.csv # 200 alarm definitions with severity and SLAs
│   ├── alarm_events.csv    # 50,000 deterministic alarm activations
│   ├── acknowledgements.csv# 45,031 operator acknowledgement records
│   ├── operator_shifts.csv # Roster and shift schedules
│   ├── incidents.csv       # Triggered safety incidents
│   ├── corrective_actions.csv # Corrective actions and verification audits
│   ├── sla_breaches.csv    # Computed routine SLA breaches
│   └── scenarios/          # Isolated injected anomalies & ground truth
├── src/
│   ├── config.py           # Centralized configuration, thresholds, and seeds
│   ├── data_access.py      # Schema enforcement, type coercions, and caching
│   ├── metrics.py          # ISA-18.2 compliance calculations & statistics
│   ├── detection.py        # Rule-based anomaly detector & scoring engine
│   ├── pipeline.py         # End-to-end data pipeline orchestrator
│   ├── generator.py        # Deterministic master data generator
│   ├── event_generator.py  # Seeded alarm event generator
│   ├── transaction_generator.py # Shift, acknowledgement & incident generator
│   ├── inject_edge_cases.py # Scenario injection engine
│   ├── safety_analyzer.py  # Automated baseline analytical report generator
│   └── build_database.py   # Relational SQLite compiler with SQL views
├── sql/
│   └── schema.sql          # Relational DDL schema, foreign keys, and views
├── docs/
│   ├── architecture.md     # In-depth architectural specification
│   ├── data_dictionary.md  # Comprehensive entity schema and column types
│   ├── validation_report.md# Baseline data validation results
│   └── PROJECT_REVIEW.md   # System engineering and domain review
├── tests/                  # 69 automated unit, integration, and UI smoke tests
├── requirements.txt        # Production runtime dependencies
└── requirements-dev.txt    # Testing & development dependencies
```

---

## Technical Documentation

- [**System Architecture Guide**](docs/architecture.md): Deep dive into data pipelines, state machines, and caching layers.
- [**Data Dictionary**](docs/data_dictionary.md): Exhaustive column definitions, foreign keys, data types, and cardinalities for all 10 entities.
- [**Validation Report**](docs/validation_report.md): Audit results for referential integrity, event causality, and lifecycle consistency.
- [**Project Engineering Review**](docs/PROJECT_REVIEW.md): Architectural decisions, edge-case rationale, and operational trade-offs.

---

## Developer Portfolio

**Gudepu Rakshitha Reddy**  
- **Degree**: B.Tech in Computer Science & Engineering (Specialization in AI & ML), Alliance University, Bengaluru (CGPA: 8.9/10)
- **Expertise**: Python, Java, Spring Boot, SQL, Machine Learning, Deep Learning, Natural Language Processing, Generative AI
- **Research**: 7 peer-reviewed publications in IEEE and Springer
- **Certifications**: 100+ verified technical certifications
- **Profiles**:
  - [LinkedIn](https://www.linkedin.com/in/gudepu-rakshitha-reddy-516aa72a9/)
  - [GitHub](https://github.com/GudepuRakshitha)
  - [ResearchGate](https://www.researchgate.net/profile/Rakshitha-Reddy-Gudepu)
  - [Technical Blogs](https://www.blogger.com/profile/08555579845123121571)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
