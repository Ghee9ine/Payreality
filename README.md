# PayReality

## Independent Control Validation Platform

**Did the money go where the system says it did?**

PayReality is a forensic desktop application that verifies whether payments processed by an ERP system actually went to approved vendors.

Traditional ERP controls rely on exact or near-exact matching. PayReality applies a multi-layered semantic approach to uncover discrepancies caused by typos, aliases, phonetic variations, or deliberate obfuscation.

But PayReality doesn't just find exceptions. It introduces a new audit metric: **The Control Entropy Score (CES)** — the first standardized measure of control effectiveness.

---

## Table of Contents

- [What is Control Entropy?](#what-is-control-entropy)
- [Overview](#overview)
- [Core Features](#core-features)
- [7-Pass Semantic Matching Engine](#7-pass-semantic-matching-engine)
- [Control Taxonomy](#control-taxonomy)
- [Control Entropy Score (CES)](#control-entropy-score-ces)
- [Confidence Scoring](#confidence-scoring)
- [Risk Scoring](#risk-scoring)
- [Explainability Layer](#explainability-layer)
- [Audit Trail](#audit-trail)
- [Vendor Master Health Scoring](#vendor-master-health-scoring)
- [Reporting & Exports](#reporting--exports)
- [Trend Analysis](#trend-analysis)
- [Privacy-First Architecture](#privacy-first-architecture)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contact](#contact)

---

## What is Control Entropy?

For 30 years, internal audit has relied on syntactic controls — matching characters, validating formats, checking boxes. These controls don't measure meaning. They measure compliance with process, not effectiveness of outcome.

**Control Entropy is the first metric that measures what actually matters: Did the control prevent the wrong payment?**

The Control Entropy Score (CES) is to audit what the credit score is to lending: A standardized, defensible, comparable metric that changes how the industry thinks about risk.
CES = (Unmatched Spend / Total Spend) × (1 - Confidence Weight) × Control Criticality

text

| CES Range | Interpretation |
|-----------|----------------|
| 0-20 | Low entropy — Controls effective |
| 21-50 | Medium entropy — Controls degraded |
| 51-80 | High entropy — Controls failing |
| 81-100 | Critical entropy — Controls compromised |

**Top quartile companies score below 20. What's your score?**

---

## Overview

Internal audit teams rely on ERP controls to enforce vendor integrity. However, these controls are syntactic — they validate format, not meaning.

PayReality introduces an independent validation layer that tests whether those controls actually work in practice.

| Capability | PayReality |
|------------|------------|
| Analyzes 100% of transactions | ✅ |
| Requires no integrations | ✅ |
| Runs entirely offline | ✅ |
| Full audit trail with run IDs | ✅ |
| Professional PDF reports | ✅ |
| Standardized control metric (CES) | ✅ |

---

## Core Features

### 7-Pass Semantic Matching Engine

Detects hidden mismatches using seven progressive matching strategies:

| Pass | Strategy | Description |
|------|----------|-------------|
| 1 | Exact | Perfect character-for-character match |
| 2 | Normalized | Case, punctuation, and suffix removal |
| 3 | Token Sort | Handles word order variations |
| 4 | Partial | Handles extra words (e.g., department names) |
| 5 | Levenshtein | Catches typos and character transpositions |
| 6 | Phonetic | Matches similar-sounding names (Soundex) |
| 7 | Obfuscation | Detects dot-spacing, leetspeak, homoglyphs, character repetition |

### Control Taxonomy

Each finding is mapped to a specific control type:

| Control ID | Control Name | Severity |
|------------|--------------|----------|
| AVC | Approved Vendor Control | Critical |
| OBC | Obfuscation Detection Control | Critical |
| VDC | Vendor Duplication Control | High |
| VNC | Vendor Name Consistency Control | High |
| VTC | Vendor Tenure Control | High |
| PAC | Payment Authorization Control | Medium |
| VMH | Vendor Master Health Control | Medium |

### Control Entropy Score (CES)

Measures the percentage of total spend that bypassed approved vendor controls, weighted by confidence and control criticality. Provides a direct indicator of control effectiveness, not just isolated failures.

**CES is calculated per analysis run and tracked over time to show control degradation or improvement.**

### Confidence Scoring

Each exception receives a confidence score (0-100) based on:

- Match strength from the 7-pass engine
- Strategy reliability weights
- Number of agreeing passes
- Historical accuracy
- Contextual factors (amount, tenure, duplicates)

| Confidence | Interpretation |
|------------|----------------|
| 90-100 | High confidence – Investigate immediately |
| 70-89 | Medium confidence – Review recommended |
| 50-69 | Low confidence – Manual verification advised |
| <50 | Very low confidence – Likely false positive |

### Risk Scoring

Automatically classifies findings based on:

- Spend magnitude
- Vendor tenure (first seen, last seen, active days)
- Duplicate payment patterns
- Weekend or off-cycle payments
- Obfuscation detection
- Confidence score

**Outputs:** High Risk, Medium Risk, Low Risk

### Explainability Layer

Every exception includes a human-readable explanation:

> *"Phonetic match detected between 'Micosoft' and 'Microsoft' with 94% similarity. Vendor tenure: 847 days active. Payment amount: $47,892 processed on Tuesday at 2:34 PM."*

> *"Payment processed on weekend, violating payment approval controls (CTL-004)."*

> *"Obfuscation detected via leetspeak (3=E, 0=O) — potential fraud indicator."*

### Audit Trail

Every analysis run is logged with:

- Unique Run ID
- Timestamp
- Client name
- File hashes (SHA256)
- Configuration snapshot
- Processing time
- Full exception details

All data stored locally in SQLite database with tamper-evident hashing.

### Vendor Master Health Scoring

Evaluates structural quality of the vendor master:

- Total vendors
- Duplicate records
- Blank names
- Short names (potential junk data)
- Overall health score (0-100)

### Reporting & Exports

| Format | Purpose |
|--------|---------|
| PDF | Executive reports with control summaries, CES, recommendations |
| JSON | Structured data for GRC system integration |
| CSV | Flat file for audit management systems |
| Excel | History export for trend analysis |

**White-label PDF reports** available for audit firm partners.

### Trend Analysis

- Historical CES tracking over time
- Visual trend chart on dashboard
- Store unlimited analysis history
- Export history to Excel
- Benchmark against industry averages (coming 2026)

### Privacy-First Architecture

- Fully offline
- No data leaves your machine
- No external integrations
- No telemetry
- File hashes for evidence, not tracking

---

## Why PayReality?

Most tools:

- Enforce controls
- Reconcile transactions
- Monitor activity

**PayReality verifies whether the control itself is trustworthy.**

It acts as an independent validation layer within the audit process. And it introduces the first standardized metric for control effectiveness: **The Control Entropy Score.**

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Clone Repository

```bash
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality
Virtual Environment
macOS/Linux:

bash
python -m venv venv
source venv/bin/activate
Windows:

bash
python -m venv venv
venv\Scripts\activate
Install Dependencies
bash
pip install -r requirements.txt
Run Application
bash
python payreality_app.py
Usage Guide
1. Select Input Files
Vendor Master

CSV or Excel

Must contain a vendor name column (e.g., vendor_name, supplier, name)

Payments

CSV, Excel, or PDF

Must contain: payee_name, amount

2. Run Analysis
Click Run Analysis

Enter a client name

Monitor progress via the status bar

View your Control Entropy Score on the dashboard

3. Review Results
Dashboard

KPI cards including CES

Exception list with risk scores

CES trend chart

History

Past analyses with CES tracking

Export to Excel

Reports

Generated PDFs with CES prominently displayed

Open within the app

Email via SMTP

File Requirements
File Type	Required Columns
Vendor Master	vendor_name (or similar)
Payments	payee_name, amount
Supported formats: CSV, Excel (.xlsx, .xls), PDF, Sage CSV

Reports are saved to: Desktop/PayReality_Reports/

Configuration
After first run, edit payreality_config.json:

json
{
  "thresholds": {
    "exact": 100,
    "normalized": 100,
    "token_sort": 80,
    "partial": 80,
    "levenshtein": 75,
    "phonetic": 80,
    "obfuscation": 80
  },
  "ces": {
    "criticality_weights": {
      "AVC": 1.0,
      "OBC": 1.0,
      "VDC": 0.8,
      "VNC": 0.7,
      "VTC": 0.6,
      "PAC": 0.4,
      "VMH": 0.3
    }
  }
}
File Structure
text
Payreality/
├── src/
│   ├── core.py
│   ├── parser.py
│   ├── reporting.py
│   └── config.py
├── data/
│   ├── sample/
│   └── test_data/
├── logs/
├── payreality_app.py
├── generate_test_data.py
├── requirements.txt
└── README.md
Troubleshooting
Problem	Solution
Missing columns	Rename to payee_name and amount
File not found	Use file browser
Empty file	Ensure at least one row
PDF extraction fails	Ensure PDF contains selectable text (OCR requires Tesseract)
License
Proprietary – AI Securewatch

PayReality is a commercial product. Source code is private. For licensing inquiries, contact sean@aisecurewatch.com.

Contact
AI Securewatch

Email: sean@aisecurewatch.com

GitHub: https://github.com/Ghee9ine/Payreality

The Final Note
What's your Control Entropy Score?

If vendor controls have not been independently validated, their effectiveness cannot be assumed.

PayReality is designed to be run as part of every audit cycle. Not because we say so. Because the CES doesn't lie.
