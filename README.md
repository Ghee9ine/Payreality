# PayReality — Independent Control Verification Platform

**Phase 2 | Enterprise-Grade Payment Control Validation**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

PayReality is an **independent control verification platform** that automatically detects unapproved vendors, duplicate payments, obfuscation attempts, and control failures using a proprietary **7-pass semantic matching engine**.

> *"If vendor controls have not been independently verified, their effectiveness cannot be assumed."*

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Control Taxonomy](#control-taxonomy)
- [7-Pass Matching Engine](#7-pass-matching-engine)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Output & Reports](#output--reports)
- [Configuration](#configuration)
- [API & Integration](#api--integration)
- [System Requirements](#system-requirements)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

PayReality solves a critical problem: **organizations cannot verify that every payment goes to an approved vendor** without manually reviewing thousands of transactions. Traditional vendor matching fails because:

- Vendor names appear differently across systems (typos, abbreviations, word order)
- Fraudsters deliberately obfuscate names (leetspeak, dot-spacing, homoglyphs)
- Duplicate/split payments bypass simple controls
- New vendors with high spend represent elevated risk

PayReality addresses all these challenges through **deterministic, explainable matching** with full audit trail.

---

## Key Features

### 🔍 7-Pass Semantic Matching Engine
| Pass | Strategy | Detection Capability |
|------|----------|---------------------|
| 1 | Exact Match | Perfect character-for-character |
| 2 | Normalized | Case, punctuation, suffix removal |
| 3 | Token Sort | Word order variations |
| 4 | Partial | Extra words (e.g., department names) |
| 5 | Levenshtein | Typos, transpositions, OCR errors |
| 6 | Phonetic | Sound-alike names (Smith/Smyth) |
| 7 | Obfuscation | Leetspeak, dot-spacing, homoglyphs, repetition |

### ⚖️ Control Taxonomy
| ID | Control Name | Severity |
|----|--------------|----------|
| AVC | Approved Vendor Control | Critical |
| OBC | Obfuscation Detection Control | Critical |
| VDC | Vendor Duplication Control | High |
| VNC | Vendor Name Consistency Control | High |
| VTC | Vendor Tenure Control | High |
| PAC | Payment Authorization Control | Medium |
| VMH | Vendor Master Health Control | Medium |

### 📊 Confidence & Risk Scoring
- **Confidence Score (0-100)**: How certain the system is a finding represents a genuine control failure
- **Risk Score (0-100)**: Composite risk based on spend, duplicates, tenure, and off-cycle payments
- **Risk Level**: High / Medium / Low classification for prioritization

### 📄 Professional Reporting
- **PDF Reports**: Executive summaries, control violation tables, exception details with explanations
- **JSON Export**: Structured data for GRC system integration
- **CSV Export**: Flat file for audit management systems

### 🗄️ Audit Trail
- Every analysis run stored with unique Run ID
- File hashing for data integrity verification
- Configuration snapshots for reproducibility
- Full exception history with all metadata

---

## Installation

### Prerequisites

```bash
# Python 3.8 or higher required
python --version
Clone & Install
bash
# Clone the repository
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
Dependencies
text
pandas>=2.0.0
rapidfuzz>=3.0.0
customtkinter>=5.2.0
matplotlib>=3.7.0
reportlab>=4.0.0
openpyxl>=3.0.0
pdfplumber>=0.10.0
PyPDF2>=3.0.0
Quick Start
1. Generate Sample Data (Optional)
bash
python generate_sample_data.py
This creates:

data/sample/vendor_master.csv (95 vendors)

data/sample/payments.csv (20,000+ payment records covering all 7 passes)

2. Run the Application
bash
python payreality_app.py
3. Load Files
File Type	Required Column	Optional Columns
Vendor Master	vendor_name	tax_id, bank_account, address, email
Payments	payee_name, amount	payment_date
Column names are auto-detected (case-insensitive).

4. Run Analysis
Click "Browse Vendor Master" and select your file

Click "Browse Payments File" and select your file

Adjust Match Threshold (default: 80%)

Click "Run Analysis"

Enter client name when prompted

5. Review Results
Dashboard: KPI cards, entropy trend chart

Exceptions: Filterable, sortable table with confidence scores

History: Complete audit trail of all analyses

Reports: Access generated PDF/JSON/CSV files

Usage Guide
Understanding the Dashboard
KPI	Description
Exceptions	Number of payments not matched to approved vendors
Exception Spend	Total value of exception payments
Control Entropy	% of total spend that bypassed controls
Total Payments	Total payments analyzed
Avg Confidence	Average confidence score across exceptions
Interpreting Control Entropy
Score	Interpretation	Action
< 10%	Acceptable	Monthly monitoring
10-20%	Warning	Investigate high-risk exceptions
> 20%	Critical	Immediate escalation required
Exception Detail View
Click any exception row to see:

Control violations with severity

Confidence score breakdown

Matching pass that triggered the flag

Human-readable explanation

Vendor tenure and payment history

Risk factors

Exporting Results
Format	Use Case
PDF	Executive reporting, audit presentations
JSON	GRC system integration, API consumption
CSV	Excel analysis, audit management systems
Excel History	Trend analysis across multiple runs
Output & Reports
PDF Report Structure
Cover Page - Client name, date, run ID

KPI Summary - Key metrics at a glance

Control Entropy Analysis - Interpretation and scoring

7-Pass Distribution - How each payment was classified

Vendor Master Health - Data quality assessment

Exception Detail - Each exception with full explanation

Control Violation Summary - Counts by control type

Recommendations - Actionable next steps

Sample Output Location
text
Desktop\PayReality_Reports\
├── PayReality_ClientName_20241201_143022.pdf
├── PayReality_ClientName_20241201_143022.json
└── PayReality_ClientName_20241201_143022.csv
Configuration
Settings Tab
Setting	Description	Default
Match Threshold	Minimum similarity score (50-95%)	80%
Phonetic Matching	Enable/disable Pass 6	Enabled
Obfuscation Detection	Enable/disable Pass 7	Enabled
Output Directory	Where reports are saved	Desktop\PayReality_Reports
Email Configuration
Field	Description
SMTP Server	e.g., smtp.gmail.com, smtp.office365.com
Port	587 (TLS) or 465 (SSL)
Email Address	Sender email
Password	App password (not regular password)
Recipients	Comma-separated email addresses
Reports are automatically emailed after each analysis run when enabled.

API & Integration
JSON Export Schema
json
{
  "meta": {
    "run_id": "A3F9C2E1",
    "timestamp": "2024-12-01T14:30:22",
    "client": "Client Name",
    "threshold": 80
  },
  "summary": {
    "total_payments": 20000,
    "total_spend": 501358135.06,
    "exception_count": 4992,
    "exception_spend": 94608581.30,
    "entropy_score": 18.87
  },
  "exceptions": [
    {
      "payee_name": "Shell Company Holdings",
      "amount": 1200000.00,
      "control_ids": ["AVC", "VTC"],
      "confidence_score": 92,
      "risk_level": "High",
      "match_strategy": "none",
      "explanation": "Vendor is not on approved vendor list..."
    }
  ]
}
Programmatic Usage
python
from core import PayRealityEngine

engine = PayRealityEngine()
results = engine.run_analysis(
    master_file="vendor_master.csv",
    payments_file="payments.csv",
    threshold=80,
    client_name="Audit Q4 2024"
)

# Access results
print(f"Exceptions: {results['exception_count']}")
print(f"Entropy Score: {results['entropy_score']:.1f}%")

# Export
engine.export_json(results, "findings.json")
engine.export_csv(results, "findings.csv")
System Requirements
Component	Minimum	Recommended
CPU	2 cores	4+ cores
RAM	4 GB	8 GB
Storage	500 MB free	1 GB free
Python	3.8	3.11+
OS	Windows 10 / Ubuntu 20.04 / macOS 11	Latest version
Performance Benchmarks
Payment Volume	Processing Time	Memory Usage
10,000	~15 seconds	~300 MB
50,000	~60 seconds	~600 MB
100,000	~120 seconds	~1 GB
Troubleshooting
Common Issues & Solutions
Issue	Solution
"No module named 'core'"	Run from the correct directory: cd payreality_v2
Import errors	Ensure all dependencies installed: pip install -r requirements.txt
Database errors	Delete %USERPROFILE%\PayReality_Data\payreality.db and restart
PDF generation fails	Install reportlab: pip install --upgrade reportlab
CustomTkinter not found	pip install customtkinter
Matplotlib backend error	Set backend: add matplotlib.use('Agg') before importing pyplot
Diagnostic Commands
bash
# Check Python version
python --version

# List installed packages
pip list

# Test imports
python -c "from core import PayRealityEngine; print('OK')"

# Run with debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from core import PayRealityEngine"
Getting Help
Email: sean@aisecurewatch.com

GitHub Issues: Create an issue

Documentation: payreality.aisecurewatch.com

File Structure
text
Payreality/
├── payreality_app.py          # Main GUI application
├── core.py                    # Matching engine, control mapping, confidence scoring
├── reporting.py               # PDF, JSON, CSV report generation
├── generate_sample_data.py    # Test data generator
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── data/
│   └── sample/
│       ├── vendor_master.csv  # Sample approved vendors
│       └── payments.csv        # Sample payment transactions
├── logs/                      # Application logs
└── PayReality_Data/           # Database and user data (created automatically)
    └── payreality.db          # SQLite audit database
License
MIT License - see LICENSE file for details.

Contact
AI Securewatch
sean@aisecurewatch.com

Version History
Version	Date	Features
Phase 2	2024-12	Control taxonomy, explainability, confidence scoring, audit trail, JSON/CSV exports
Phase 1	2024-10	7-pass matching, PDF reports, basic UI
Acknowledgments
Built with:

CustomTkinter - Modern UI framework

RapidFuzz - High-performance fuzzy matching

ReportLab - PDF generation

Matplotlib - Trend visualization

"Controls must be independently verified."

text

This README is ready for your GitHub repository. It's professional, detailed, and will help potential users and customers understand the value of PayReality.