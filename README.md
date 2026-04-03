# PayReality

## Independent Control Verification Platform

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

PayReality is a forensic desktop application that verifies whether payments processed by an ERP system actually went to approved vendors.

Traditional ERP controls rely on exact or near-exact matching. PayReality applies a multi-layered semantic approach to uncover discrepancies caused by typos, aliases, phonetic variations, or deliberate obfuscation.

> **Did the money go where the system says it did?**

---

## Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [7-Pass Semantic Matching Engine](#7-pass-semantic-matching-engine)
- [Control Taxonomy](#control-taxonomy)
- [Confidence Scoring](#confidence-scoring)
- [Risk Scoring](#risk-scoring)
- [Explainability Layer](#explainability-layer)
- [Audit Trail](#audit-trail)
- [Vendor Master Health Scoring](#vendor-master-health-scoring)
- [Reporting & Exports](#reporting--exports)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contact](#contact)

---

## Overview

Internal audit teams rely on ERP controls to enforce vendor integrity. However, these controls are *syntactic* — they validate format, not meaning.

PayReality introduces an **independent validation layer** that tests whether those controls actually work in practice.

- ✅ Analyzes 100% of transactions
- ✅ Requires no integrations
- ✅ Runs entirely offline
- ✅ Full audit trail with run IDs
- ✅ Professional PDF reports

---

## Core Features

### 7-Pass Semantic Matching Engine

Detects hidden mismatches using seven progressive matching strategies:

| Pass | Strategy | Description |
|------|----------|-------------|
| 1 | **Exact** | Perfect character-for-character match |
| 2 | **Normalized** | Case, punctuation, and suffix removal |
| 3 | **Token Sort** | Handles word order variations |
| 4 | **Partial** | Handles extra words (e.g., department names) |
| 5 | **Levenshtein** | Catches typos and character transpositions |
| 6 | **Phonetic** | Matches similar-sounding names (Soundex) |
| 7 | **Obfuscation** | Detects dot-spacing, leetspeak, homoglyphs, character repetition |

### Control Taxonomy

Each finding is mapped to a specific control type:

| Control ID | Control Name | Severity |
|------------|--------------|----------|
| **AVC** | Approved Vendor Control | Critical |
| **OBC** | Obfuscation Detection Control | Critical |
| **VDC** | Vendor Duplication Control | High |
| **VNC** | Vendor Name Consistency Control | High |
| **VTC** | Vendor Tenure Control | High |
| **PAC** | Payment Authorization Control | Medium |
| **VMH** | Vendor Master Health Control | Medium |

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

- *"Phonetic match detected between 'Micosoft' and 'Microsoft' with 94% similarity"*
- *"Payment processed on weekend, violating payment approval controls (CTL-004)"*
- *"Obfuscation detected via leetspeak (3=E, 0=O) — potential fraud indicator"*

### Audit Trail

Every analysis run is logged with:

- Unique Run ID
- Timestamp
- Client name
- File hashes (SHA256)
- Configuration snapshot
- Processing time
- Full exception details

All data stored locally in SQLite database.

### Vendor Master Health Scoring

Evaluates structural quality of the vendor master:

- Total vendors
- Duplicate records
- Blank names
- Short names (potential junk data)
- Overall health score (0-100)

### Pagination & Filtering

The Exceptions tab supports:

- **Pagination:** 100 rows per page with Previous/Next buttons
- **Filtering:** By risk level (High/Medium/Low)
- **Filtering:** By control type (AVC, OBC, VDC, etc.)
- **Sorting:** By confidence, risk score, amount, or alphabetically
- **Search:** By payee name

### Reporting & Exports

| Format | Purpose |
|--------|---------|
| **PDF** | Executive reports with control summaries, recommendations |
| **JSON** | Structured data for GRC system integration |
| **CSV** | Flat file for audit management systems |
| **Excel** | History export for trend analysis |

### Email Integration

- Configure SMTP settings within the app
- Automatically email PDF reports after each analysis
- Test email functionality
- Customizable recipient lists

### Trend Analysis

- Historical Control Entropy Score tracking
- Visual trend chart on dashboard
- Store unlimited analysis history
- Export history to Excel

---

## Why PayReality?

Most tools:
- Enforce controls
- Reconcile transactions
- Monitor activity

**PayReality verifies whether the control itself is trustworthy.**

It acts as an independent validation layer within the audit process.

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Clone Repository

```bash
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality
