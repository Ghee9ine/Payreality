# PayReality

## Independent Control Validation Platform

**Did the money go where the system says it did?**

PayReality is a forensic desktop application that verifies whether payments processed by an ERP system actually went to approved vendors.

Traditional ERP controls enforce **syntactic compliance** — they validate format, not meaning. They cannot detect **identity hallucination** (vendor records that don't correspond to real entities) or **semantic drift** (the gradual divergence between legal names and payment system variations).

PayReality applies a multi-layered semantic approach to uncover discrepancies caused by typos, aliases, phonetic variations, or deliberate obfuscation. And it introduces **Control Entropy** — the first metric for measuring control effectiveness degradation over time.

---

## Quick Start

### Download Executable (No Python Required)

| Platform | Download |
|----------|----------|
| Windows | [PayReality.exe](dist/PayReality.exe) |

Just double-click to run. No installation. No dependencies.

### Or Run from Source

```bash
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality
pip install -r requirements.txt
python payreality_app.py
```

---

## Table of Contents

- [The PayReality Vocabulary](#the-payreality-vocabulary)
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
- [Pagination & Filtering](#pagination--filtering)
- [Trend Analysis](#trend-analysis)
- [Privacy-First Architecture](#privacy-first-architecture)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [Glossary](#glossary)
- [License](#license)
- [Contact](#contact)

---

## The PayReality Vocabulary

Category definition requires new language. PayReality introduces four terms that every auditor will need to know:

### Identity Hallucination

An ERP system creates a vendor record. The record has a name, an address, a tax ID. But the vendor doesn't actually exist as a legal entity. The ERP has hallucinated an identity.

**How it happens:** Data entry errors, system migrations, legacy imports, or deliberate fraud.

**Why it matters:** Payments to hallucinated vendors are unrecoverable. The money is gone.

**PayReality detects identity hallucination by:** Cross-referencing payment patterns, tenure anomalies, and structural vendor master inconsistencies.

### Semantic Drift

A vendor's legal name is "International Business Machines Corporation." Over time, your payment systems record it as "IBM," then "IBM Corp," then "IBM Global Services." Each variation is semantically identical but syntactically distinct.

**How it happens:** Normal business operations, acquisitions, rebranding, or different departments using different conventions.

**Why it matters:** Semantic drift creates false exceptions. Your ERP controls flag legitimate payments as violations. Audit hours wasted.

**PayReality detects semantic drift by:** Applying 7-pass semantic matching to link variations to the same canonical vendor.

### Control Entropy

The measurable degradation of control effectiveness over time. Every control has a half-life. Without independent validation, you cannot know when a control has failed.

**How it happens:** Process changes, personnel turnover, system updates, or deliberate evasion.

**Why it matters:** A control that worked last quarter may not work this quarter. Control Entropy is the first metric that tracks this decay.

**PayReality measures control entropy via:** The Control Entropy Score (CES), tracked over time and benchmarked against industry peers.

### Syntactic Compliance

The false sense of security when a payment passes format checks but fails meaning checks.

**Example:** The payee name "Micros0ft" passes ERP validation (non-empty, correct length, valid characters). But the payment did not go to Microsoft.

**Why it matters:** Most ERP controls only enforce syntactic compliance. They don't test semantic truth.

**PayReality exposes syntactic compliance by:** Testing every payment against semantic meaning, not just format rules.

---

## What is Control Entropy?

For 30 years, internal audit has relied on syntactic controls — matching characters, validating formats, checking boxes. These controls don't measure meaning. They measure compliance with process, not effectiveness of outcome.

**Control Entropy is the first metric that measures what actually matters: Did the control prevent the wrong payment?**

The Control Entropy Score (CES) is to audit what the credit score is to lending: A standardized, defensible, comparable metric that changes how the industry thinks about risk.

```
CES = (Unmatched Spend / Total Spend) × (1 - Confidence Weight) × Control Criticality
```

| CES Range | Interpretation |
|-----------|----------------|
| 0-20 | Low entropy — Controls effective |
| 21-50 | Medium entropy — Controls degraded |
| 51-80 | High entropy — Controls failing |
| 81-100 | Critical entropy — Controls compromised |

**Top quartile companies score below 20. What's your score?**

---

## Overview

Internal audit teams rely on ERP controls to enforce vendor integrity. However, these controls are syntactically compliant — they validate format, not meaning.

PayReality introduces an independent validation layer that tests whether those controls actually work in practice. It detects identity hallucination, maps semantic drift, and quantifies control entropy.

| Capability | PayReality |
|------------|------------|
| Analyzes 100% of transactions | ✅ |
| Requires no integrations | ✅ |
| Runs entirely offline | ✅ |
| Full audit trail with run IDs | ✅ |
| Professional PDF reports | ✅ |
| Standardized control metric (CES) | ✅ |
| Detects identity hallucination | ✅ |
| Maps semantic drift | ✅ |
| Quantifies control entropy | ✅ |

---

## Core Features

### 7-Pass Semantic Matching Engine

Detects hidden mismatches using seven progressive matching strategies. This is how PayReality maps semantic drift across your payment systems.

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

| Control ID | Control Name | Severity | Related Concept |
|------------|--------------|----------|-----------------|
| AVC | Approved Vendor Control | Critical | Syntactic Compliance |
| OBC | Obfuscation Detection Control | Critical | Identity Hallucination |
| VDC | Vendor Duplication Control | High | Semantic Drift |
| VNC | Vendor Name Consistency Control | High | Semantic Drift |
| VTC | Vendor Tenure Control | High | Identity Hallucination |
| PAC | Payment Authorization Control | Medium | Control Entropy |
| VMH | Vendor Master Health Control | Medium | Identity Hallucination |

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

Every exception includes a human-readable explanation that translates technical findings into audit language:

> "Phonetic match detected between 'Micosoft' and 'Microsoft' with 94% similarity. This represents semantic drift. Vendor tenure: 847 days active. Payment amount: $47,892 processed on Tuesday at 2:34 PM."

> "Payment processed on weekend, violating payment approval controls (CTL-004). Control Entropy Score impact: +4.7 points."

> "Obfuscation detected via leetspeak (3=E, 0=O). Potential identity hallucination. Recommend immediate vendor verification."

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

Evaluates structural quality of the vendor master to detect identity hallucination:

- Total vendors
- Duplicate records (semantic drift indicators)
- Blank names (potential hallucinations)
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

### Pagination & Filtering

- Load 25/50/100/250 exceptions per page
- Filter by risk level (High/Medium/Low)
- Filter by control type (AVC, OBC, etc.)
- Search by payee name
- Sort by confidence, amount, or risk

### Trend Analysis

- Historical CES tracking over time (control entropy visualization)
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

It acts as an independent validation layer within the audit process. It introduces the first standardized metric for control effectiveness: **The Control Entropy Score.**

It gives auditors language for phenomena they've always seen but never named: **Identity Hallucination. Semantic Drift. Syntactic Compliance.**

---

## Installation

### Download Executable (Recommended)

1. Download `PayReality.exe` from the [releases page](https://github.com/Ghee9ine/Payreality/releases) or the `dist` folder
2. Double-click to run
3. No Python required. No installation.

### Run from Source

**Prerequisites:** Python 3.10 or higher

```bash
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality
pip install -r requirements.txt
python payreality_app.py
```

---

## Usage Guide

### 1. Select Input Files

**Vendor Master**
- CSV or Excel
- Must contain a vendor name column (e.g., vendor_name, supplier, name)

**Payments**
- CSV, Excel, or PDF
- Must contain: payee_name, amount

### 2. Run Analysis

- Click Run Analysis
- Enter a client name
- Monitor progress via the status bar
- View your **Control Entropy Score** on the dashboard

### 3. Review Results

**Dashboard**
- KPI cards including CES
- Exception list with risk scores
- CES trend chart (control entropy over time)

**History**
- Past analyses with CES tracking
- Export to Excel

**Reports**
- Generated PDFs with CES prominently displayed
- Open within the app
- Email via SMTP

### File Requirements

| File Type | Required Columns |
|-----------|------------------|
| Vendor Master | vendor_name (or similar) |
| Payments | payee_name, amount |

**Supported formats:** CSV, Excel (.xlsx, .xls), PDF, Sage CSV

Reports are saved to: `Desktop/PayReality_Reports/`

---

## Configuration

After first run, edit `payreality_config.json`:

```json
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
```

---

## File Structure

```
Payreality/
├── payreality_app.py      # Main desktop application
├── src/
│   ├── core.py            # 7-pass engine, CES, audit trail
│   ├── parser.py          # CSV/Excel/PDF parsing
│   ├── reporting.py       # PDF report generation
│   └── config.py          # Configuration management
├── tests/
│   └── test_payreality.py # Unit tests (26 passing)
├── data/
│   ├── sample/
│   └── test_data/
├── logs/
├── dist/
│   └── PayReality.exe     # Standalone executable (no Python required)
├── generate_test_data.py
├── requirements.txt
└── README.md
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| App won't open | Make sure all files are extracted from zip |
| Missing columns | Rename to payee_name and amount |
| File not found | Use file browser |
| Empty file | Ensure at least one row |
| PDF extraction fails | Ensure PDF contains selectable text (OCR requires Tesseract) |
| No exceptions | Your vendor master may have all payments approved |

---

## Glossary

| Term | Definition |
|------|------------|
| **Control Entropy** | The measurable degradation of control effectiveness over time. Expressed as the Control Entropy Score (CES). |
| **Control Entropy Score (CES)** | A standardized metric (0-100) measuring control effectiveness. Lower is better. |
| **Identity Hallucination** | An ERP vendor record that does not correspond to a real legal entity. |
| **Semantic Drift** | The gradual divergence between a vendor's legal name and how they appear in payment systems. |
| **Syntactic Compliance** | Passing format-based controls while failing semantic truth. |
| **Independent Control Validation (ICV)** | The discipline of testing controls themselves, not just the transactions they process. |

---

## License

Proprietary – AI Securewatch

PayReality is a commercial product. Source code is private. For licensing inquiries, contact sean@aisecurewatch.com.

---

## Contact

**AI Securewatch**

Email: sean@aisecurewatch.com

GitHub: https://github.com/Ghee9ine/Payreality

---

## The Final Note

**What's your Control Entropy Score?**

If vendor controls have not been independently validated, their effectiveness cannot be assumed. Identity hallucination goes undetected. Semantic drift accumulates. Syntactic compliance creates false confidence.

PayReality is designed to be run as part of every audit cycle. Not because we say so. Because the CES doesn't lie.

---

*Control Entropy. Know your number.*
```
