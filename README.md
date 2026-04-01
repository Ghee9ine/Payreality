# PayReality  
### Independent Control Validation for Internal Audit

PayReality is a forensic desktop application that verifies whether payments processed by an ERP system actually went to approved vendors.

Traditional ERP controls rely on exact or near-exact matching. PayReality applies a multi-layered semantic approach to uncover discrepancies caused by typos, aliases, phonetic variations, or deliberate obfuscation.

> **Did the money go where the system says it did?**

---

## Overview

Internal audit teams rely on ERP controls to enforce vendor integrity. However, these controls are **syntactic** — they validate format, not meaning.

PayReality introduces an independent validation layer that tests whether those controls actually work in practice.

- Analyzes 100% of transactions  
- Requires no integrations  
- Runs entirely offline  

---

## Core Capabilities

### Semantic Control Engine (7-Pass Matching)

Detects hidden mismatches using layered analysis:

- Exact  
- Normalized  
- Token Sort  
- Partial  
- Levenshtein  
- Phonetic  
- Obfuscation  

Identifies cases where payments appear valid but are not truly linked to approved vendors.

---

### Control Entropy Score

Measures the percentage of total spend that bypassed approved vendor controls.

Provides a direct indicator of control effectiveness, not just isolated failures.

---

### Risk Scoring

Automatically classifies findings based on:

- Spend magnitude  
- Vendor tenure  
- Duplicate patterns  
- Weekend or off-cycle payments  

Outputs:
- High Risk  
- Medium Risk  
- Low Risk  

---

### Tenure Tracking

Tracks vendor lifecycle behavior:

- First seen  
- Last seen  
- Number of payments  
- Active duration  

---

### Vendor Master Health Score

Evaluates structural quality of the vendor master:

- Duplicate rate  
- Dormancy  
- Orphan records  
- Data completeness  
- Format consistency  

---

### Audit-Ready Reporting

Generates professional PDF reports including:

- Executive summary  
- Risk overview  
- Detailed exceptions  
- Actionable recommendations  

Supports automatic email delivery via SMTP.

---

### History and Trend Analysis

- Stores analyses in a local SQLite database  
- Tracks trends over time  
- Exportable to Excel  

---

### Privacy-First Architecture

- Fully offline  
- No data leaves your machine  
- No external integrations  

---

## Why PayReality

Most tools:
- Enforce controls  
- Reconcile transactions  
- Monitor activity  

**PayReality verifies whether the control itself is trustworthy.**

It acts as an independent validation layer within the audit process.

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

---

### Installation

```bash
git clone https://github.com/Ghee9ine/Payreality.git
cd Payreality

python -m venv venv

Activate virtual environment:

macOS/Linux

source venv/bin/activate

Windows

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt
Run the Application
python payreality_app.py
Usage
1. Select Input Files

Vendor Master

CSV or Excel
Must contain a vendor name column
(e.g., vendor_name, supplier, name)

Payments

CSV, Excel, or PDF
Must contain:
payee_name
amount
2. Run Analysis
Click Run Analysis
Enter a client name
Monitor progress via the status bar
3. Review Results

Dashboard

KPI cards
Exception list
Trend chart

History

Past analyses
Export to Excel

Reports

Generated PDFs
Open within the app

Email

Configure SMTP for automatic delivery

Reports are saved to:

Desktop/PayReality_Reports/
File Requirements
File Type	Required Columns
Vendor Master	vendor_name (or similar)
Payments	payee_name, amount

Supported formats:

CSV
Excel (.xlsx, .xls)
PDF
Sage CSV
Configuration

After first run, edit:

payreality_config.json

Example:

{
  "thresholds": {
    "exact": 100,
    "normalized": 100,
    "token_sort": 80,
    "partial": 80,
    "levenshtein": 75,
    "phonetic": 80,
    "obfuscation": 80
  }
}
Troubleshooting
Problem	Solution
Missing columns	Rename to payee_name and amount
File not found	Use file browser
Empty file	Ensure at least one row
PDF extraction fails	Ensure PDF contains selectable text (OCR requires Tesseract)
Project Structure
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
License

Proprietary – AI Securewatch

Contact

AI Securewatch
Email: sean@aisecurewatch.com

GitHub: https://github.com/Ghee9ine/Payreality

Final Note

PayReality is designed to be run as part of every audit cycle.

If vendor controls have not been independently validated, their effectiveness cannot be assumed.