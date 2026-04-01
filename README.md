# PayReality

**Independent Control Validation for Internal Audit**

PayReality is a professional desktop application that helps internal audit teams verify that all payments are made to approved vendors. It uses a powerful **7‑pass semantic matching engine** to catch typos, abbreviations, phonetic variations, and intentional obfuscation that ERPs miss.

---

## Features

| Feature | Description |
|---------|-------------|
| **7‑pass semantic matching** | Exact → Normalized → Token Sort → Partial → Levenshtein → Phonetic → Obfuscation |
| **Control Entropy Score** | Percentage of total spend that bypassed approved vendor controls |
| **Risk scoring** | High / Medium / Low based on spend, tenure, duplicates, weekend payments |
| **Tenure tracking** | First seen, last seen, payment count, active days |
| **Vendor Master Health Score** | Completeness, duplicate rate, dormancy, orphan rate, format quality |
| **PDF reports** | Professional, audit‑ready reports with executive summary, risk summary, recommendations |
| **Email reports** | Automatic delivery of reports to configured recipients |
| **History tracking** | SQLite database stores all analyses with trend chart |
| **File parser** | Handles CSV, Excel, PDF, and Sage formats with auto‑column detection |
| **Cross‑platform** | Works on Windows, macOS, Linux |
| **Privacy‑first** | Data never leaves your machine – runs entirely offline |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ghee9ine/Payreality.git
   cd Payreality
Create a virtual environment

bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
Install dependencies

bash
pip install -r requirements.txt
Run the application

bash
python payreality_app.py
Usage
Step	Action
1	Select Vendor Master file (CSV/Excel)
2	Select Payments file (CSV/Excel/PDF)
3	Click Run Analysis
4	View results on Dashboard
5	PDF report saved to Desktop/PayReality_Reports/
File Requirements
File Type	Required Columns
Vendor Master	vendor_name (or similar)
Payments	payee_name and amount (or similar)
Supported formats: CSV, Excel (.xlsx, .xls), PDF, Sage CSV.

Configuration
You can adjust matching thresholds in payreality_config.json after the first run:

json
"thresholds": {
    "exact": 100,
    "normalized": 100,
    "token_sort": 80,
    "partial": 80,
    "levenshtein": 75,
    "phonetic": 80,
    "obfuscation": 80
}
Troubleshooting
Problem	Solution
Missing required columns	Rename your columns to payee_name and amount. Check the sample files in data/sample/.
File not found	Use the Browse buttons instead of typing paths.
Empty file	Ensure your file has at least one row of data.
PDF extraction fails	Ensure the PDF contains text (not just scanned images). OCR is supported but requires Tesseract.
Project Structure
text
Payreality/
├── src/
│   ├── core.py          # 7‑pass matching engine, risk scoring, health analysis
│   ├── parser.py        # CSV, Excel, PDF, Sage parser
│   ├── reporting.py     # PDF report generator
│   └── config.py        # Configuration management
├── data/
│   ├── sample/          # Sample files for testing
│   └── test_data/       # Large test datasets (generated)
├── logs/                # Application logs
├── payreality_app.py    # Main desktop application
├── generate_test_data.py
├── requirements.txt
├── README.md
└── .gitignore
License
Proprietary – AI Securewatch

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

For licensing inquiries, contact: sean@aisecurewatch.com

Contact
AI Securewatch
Email: sean@aisecurewatch.com
GitHub: https://github.com/Ghee9ine/Payreality

“Your ERP monitors what it recognises. PayReality monitors what it ignores.”