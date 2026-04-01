Let's update your README to reflect the final product and make it clear, professional, and helpful for anyone who clones the repository.

Here's the updated `README.md`:


# PayReality

**Independent Control Validation for Internal Audit**

PayReality is a professional desktop application that helps internal audit teams verify that all payments are made to approved vendors. It uses a powerful **7-pass semantic matching engine** to catch typos, abbreviations, phonetic variations, and intentional obfuscation that ERPs miss.

---

## Features

| Feature | Description |
|---------|-------------|
| **7‑pass semantic matching** | Exact → Normalized → Token Sort → Partial → Levenshtein → Phonetic → Obfuscation |
| **Control Entropy Score** | Percentage of total spend that bypassed approved vendor controls |
| **Risk scoring** | High/Medium/Low based on spend, tenure, duplicates, weekend payments |
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
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python payreality_app.py
   ```

---

## Usage

### 1. Select Your Files

- **Vendor Master** – a CSV or Excel file containing your approved vendor list.  
  Must have a column with vendor names (e.g., `vendor_name`, `supplier`, `name`).

- **Payments** – a CSV, Excel, or PDF file containing your payment transactions.  
  Must have payee name and amount columns (e.g., `payee_name`, `amount`, `value`).

### 2. Run Analysis

Click **Run Analysis** and enter a client name. The progress bar will show the status.

### 3. View Results

- **Dashboard** – KPI cards, exceptions list, trend chart.
- **History** – Table of all past analyses. Export to Excel.
- **Reports** – List of generated PDF reports. Click **Open** to view.
- **Email** – Configure SMTP settings to receive reports automatically.

The PDF report is also saved to `Desktop/PayReality_Reports/`.

---

## File Requirements

| File Type | Required Columns |
|-----------|------------------|
| Vendor Master | `vendor_name` (or similar) |
| Payments | `payee_name` and `amount` (or similar) |

Supported formats: CSV, Excel (.xlsx, .xls), PDF, Sage CSV.

---

## Configuration

You can adjust matching thresholds in `payreality_config.json` after the first run:

```json
"thresholds": {
    "exact": 100,
    "normalized": 100,
    "token_sort": 80,
    "partial": 80,
    "levenshtein": 75,
    "phonetic": 80,
    "obfuscation": 80
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Missing required columns** | Rename your columns to `payee_name` and `amount`. Check the sample files in `data/sample/`. |
| **File not found** | Use the **Browse** buttons instead of typing paths. |
| **Empty file** | Ensure your file has at least one row of data. |
| **PDF extraction fails** | Ensure the PDF contains text (not just scanned images). OCR is supported but requires Tesseract. |

---

## Project Structure

```
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
```

---

## License

Proprietary – AI Securewatch

---

## Contact

**AI Securewatch**  
Email: sean@aisecurewatch.com  
GitHub: [https://github.com/Ghee9ine/Payreality](https://github.com/Ghee9ine/Payreality)

---

*“Your ERP monitors what it recognises. PayReality monitors what it ignores.”