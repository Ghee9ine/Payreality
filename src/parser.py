"""
PayReality File Parser Module
Bulletproof universal parser for CSV, Excel, PDF, and Sage formats

Fixes applied:
- _standardize_columns: numeric column guesser now skips columns whose name suggests
  an ID/reference/number, and checks that sampled values are in a plausible monetary
  range (> 0, not suspiciously sequential) before accepting them as 'amount'.
"""

import pandas as pd
import os
import logging
import re
import PyPDF2
import pdfplumber
from typing import Dict, List, Tuple, Optional, Any
import chardet
import csv


# Column names that suggest an identifier rather than a monetary amount
_ID_LIKE_KEYWORDS = {
    'id', 'ref', 'reference', 'number', 'num', 'no', 'code',
    'index', 'seq', 'sequence', 'key', 'pk', 'row'
}


class FileParser:
    def __init__(self):
        self.logger = logging.getLogger('PayReality')

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse_file(self, filepath: str, file_type: str = None) -> pd.DataFrame:
        """
        Universal file parser – returns DataFrame with standardised columns:
        payee_name, amount, payment_date
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        if os.path.getsize(filepath) == 0:
            raise ValueError(f"File is empty: {filepath}")

        if file_type is None:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.csv':
                file_type = 'csv'
            elif ext in ['.xlsx', '.xls']:
                file_type = 'excel'
            elif ext == '.pdf':
                file_type = 'pdf'
            else:
                raise ValueError(f"Unsupported file type: {ext}")

        self.logger.info(f"Parsing {file_type} file: {filepath}")

        try:
            if file_type == 'csv':
                df = self._parse_csv(filepath)
            elif file_type == 'excel':
                df = self._parse_excel(filepath)
            elif file_type == 'pdf':
                df = self._parse_pdf(filepath)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            self.logger.error(f"Failed to parse file: {e}")
            raise ValueError(f"Could not parse file: {e}")

        if df is None or len(df) == 0:
            raise ValueError("File contains no data rows")

        df = self._standardize_columns(df)

        if len(df) == 0:
            raise ValueError("No valid payment records found after processing")

        self.logger.info(f"Successfully parsed {len(df)} payment records")
        return df

    # ------------------------------------------------------------------
    # Format-specific parsers
    # ------------------------------------------------------------------

    def _parse_csv(self, filepath: str) -> pd.DataFrame:
        """Parse CSV with automatic encoding and delimiter detection"""
        encoding = self._detect_encoding(filepath)
        self.logger.info(f"Detected encoding: {encoding}")

        for delimiter in [',', ';', '\t', '|']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    sample = f.read(10000)
                    sniffer = csv.Sniffer()
                    try:
                        dialect = sniffer.sniff(sample)
                        delimiter = dialect.delimiter
                        self.logger.info(f"Detected delimiter: '{delimiter}'")
                    except Exception:
                        pass

                df = pd.read_csv(
                    filepath, encoding=encoding,
                    delimiter=delimiter, on_bad_lines='skip', engine='python'
                )
                if len(df) > 0:
                    self.logger.info(f"Parsed CSV with delimiter '{delimiter}'")
                    return df
            except Exception as e:
                self.logger.debug(f"Failed with delimiter '{delimiter}': {e}")
                continue

        try:
            df = pd.read_csv(filepath, encoding=encoding, engine='python')
            if len(df) > 0:
                return df
        except Exception:
            pass

        raise ValueError("Could not parse CSV file — tried all delimiters and encodings")

    def _detect_encoding(self, filepath: str) -> str:
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                return result.get('encoding') or 'utf-8'
        except Exception:
            return 'utf-8'

    def _parse_excel(self, filepath: str) -> pd.DataFrame:
        try:
            excel_file = pd.ExcelFile(filepath, engine='openpyxl')

            best_sheet = None
            max_rows = 0
            for sheet in excel_file.sheet_names:
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet, nrows=100)
                    if len(df) > max_rows:
                        max_rows = len(df)
                        best_sheet = sheet
                except Exception:
                    continue

            if best_sheet:
                df = pd.read_excel(filepath, sheet_name=best_sheet)
                self.logger.info(f"Using sheet: {best_sheet} with {len(df)} rows")
                return df

            return pd.read_excel(filepath, sheet_name=0)

        except Exception as e:
            self.logger.error(f"Excel parsing error: {e}")
            raise ValueError(f"Could not parse Excel file: {e}")

    def _parse_pdf(self, filepath: str) -> pd.DataFrame:
        payments = []

        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        payments.extend(self._extract_payments_from_text(text))
            if payments:
                self.logger.info(f"Extracted {len(payments)} payments using pdfplumber")
                return pd.DataFrame(payments)
        except Exception as e:
            self.logger.debug(f"pdfplumber failed: {e}")

        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        payments.extend(self._extract_payments_from_text(text))
            if payments:
                self.logger.info(f"Extracted {len(payments)} payments using PyPDF2")
                return pd.DataFrame(payments)
        except Exception as e:
            self.logger.debug(f"PyPDF2 failed: {e}")

        if not payments:
            raise ValueError("Could not extract any payment data from PDF")

        return pd.DataFrame(payments)

    def _extract_payments_from_text(self, text: str) -> List[Dict]:
        payments = []
        patterns = [
            r'([A-Z][A-Za-z\s\.]{2,50})\s+([\d,]+\.?\d{2})\s*$',
            r'([\d,]+\.?\d{2})\s+([A-Z][A-Za-z\s\.]{2,50})\s*$',
            r'(?:Vendor|Payee|Supplier|Name)[:\s]+([A-Z][A-Za-z\s\.]+)\s+(?:Amount|Total|Value)[:\s]+([\d,]+\.?\d{2})',
            r'([A-Z][A-Za-z\s\.]{2,50}).*?([\d,]+\.?\d{2})\s*$',
        ]

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        if self._is_amount(groups[0]):
                            amount = self._to_float(groups[0])
                            vendor = groups[1].strip()
                        elif self._is_amount(groups[1]):
                            amount = self._to_float(groups[1])
                            vendor = groups[0].strip()
                        else:
                            vendor = groups[0].strip()
                            amount = self._to_float(groups[1])

                        if vendor and amount > 0 and len(vendor) > 2:
                            payments.append({
                                'payee_name': vendor[:100],
                                'amount': amount
                            })
                            break

        return payments

    def _is_amount(self, text: str) -> bool:
        cleaned = re.sub(r'[^\d.-]', '', str(text))
        return bool(cleaned) and cleaned.replace('.', '').replace('-', '').isdigit()

    def _to_float(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.-]', '', value.replace(' ', '').replace(',', ''))
            try:
                return float(cleaned)
            except Exception:
                return 0.0
        return 0.0

    # ------------------------------------------------------------------
    # Column standardisation  (FIXED: smarter amount-column guesser)
    # ------------------------------------------------------------------

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map raw columns to payee_name, amount, payment_date."""

        vendor_aliases = [
            'payee_name', 'payee', 'vendor_name', 'vendor', 'supplier',
            'supplier_name', 'name', 'creditor', 'customer', 'pay to',
            'recipient', 'beneficiary', 'account name', 'description',
            'party', 'payable', 'payable_to'
        ]
        amount_aliases = [
            'amount', 'value', 'total', 'price', 'cost', 'debit', 'credit',
            'payment', 'transaction', 'net', 'gross', 'invoice', 'excl',
            'incl', 'vat', 'balance', 'due', 'paid', 'charge'
        ]
        date_aliases = [
            'date', 'transaction_date', 'payment_date', 'invoice_date',
            'posting_date', 'value_date', 'created', 'due_date',
            'entry_date', 'date_posted'
        ]

        vendor_col = amount_col = date_col = None

        # Exact match first
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in vendor_aliases and vendor_col is None:
                vendor_col = col
            elif col_lower in amount_aliases and amount_col is None:
                amount_col = col
            elif col_lower in date_aliases and date_col is None:
                date_col = col

        # Partial match fallback
        if not vendor_col:
            for col in df.columns:
                col_lower = col.lower().strip()
                if any(alias in col_lower for alias in vendor_aliases):
                    vendor_col = col
                    break

        if not amount_col:
            for col in df.columns:
                col_lower = col.lower().strip()
                if any(alias in col_lower for alias in amount_aliases):
                    amount_col = col
                    break

        if not date_col:
            for col in df.columns:
                col_lower = col.lower().strip()
                if any(alias in col_lower for alias in date_aliases):
                    date_col = col
                    break

        # Heuristic fallback for vendor column
        if not vendor_col:
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    continue
                sample = df[col].dropna().head(20).astype(str)
                if len(sample) > 0 and sample.str.len().mean() > 2 and not sample.str.isdigit().all():
                    vendor_col = col
                    break

        # FIXED: heuristic fallback for amount column — skip ID-like columns
        if not amount_col:
            for col in df.columns:
                col_lower = col.lower().strip()

                # Skip columns that look like identifiers
                if any(kw in col_lower for kw in _ID_LIKE_KEYWORDS):
                    self.logger.debug(f"Skipping ID-like column for amount: '{col}'")
                    continue

                # Try numeric columns first
                if df[col].dtype in ['int64', 'float64']:
                    if self._looks_like_monetary(df[col]):
                        amount_col = col
                        break
                    continue

                # Try coercing string columns
                try:
                    numeric_series = pd.to_numeric(df[col].head(100), errors='raise')
                    if self._looks_like_monetary(numeric_series):
                        amount_col = col
                        break
                except Exception:
                    continue

        # Apply renames
        rename_map = {}
        if vendor_col:
            rename_map[vendor_col] = 'payee_name'
            self.logger.info(f"Mapped '{vendor_col}' -> payee_name")
        else:
            self.logger.warning("Could not find vendor name column")

        if amount_col:
            rename_map[amount_col] = 'amount'
            self.logger.info(f"Mapped '{amount_col}' -> amount")
        else:
            self.logger.warning("Could not find amount column")

        if date_col:
            rename_map[date_col] = 'payment_date'
            self.logger.info(f"Mapped '{date_col}' -> payment_date")

        if rename_map:
            df = df.rename(columns=rename_map)

        # Convert and clean
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df = df.dropna(subset=['amount'])

        if 'payee_name' in df.columns:
            df['payee_name'] = df['payee_name'].astype(str).str.strip()
            df['payee_name'] = df['payee_name'].replace('', pd.NA)
            df = df.dropna(subset=['payee_name'])

        if 'payee_name' not in df.columns or 'amount' not in df.columns:
            raise ValueError(
                f"Could not find required columns.\n"
                f"Available columns: {list(df.columns)}\n"
                f"Required: payee_name (vendor name) and amount.\n"
                f"Please rename your columns to 'payee_name' and 'amount'."
            )

        df = df[df['amount'] > 0]
        return df

    @staticmethod
    def _looks_like_monetary(series: pd.Series) -> bool:
        """
        Return True if a numeric series looks like monetary values rather than
        sequential IDs or row numbers.

        Heuristics:
        - Values must be positive
        - Values should not be a near-perfect arithmetic sequence (e.g. 1, 2, 3 …)
        - Median value > 1  (IDs are often small integers)
        - Standard deviation meaningful relative to mean (coefficient of variation)
        """
        s = pd.to_numeric(series, errors='coerce').dropna()
        if len(s) < 2:
            return False

        # Must have at least some positive values
        if (s <= 0).all():
            return False

        median = s.median()
        if median < 1:
            return False

        # Reject near-perfect sequential series (sequential IDs)
        diffs = s.diff().dropna()
        if len(diffs) > 0:
            unique_diffs = diffs.nunique()
            if unique_diffs == 1:
                # Perfectly sequential — almost certainly an ID column
                return False

        # Coefficient of variation: IDs have low CV relative to their range
        mean = s.mean()
        std = s.std()
        if mean > 0:
            cv = std / mean
            # Very low CV with small values suggests sequential IDs
            if cv < 0.1 and median < 1000:
                return False

        return True