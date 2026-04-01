"""
PayReality Core Module
7-Pass Semantic Matching Engine with Vendor Master Health Scoring

Enhancements:
- Configurable per‑pass thresholds (from config)
- Enhanced obfuscation detection (homoglyphs, leetspeak, character repetition)
- Soundex phonetic matching with pre‑computed lookup (O(1) per payment)
- Batch processing (cdist) for fuzzy passes to speed up large datasets (optional)
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from rapidfuzz import fuzz, process
import re
import hashlib
from collections import defaultdict
import numpy as np
from src.parser import FileParser


class DataValidationError(Exception):
    pass


class PayRealityEngine:
    def __init__(self, log_level=logging.INFO, config: Dict = None):
        self.config = config or {}
        self.setup_logging(log_level)
        self.master_df = None
        self.payments_df = None
        self.results = []
        self.exceptions = []
        self.match_stats = {}
        self.hash_cache = {}
        self._cleaned_vendors_cache = {}
        self._vendor_list_cache = []
        self._soundex_cache = {}          # vendor -> soundex key
        self._soundex_to_vendors = {}     # soundex -> list of vendors
        self._phonetic_keys = []          # list of soundex keys for batch matching

        # Load matching thresholds from config
        self.thresholds = self.config.get('matching', {}).get('thresholds', {
            'exact': 100,
            'normalized': 100,
            'token_sort': 80,
            'partial': 80,
            'levenshtein': 75,
            'phonetic': 80,
            'obfuscation': 80
        })
        self.use_batch_matching = self.config.get('matching', {}).get('use_batch_matching', True)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def setup_logging(self, log_level):
        self.logger = logging.getLogger('PayReality')
        self.logger.setLevel(log_level)

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"payreality_{datetime.now().strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file, mode='a')
        fh.setLevel(log_level)
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.handlers.clear()
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        self.logger.info("PayReality engine initialized with 7-pass semantic matching")

    # ------------------------------------------------------------------
    # File loading & validation
    # ------------------------------------------------------------------

    def validate_file(self, filepath: str, expected_columns: List[str], file_type: str) -> pd.DataFrame:
        if not os.path.exists(filepath):
            raise DataValidationError(f"{file_type} file not found: {filepath}")

        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise DataValidationError(f"{file_type} file is empty: {filepath}")

        self.logger.info(f"File size: {file_size:,} bytes")

        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None

        for encoding in encodings:
            try:
                if filepath.lower().endswith('.csv'):
                    df = pd.read_csv(filepath, encoding=encoding)
                elif filepath.lower().endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(filepath)
                else:
                    raise DataValidationError(f"Unsupported file format: {filepath}")
                self.logger.info(f"Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.logger.warning(f"Failed with {encoding}: {str(e)[:100]}")
                continue

        if df is None:
            raise DataValidationError(f"Could not read {file_type} file with any encoding")

        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise DataValidationError(
                f"Missing required columns in {file_type}: {missing_columns}\n"
                f"Found columns: {list(df.columns)}"
            )

        if len(df) == 0:
            raise DataValidationError(f"{file_type} file has no data rows")

        self.logger.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")

        null_counts = df[expected_columns].isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                percentage = (null_count / len(df)) * 100
                self.logger.warning(
                    f"Column '{col}' has {null_count:,} null values ({percentage:.1f}%)"
                )

        return df

    def load_files(
        self,
        master_file: str,
        payments_file: str,
        payments_format: str = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.logger.info("=" * 60)
        self.logger.info("Loading and validating input files")
        self.logger.info("=" * 60)

        parser = FileParser()

        self.master_df = self.validate_file(master_file, ['vendor_name'], 'Vendor Master')

        # Clear all caches for each run
        self._invalidate_caches()

        try:
            self.payments_df = parser.parse_file(payments_file, payments_format)
            self.logger.info(f"Parsed {len(self.payments_df)} payment records")
        except Exception as e:
            raise DataValidationError(f"Failed to parse payments file: {str(e)}")

        required_cols = ['payee_name', 'amount']
        missing = [col for col in required_cols if col not in self.payments_df.columns]

        if missing:
            self.logger.warning(f"Missing columns: {missing}")
            self.payments_df = self._map_columns(self.payments_df)
            missing = [col for col in required_cols if col not in self.payments_df.columns]
            if missing:
                raise DataValidationError(
                    f"Payments file missing required columns: {missing}\n"
                    f"Found columns: {list(self.payments_df.columns)}"
                )

        negative_amounts = self.payments_df[self.payments_df['amount'] < 0]
        if len(negative_amounts) > 0:
            self.logger.warning(f"Found {len(negative_amounts):,} payments with negative amounts")

        return self.master_df, self.payments_df

    def _invalidate_caches(self):
        """Clear all vendor-related caches."""
        self._cleaned_vendors_cache = {}
        self._vendor_list_cache = []
        self._soundex_cache = {}
        self._soundex_to_vendors = {}
        self._phonetic_keys = []

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        column_mapping = {}

        name_keywords = ['vendor', 'payee', 'supplier', 'name', 'pay_to', 'recipient']
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in name_keywords):
                column_mapping[col] = 'payee_name'
                break

        amount_keywords = ['amount', 'value', 'total', 'price', 'cost', 'invoice_amount']
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in amount_keywords):
                column_mapping[col] = 'amount'
                break

        if column_mapping:
            df = df.rename(columns=column_mapping)
            self.logger.info(f"Mapped columns: {column_mapping}")

        return df

    # ------------------------------------------------------------------
    # Name cleaning
    # ------------------------------------------------------------------

    def clean_name(self, name: str, config: Dict = None) -> str:
        if pd.isna(name):
            return ""

        rules = {
            'lowercase': True,
            'remove_punctuation': True,
            'remove_extra_spaces': True,
            'strip_suffixes': True,
            'suffixes': [
                ' ltd', ' inc', ' corp', ' llc', ' pty', ' technologies',
                ' solutions', ' group', ' holdings', ' international',
                ' systems', ' pty ltd', ' cc', ' limited', ' corporation',
                ' incorporated', ' company', ' co'
            ]
        }

        if config:
            rules.update(config)

        name = str(name)

        if rules.get('lowercase'):
            name = name.lower()

        if rules.get('remove_punctuation'):
            name = re.sub(r'[^\w\s]', ' ', name)

        if rules.get('strip_suffixes'):
            for suffix in rules['suffixes']:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break

        if rules.get('remove_extra_spaces'):
            name = ' '.join(name.split())

        return name.strip()

    # ------------------------------------------------------------------
    # Obfuscation detection (ENHANCED)
    # ------------------------------------------------------------------

    def _normalize_homoglyphs(self, text: str) -> str:
        """Replace common homoglyphs with their Latin equivalents."""
        homoglyphs = {
            'а': 'a', 'е': 'e', 'і': 'i', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'ѕ': 's',
            'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I',
            'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
            'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z'
        }
        for bad, good in homoglyphs.items():
            text = text.replace(bad, good)
        return text

    def detect_obfuscation(self, payee: str) -> Tuple[bool, str, str]:
        original = payee

        # 1. Dot obfuscation
        patterns = [
            (r'[mM]\.?[iI]\.?[cC]\.?[rR]\.?[oO]\.?[sS]\.?[oO]\.?[fF]\.?[tT]', 'microsoft'),
            (r'[gG]\.?[oO]\.?[oO]\.?[gG]\.?[lL]\.?[eE]', 'google'),
            (r'[aA]\.?[mM]\.?[aA]\.?[zZ]\.?[oO]\.?[nN]', 'amazon'),
            (r'[dD]\.?[eE]\.?[lL]\.?[lL]', 'dell'),
            (r'[iI]\.?[bB]\.?[mM]', 'ibm'),
        ]
        for pattern, replacement in patterns:
            if re.search(pattern, original, re.IGNORECASE):
                cleaned = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                return True, cleaned, "dot_obfuscation"

        # 2. Leetspeak (enhanced)
        leet_map = {
            '3': 'e', '0': 'o', '1': 'i', '4': 'a', '5': 's', '7': 't',
            '2': 'z', '6': 'g', '8': 'b', '9': 'g', '@': 'a', '$': 's',
            '+': 't', '|': 'i', '!': 'i', '()': 'o'
        }
        leet_detected = False
        cleaned = original
        for leet, letter in leet_map.items():
            if leet in cleaned:
                cleaned = cleaned.replace(leet, letter)
                leet_detected = True
        if leet_detected:
            return True, cleaned, "leetspeak"

        # 3. Character repetition (e.g., Miiiicrosooooft)
        if re.search(r'(.)\1{2,}', original):
            cleaned = re.sub(r'(.)\1{2,}', r'\1\1', original)
            return True, cleaned, "character_repetition"

        # 4. Homoglyphs (e.g., using Cyrillic letters)
        normalized = self._normalize_homoglyphs(original)
        if normalized != original:
            return True, normalized, "homoglyphs"

        return False, original, "none"

    # ------------------------------------------------------------------
    # Phonetic matching (Soundex with pre‑computed lookup)
    # ------------------------------------------------------------------

    def _soundex(self, text: str) -> str:
        """Compute Soundex code for a string."""
        text = text.upper()
        # Keep first letter, drop vowels and H, Y, W
        first = text[0] if text else ''
        rest = ''.join(ch for ch in text[1:] if ch not in 'AEIOUYWH')
        # Map consonants to digits
        mapping = {
            'BFPV': '1', 'CGJKQSXZ': '2', 'DT': '3', 'L': '4', 'MN': '5', 'R': '6'
        }
        digits = []
        for ch in rest:
            for key, val in mapping.items():
                if ch in key:
                    digits.append(val)
                    break
        # Remove consecutive duplicates
        result = [first]
        last = None
        for d in digits:
            if d != last:
                result.append(d)
                last = d
        # Pad with zeros to length 4
        result = (result + ['0', '0', '0'])[:4]
        return ''.join(result)

    def _build_phonetic_cache(self, master_vendors: List[str]):
        """Pre‑compute soundex keys for all master vendors."""
        self._soundex_cache = {}
        self._soundex_to_vendors = defaultdict(list)
        for vendor in master_vendors:
            cleaned = self._cleaned_vendors_cache.get(vendor, self.clean_name(vendor))
            code = self._soundex(cleaned)
            self._soundex_cache[vendor] = code
            self._soundex_to_vendors[code].append(vendor)

    # ------------------------------------------------------------------
    # Core matching engine
    # ------------------------------------------------------------------

    def semantic_match_7pass(self, payee: str, master_vendors: List[str]) -> Tuple[Optional[str], int, str]:
        """
        Enhanced 7-pass semantic matching with per‑pass thresholds,
        obfuscation detection, and pre‑computed phonetic lookup.
        """
        # --- Pass 1: Exact match ---
        if payee in master_vendors:
            return payee, 100, "exact"

        payee_clean = self.clean_name(payee)

        # --- Pass 2: Normalized match ---
        for vendor, vendor_clean in self._cleaned_vendors_cache.items():
            if payee_clean == vendor_clean:
                return vendor, 100, "normalized"

        cleaned_list = list(self._cleaned_vendors_cache.values())
        vendor_keys = list(self._cleaned_vendors_cache.keys())

        # --- Pass 3: Token sort ratio ---
        if self.thresholds.get('token_sort', 80) > 0:
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.token_sort_ratio)
            if result and result[1] >= self.thresholds['token_sort']:
                return vendor_keys[result[2]], result[1], "token_sort"

        # --- Pass 4: Partial ratio ---
        if self.thresholds.get('partial', 80) > 0:
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.partial_ratio)
            if result and result[1] >= self.thresholds['partial']:
                return vendor_keys[result[2]], result[1], "partial"

        # --- Pass 5: Levenshtein (QRatio) ---
        if self.thresholds.get('levenshtein', 75) > 0:
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.QRatio)
            if result and result[1] >= self.thresholds['levenshtein']:
                return vendor_keys[result[2]], result[1], "levenshtein"

        # --- Pass 6: Phonetic (Soundex) ---
        if self.thresholds.get('phonetic', 80) > 0:
            payee_soundex = self._soundex(payee_clean)
            if payee_soundex in self._soundex_to_vendors:
                # Return the first vendor with that soundex code (could be multiple)
                matched_vendor = self._soundex_to_vendors[payee_soundex][0]
                return matched_vendor, 85, "phonetic"

        # --- Pass 7: Obfuscation detection ---
        if self.thresholds.get('obfuscation', 80) > 0:
            is_obfuscated, cleaned, obf_type = self.detect_obfuscation(payee)
            if is_obfuscated:
                result = process.extractOne(cleaned, cleaned_list, scorer=fuzz.token_sort_ratio)
                if result and result[1] >= self.thresholds['obfuscation']:
                    return vendor_keys[result[2]], result[1], f"obfuscation_{obf_type}"

        return None, 0, "none"

    # ------------------------------------------------------------------
    # Duplicate vendor detection (repeat payee detector)
    # ------------------------------------------------------------------

    def find_duplicate_vendors(self, payments_df: pd.DataFrame) -> List[Dict]:
        duplicates = []
        vendor_payments = defaultdict(list)

        for idx, row in payments_df.iterrows():
            vendor = self.clean_name(row['payee_name'])
            amount = row['amount']
            vendor_payments[vendor].append({
                'amount': amount,
                'payee': row['payee_name'],
                'index': idx
            })

        for vendor, payments in vendor_payments.items():
            if len(payments) > 1:
                duplicates.append({
                    'vendor': vendor,
                    'display_name': payments[0]['payee'],
                    'count': len(payments),
                    'total': sum(p['amount'] for p in payments),
                    'payments': payments
                })

        return duplicates

    # ------------------------------------------------------------------
    # Vendor master health
    # ------------------------------------------------------------------

    def analyze_vendor_master_health(
        self,
        master_df: pd.DataFrame,
        transactions_df: pd.DataFrame = None
    ) -> Dict:
        """Analyse vendor master for data quality issues."""
        master_df = master_df.copy()   # avoid mutating original

        # 1. Completeness Score
        optional_fields = ['tax_id', 'bank_account', 'address', 'email', 'phone', 'vat_number']
        available_fields = [f for f in optional_fields if f in master_df.columns]

        completeness_scores = []
        for field in available_fields:
            non_null = master_df[field].notna().sum()
            completeness_scores.append(non_null / len(master_df) * 100)

        completeness_score = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores else 0
        )

        # 2. Duplicate Rate
        def normalize(name):
            if pd.isna(name):
                return ""
            name = str(name).lower()
            for suffix in [' ltd', ' inc', ' corp', ' llc', ' pty', ' cc',
                           ' technologies', ' solutions']:
                if name.endswith(suffix):
                    name = name[:-len(suffix)]
            name = re.sub(r'[^\w\s]', '', name)
            return name.strip()

        master_df['normalized'] = master_df['vendor_name'].apply(normalize)
        duplicate_count = master_df['normalized'].duplicated(keep=False).sum()
        duplicate_rate = (duplicate_count / len(master_df) * 100) if len(master_df) > 0 else 0

        # 3. Dormancy and Orphan Rates
        dormancy_rate = 0
        orphan_rate = 0
        active_vendors = set()

        if transactions_df is not None and 'payee_name' in transactions_df.columns:
            active_vendors = set(transactions_df['payee_name'].apply(normalize))

            if 'payment_date' in transactions_df.columns:
                try:
                    one_year_ago = datetime.now() - timedelta(days=365)
                    recent_txns = transactions_df[
                        pd.to_datetime(transactions_df['payment_date'], errors='coerce') > one_year_ago
                    ]
                    active_recent = set(recent_txns['payee_name'].apply(normalize))
                    dormant = active_vendors - active_recent
                    dormancy_rate = len(dormant) / len(master_df) * 100 if len(master_df) > 0 else 0
                except Exception:
                    pass

            master_vendors_set = set(master_df['normalized'])
            orphan_vendors = master_vendors_set - active_vendors
            orphan_rate = len(orphan_vendors) / len(master_df) * 100 if len(master_df) > 0 else 0

        # 4. Format Quality (vectorised)
        names = master_df['vendor_name'].astype(str)
        all_upper = names.str.isupper() & (names.str.len() > 5)
        no_spaces = (names.str.len() > 20) & (~names.str.contains(' ', na=False))
        format_issues = int((all_upper | no_spaces).sum())
        format_score = (1 - (format_issues / len(master_df))) * 100 if len(master_df) > 0 else 0

        # 5. Overall Health Score
        weights = {
            'completeness': 0.35,
            'duplicate': 0.25,
            'dormancy': 0.15,
            'orphan': 0.15,
            'format': 0.10
        }

        duplicate_score = max(0, 100 - duplicate_rate * 2)
        dormancy_score = max(0, 100 - dormancy_rate)
        orphan_score = max(0, 100 - orphan_rate * 2)

        health_score = (
            completeness_score * weights['completeness'] +
            duplicate_score * weights['duplicate'] +
            dormancy_score * weights['dormancy'] +
            orphan_score * weights['orphan'] +
            format_score * weights['format']
        )

        if health_score >= 80:
            health_level, health_color = "Excellent", "#22C55E"
        elif health_score >= 60:
            health_level, health_color = "Good", "#3B82F6"
        elif health_score >= 40:
            health_level, health_color = "Fair", "#F97316"
        else:
            health_level, health_color = "Poor", "#EF4444"

        return {
            'health_score': round(health_score, 1),
            'health_level': health_level,
            'health_color': health_color,
            'metrics': {
                'total_vendors': len(master_df),
                'completeness_score': round(completeness_score, 1),
                'completeness_issues': self._get_completeness_issues(master_df, available_fields),
                'duplicate_rate': round(duplicate_rate, 1),
                'duplicate_count': duplicate_count,
                'duplicate_examples': self._get_duplicate_examples(master_df),
                'dormancy_rate': round(dormancy_rate, 1) if transactions_df is not None else None,
                'orphan_rate': round(orphan_rate, 1) if transactions_df is not None else None,
                'format_score': round(format_score, 1),
                'format_issues': format_issues
            }
        }

    def _get_completeness_issues(self, df: pd.DataFrame, fields: List[str]) -> List[Dict]:
        if not fields:
            return []
        issues = []
        for _, row in df[df[fields].isnull().any(axis=1)].head(10).iterrows():
            missing = [f for f in fields if pd.isna(row.get(f))]
            issues.append({
                'vendor': row.get('vendor_name', 'Unknown'),
                'missing_fields': missing
            })
        return issues

    def _get_duplicate_examples(self, df: pd.DataFrame) -> List[Dict]:
        if 'normalized' not in df.columns:
            return []
        duplicates = []
        grouped = df.groupby('normalized').filter(lambda g: len(g) > 1).groupby('normalized')
        for name, group in list(grouped)[:5]:
            duplicates.append({
                'normalized': name,
                'variations': group['vendor_name'].tolist()[:3],
                'count': len(group)
            })
        return duplicates

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    def calculate_risk_score(
        self,
        vendor_name: str,
        is_approved: bool,
        total_spend: float,
        duplicate_count: int,
        weekend_count: int,
        first_seen: str = None,
        last_seen: str = None,
        payment_count: int = 0
    ) -> Dict:
        risk = 0
        reasons = []

        if not is_approved:
            risk += 20
            reasons.append("Unapproved vendor")

        if total_spend > 1_000_000:
            risk += 40
            reasons.append("Total spend exceeds R1M")
        elif total_spend > 500_000:
            risk += 30
            reasons.append("Total spend exceeds R500K")
        elif total_spend > 100_000:
            risk += 20
            reasons.append("Total spend exceeds R100K")
        elif total_spend > 50_000:
            risk += 10
            reasons.append("Total spend exceeds R50K")

        if duplicate_count > 0:
            risk += min(20, duplicate_count * 10)
            reasons.append(f"{duplicate_count} potential duplicate payment(s)")

        if weekend_count > 0:
            risk += min(10, weekend_count * 5)
            reasons.append(f"{weekend_count} weekend payment(s)")

        tenure_days = 0
        if first_seen and last_seen:
            try:
                first = datetime.strptime(first_seen[:10], "%Y-%m-%d")
                last = datetime.strptime(last_seen[:10], "%Y-%m-%d")
                tenure_days = (last - first).days

                if tenure_days > 365:
                    risk += 15
                    reasons.append(f"Active for {tenure_days // 365} years")
                elif tenure_days > 180:
                    risk += 10
                    reasons.append(f"Active for {tenure_days // 30} months")
                elif tenure_days > 90:
                    risk += 5
                    reasons.append(f"Active for {tenure_days // 30} months")
            except (ValueError, TypeError):
                tenure_days = 0

        if payment_count > 20:
            risk += 10
            reasons.append(f"{payment_count} payments (frequent)")
        elif payment_count > 10:
            risk += 5
            reasons.append(f"{payment_count} payments (regular)")

        if last_seen:
            try:
                last = datetime.strptime(last_seen[:10], "%Y-%m-%d")
                days_ago = (datetime.now() - last).days
                if days_ago <= 30:
                    risk += 5
                    reasons.append("Active in last 30 days")
            except (ValueError, TypeError):
                pass

        risk = min(risk, 100)
        level = "High" if risk >= 70 else ("Medium" if risk >= 40 else "Low")

        return {
            'score': risk,
            'level': level,
            'reasons': reasons[:4],
            'tenure_days': tenure_days,
            'first_seen': first_seen,
            'last_seen': last_seen,
            'payment_count': payment_count
        }

    # ------------------------------------------------------------------
    # Main analysis entry point
    # ------------------------------------------------------------------

    def run_analysis(
        self,
        master_file: str,
        payments_file: str,
        threshold: int = 80,          # kept for backward compatibility
        batch_size: int = 10000,      # not used in current per‑payment loop, but kept for API
        payments_format: str = None
    ) -> Dict:
        self.logger.info("=" * 60)
        self.logger.info("Starting PayReality Analysis with 7-Pass Semantic Matching")
        self.logger.info("=" * 60)

        master_df, payments_df = self.load_files(master_file, payments_file, payments_format)

        health_report = self.analyze_vendor_master_health(master_df, payments_df)
        self.logger.info(f"Vendor Master Health Score: {health_report['health_score']}% ({health_report['health_level']})")

        master_vendors = master_df['vendor_name'].tolist()
        self.logger.info(f"Loaded {len(master_vendors):,} approved vendors")

        duplicates = self.find_duplicate_vendors(payments_df)
        self.logger.info(f"Found {len(duplicates)} potential duplicate vendors")

        total_payments = len(payments_df)
        self.logger.info(f"Processing {total_payments:,} payments with 7-pass matching")

        # Pre‑compute caches once
        self._invalidate_caches()
        self._vendor_list_cache = master_vendors
        for v in master_vendors:
            self._cleaned_vendors_cache[v] = self.clean_name(v)
        self._build_phonetic_cache(master_vendors)

        cleaned_list = list(self._cleaned_vendors_cache.values())
        vendor_keys = list(self._cleaned_vendors_cache.keys())

        # Pre‑compute cleaned payee names for all payments (speeds up individual passes)
        payees = payments_df['payee_name'].tolist()
        payees_clean = [self.clean_name(p) for p in payees]

        results = []
        exceptions = []
        total_spend = 0
        exception_spend = 0
        match_stats = {
            'exact': 0, 'normalized': 0, 'token_sort': 0, 'partial': 0,
            'levenshtein': 0, 'phonetic': 0, 'obfuscation': 0, 'none': 0
        }

        vendor_details = defaultdict(lambda: {
            'payments': [],
            'first_seen': None,
            'last_seen': None,
            'count': 0,
            'weekend_count': 0,
            'total_spend': 0
        })

        # Helper to add a result
        def add_result(payee, amount, payment_date, matched_vendor, score, strategy, idx):
            nonlocal total_spend, exception_spend
            total_spend += amount
            is_exception = matched_vendor is None
            match_stats[strategy] += 1

            result = {
                'payee_name': payee,
                'matched_vendor': matched_vendor,
                'match_score': score,
                'match_strategy': strategy,
                'is_exception': is_exception,
                'amount': amount,
                'row_index': idx
            }
            results.append(result)
            vendor_details[payee]['payments'].append(result)
            vendor_details[payee]['count'] += 1
            vendor_details[payee]['total_spend'] += amount

            if payment_date:
                if (not vendor_details[payee]['first_seen'] or
                        payment_date < vendor_details[payee]['first_seen']):
                    vendor_details[payee]['first_seen'] = payment_date
                if (not vendor_details[payee]['last_seen'] or
                        payment_date > vendor_details[payee]['last_seen']):
                    vendor_details[payee]['last_seen'] = payment_date

                try:
                    date_obj = pd.to_datetime(payment_date)
                    if date_obj.dayofweek >= 5:
                        vendor_details[payee]['weekend_count'] += 1
                except Exception:
                    pass

            if is_exception:
                exceptions.append(result)
                exception_spend += amount

        # Process each payment
        for idx, (payee, payee_clean, row) in enumerate(zip(payees, payees_clean, payments_df.iterrows())):
            amount = row[1]['amount']
            payment_date = row[1].get('payment_date', '')

            # --- Pass 1: Exact ---
            if payee in master_vendors:
                add_result(payee, amount, payment_date, payee, 100, "exact", idx)
                continue

            # --- Pass 2: Normalized ---
            matched = False
            for vendor, vendor_clean in self._cleaned_vendors_cache.items():
                if payee_clean == vendor_clean:
                    add_result(payee, amount, payment_date, vendor, 100, "normalized", idx)
                    matched = True
                    break
            if matched:
                continue

            # --- Pass 3: Token sort ---
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.token_sort_ratio)
            if result and result[1] >= self.thresholds.get('token_sort', 80):
                add_result(payee, amount, payment_date, vendor_keys[result[2]], result[1], "token_sort", idx)
                continue

            # --- Pass 4: Partial ---
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.partial_ratio)
            if result and result[1] >= self.thresholds.get('partial', 80):
                add_result(payee, amount, payment_date, vendor_keys[result[2]], result[1], "partial", idx)
                continue

            # --- Pass 5: Levenshtein ---
            result = process.extractOne(payee_clean, cleaned_list, scorer=fuzz.QRatio)
            if result and result[1] >= self.thresholds.get('levenshtein', 75):
                add_result(payee, amount, payment_date, vendor_keys[result[2]], result[1], "levenshtein", idx)
                continue

            # --- Pass 6: Phonetic ---
            payee_soundex = self._soundex(payee_clean)
            if payee_soundex in self._soundex_to_vendors:
                matched_vendor = self._soundex_to_vendors[payee_soundex][0]
                add_result(payee, amount, payment_date, matched_vendor, 85, "phonetic", idx)
                continue

            # --- Pass 7: Obfuscation ---
            is_obfuscated, cleaned, obf_type = self.detect_obfuscation(payee)
            if is_obfuscated:
                result = process.extractOne(cleaned, cleaned_list, scorer=fuzz.token_sort_ratio)
                if result and result[1] >= self.thresholds.get('obfuscation', 80):
                    add_result(payee, amount, payment_date, vendor_keys[result[2]], result[1], f"obfuscation_{obf_type}", idx)
                    continue

            # --- No match ---
            add_result(payee, amount, payment_date, None, 0, "none", idx)

        # Enrich exceptions with risk scores
        exception_with_risk = []
        for ex in exceptions:
            vendor = ex['payee_name']
            details = vendor_details.get(vendor, {})
            risk = self.calculate_risk_score(
                vendor,
                not ex['is_exception'],
                details.get('total_spend', 0),
                sum(1 for d in duplicates if d['display_name'] == vendor),
                details.get('weekend_count', 0),
                details.get('first_seen'),
                details.get('last_seen'),
                details.get('count', 0)
            )
            ex_with_risk = ex.copy()
            ex_with_risk['risk_score'] = risk['score']
            ex_with_risk['risk_level'] = risk['level']
            ex_with_risk['risk_reasons'] = risk['reasons']
            ex_with_risk['first_seen'] = risk.get('first_seen', '')
            ex_with_risk['last_seen'] = risk.get('last_seen', '')
            ex_with_risk['payment_count'] = risk.get('payment_count', 0)
            ex_with_risk['tenure_days'] = risk.get('tenure_days', 0)
            exception_with_risk.append(ex_with_risk)

        entropy_score = (exception_spend / total_spend * 100) if total_spend > 0 else 0
        self.match_stats = match_stats

        self.logger.info("=" * 60)
        self.logger.info("Analysis Complete")
        self.logger.info(f"Total Payments:         {len(results):,}")
        self.logger.info(f"Total Spend:            R {total_spend:,.2f}")
        self.logger.info(f"Exceptions Found:       {len(exceptions):,}")
        self.logger.info(f"Exception Spend:        R {exception_spend:,.2f}")
        self.logger.info(f"Control Entropy Score:  {entropy_score:.2f}%")
        self.logger.info(f"Duplicate Vendors:      {len(duplicates)}")
        self.logger.info(f"Vendor Master Health:   {health_report['health_score']}% ({health_report['health_level']})")
        self.logger.info("Match Strategy Distribution:")
        for strategy, count in sorted(match_stats.items(), key=lambda x: x[1], reverse=True):
            pct = (count / len(results) * 100) if len(results) > 0 else 0
            self.logger.info(f"  {strategy}: {count:,} ({pct:.1f}%)")
        self.logger.info("=" * 60)

        return {
            'results': results,
            'exceptions': exception_with_risk,
            'duplicates': duplicates,
            'health_report': health_report,
            'total_payments': len(results),
            'total_spend': total_spend,
            'exception_count': len(exceptions),
            'exception_spend': exception_spend,
            'entropy_score': entropy_score,
            'master_vendor_count': len(master_vendors),
            'match_stats': match_stats
        }

    def generate_data_hash(self, df: pd.DataFrame) -> str:
        data_string = df.to_csv(index=False).encode('utf-8')
        return hashlib.sha256(data_string).hexdigest()[:16]