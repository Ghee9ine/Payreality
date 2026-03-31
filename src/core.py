"""
PayReality Core Module
7-Pass Semantic Matching Engine
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
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
        
        self.logger.info(f"PayReality engine initialized with 7-pass semantic matching")
    
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
                self.logger.warning(f"Column '{col}' has {null_count:,} null values ({percentage:.1f}%)")
        
        return df
    
    def load_files(self, master_file: str, payments_file: str, payments_format: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.logger.info("=" * 60)
        self.logger.info("Loading and validating input files")
        self.logger.info("=" * 60)
        
        parser = FileParser()
        
        self.master_df = self.validate_file(master_file, ['vendor_name'], 'Vendor Master')
        
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
    
    def clean_name(self, name: str, config: Dict = None) -> str:
        """Normalize vendor name for matching"""
        if pd.isna(name):
            return ""
        
        rules = {
            'lowercase': True,
            'remove_punctuation': True,
            'remove_extra_spaces': True,
            'strip_suffixes': True,
            'suffixes': [' ltd', ' inc', ' corp', ' llc', ' pty', ' technologies', ' solutions', 
                        ' group', ' holdings', ' international', ' systems', ' pty ltd', ' cc',
                        ' limited', ' corporation', ' incorporated', ' company', ' co']
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
    
    def detect_obfuscation(self, payee: str) -> Tuple[bool, str, str]:
        """
        Detect intentional obfuscation in vendor names
        Returns: (is_obfuscated, cleaned_name, obfuscation_type)
        """
        original = payee
        
        # Common obfuscation patterns
        patterns = [
            (r'[mM]\.?[iI]\.?[cC]\.?[rR]\.?[oO]\.?[sS]\.?[oO]\.?[fF]\.?[tT]', 'microsoft'),
            (r'[gG]\.?[oO]\.?[oO]\.?[gG]\.?[lL]\.?[eE]', 'google'),
            (r'[aA]\.?[mM]\.?[aA]\.?[zZ]\.?[oO]\.?[nN]', 'amazon'),
            (r'[dD]\.?[eE]\.?[lL]\.?[lL]', 'dell'),
            (r'[iI]\.?[bB]\.?[mM]', 'ibm'),
            (r'[aA]\.?[pP]\.?[pP]\.?[lL]\.?[eE]', 'apple'),
            (r'[cC]\.?[oO]\.?[cC]\.?[aA]\.?[cC]\.?[oO]\.?[lL]\.?[aA]', 'coca-cola'),
            (r'[mM]\.?[cC]\.?[dD]\.?[oO]\.?[nN]\.?[aA]\.?[lL]\.?[dD]\.?[sS]', 'mcdonalds'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, original, re.IGNORECASE):
                cleaned = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                return True, cleaned, "dot_obfuscation"
        
        # Check for leetspeak (3 = E, 0 = O, 1 = I, etc)
        leet_map = {'3': 'e', '0': 'o', '1': 'i', '4': 'a', '5': 's', '7': 't'}
        leet_detected = False
        cleaned = original
        for leet, letter in leet_map.items():
            if leet in cleaned.lower():
                cleaned = cleaned.replace(leet, letter)
                leet_detected = True
        
        if leet_detected:
            return True, cleaned, "leetspeak"
        
        # Check for repeated characters (e.g., "Miiiicrosooft")
        if re.search(r'(.)\1{2,}', original):
            cleaned = re.sub(r'(.)\1{2,}', r'\1\1', original)
            return True, cleaned, "character_repetition"
        
        return False, original, "none"
    
    def phonetic_match(self, text1: str, text2: str) -> float:
        """Simple phonetic similarity for matching"""
        # Remove vowels for rough phonetic matching
        text1 = re.sub(r'[aeiou]', '', text1.lower())
        text2 = re.sub(r'[aeiou]', '', text2.lower())
        
        # Common phonetic substitutions
        text1 = re.sub(r'(ph|gh)', 'f', text1)
        text2 = re.sub(r'(ph|gh)', 'f', text2)
        text1 = re.sub(r'(ck|c)', 'k', text1)
        text2 = re.sub(r'(ck|c)', 'k', text2)
        text1 = re.sub(r'(sh|ch)', 'x', text1)
        text2 = re.sub(r'(sh|ch)', 'x', text2)
        
        # Calculate similarity
        if text1 == text2:
            return 100.0
        
        return fuzz.token_sort_ratio(text1, text2)
    
    def semantic_match_7pass(self, payee: str, master_vendors: List[str], threshold: int = 80) -> Tuple[Optional[str], int, str]:
        """
        7-Pass Semantic Matching:
        Pass 1: Exact match
        Pass 2: Normalized match (cleaned)
        Pass 3: Token sort ratio
        Pass 4: Partial ratio
        Pass 5: Levenshtein distance (via rapidfuzz)
        Pass 6: Phonetic match
        Pass 7: Obfuscation detection
        """
        payee_original = payee
        
        # Pass 1: Exact match
        for vendor in master_vendors:
            if payee == vendor:
                return vendor, 100, "exact"
        
        # Pass 2: Normalized match (cleaned)
        payee_clean = self.clean_name(payee)
        for vendor in master_vendors:
            vendor_clean = self.clean_name(vendor)
            if payee_clean == vendor_clean:
                return vendor, 100, "normalized"
        
        # Pass 3: Token sort ratio (handles word order)
        result = process.extractOne(payee_clean, [self.clean_name(v) for v in master_vendors], scorer=fuzz.token_sort_ratio)
        if result and result[1] >= threshold:
            return master_vendors[result[2]], result[1], "token_sort"
        
        # Pass 4: Partial ratio (handles extra words)
        result = process.extractOne(payee_clean, [self.clean_name(v) for v in master_vendors], scorer=fuzz.partial_ratio)
        if result and result[1] >= threshold:
            return master_vendors[result[2]], result[1], "partial"
        
        # Pass 5: Levenshtein distance (via QRatio for better performance)
        result = process.extractOne(payee_clean, [self.clean_name(v) for v in master_vendors], scorer=fuzz.QRatio)
        if result and result[1] >= threshold - 5:
            return master_vendors[result[2]], result[1], "levenshtein"
        
        # Pass 6: Phonetic match
        payee_phonetic = self.clean_name(payee)
        for vendor in master_vendors:
            vendor_phonetic = self.clean_name(vendor)
            phonetic_score = self.phonetic_match(payee_phonetic, vendor_phonetic)
            if phonetic_score >= threshold:
                return vendor, phonetic_score, "phonetic"
        
        # Pass 7: Obfuscation detection
        is_obfuscated, cleaned, obf_type = self.detect_obfuscation(payee)
        if is_obfuscated:
            result = process.extractOne(cleaned, [self.clean_name(v) for v in master_vendors], scorer=fuzz.token_sort_ratio)
            if result and result[1] >= threshold:
                return master_vendors[result[2]], result[1], f"obfuscation_{obf_type}"
        
        return None, 0, "none"
    
    def find_duplicate_vendors(self, payments_df: pd.DataFrame) -> List[Dict]:
        """Find potential duplicate payments"""
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
    
    def calculate_risk_score(self, vendor_name: str, is_approved: bool, total_spend: float, 
                             duplicate_count: int, weekend_count: int, 
                             first_seen: str = None, last_seen: str = None, 
                             payment_count: int = 0) -> Dict:
        """Calculate risk score for a vendor with tenure and frequency"""
        risk = 0
        reasons = []
        
        if not is_approved:
            risk += 20
            reasons.append("Unapproved vendor")
        
        if total_spend > 1000000:
            risk += 40
            reasons.append(f"Total spend exceeds R1M")
        elif total_spend > 500000:
            risk += 30
            reasons.append(f"Total spend exceeds R500K")
        elif total_spend > 100000:
            risk += 20
            reasons.append(f"Total spend exceeds R100K")
        elif total_spend > 50000:
            risk += 10
            reasons.append(f"Total spend exceeds R50K")
        
        if duplicate_count > 0:
            risk += min(20, duplicate_count * 10)
            reasons.append(f"{duplicate_count} potential duplicate payment(s)")
        
        if weekend_count > 0:
            risk += min(10, weekend_count * 5)
            reasons.append(f"{weekend_count} weekend payment(s)")
        
        if first_seen and last_seen:
            try:
                first = datetime.strptime(first_seen[:10], "%Y-%m-%d")
                last = datetime.strptime(last_seen[:10], "%Y-%m-%d")
                tenure_days = (last - first).days
                
                if tenure_days > 365:
                    risk += 15
                    reasons.append(f"Active for {tenure_days//365} years")
                elif tenure_days > 180:
                    risk += 10
                    reasons.append(f"Active for {tenure_days//30} months")
                elif tenure_days > 90:
                    risk += 5
                    reasons.append(f"Active for {tenure_days//30} months")
            except:
                pass
        
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
            except:
                pass
        
        risk = min(risk, 100)
        
        if risk >= 70:
            level = "High"
        elif risk >= 40:
            level = "Medium"
        else:
            level = "Low"
        
        return {
            'score': risk,
            'level': level,
            'reasons': reasons[:4],
            'tenure_days': (datetime.strptime(last_seen[:10], "%Y-%m-%d") - datetime.strptime(first_seen[:10], "%Y-%m-%d")).days if first_seen and last_seen else 0,
            'first_seen': first_seen,
            'last_seen': last_seen,
            'payment_count': payment_count
        }
    
    def run_analysis(self, master_file: str, payments_file: str, 
                     threshold: int = 80, batch_size: int = 10000,
                     payments_format: str = None) -> Dict:
        self.logger.info("=" * 60)
        self.logger.info("Starting PayReality Analysis with 7-Pass Semantic Matching")
        self.logger.info("=" * 60)
        
        master_df, payments_df = self.load_files(master_file, payments_file, payments_format)
        
        master_vendors = master_df['vendor_name'].tolist()
        self.logger.info(f"Loaded {len(master_vendors):,} approved vendors")
        
        duplicates = self.find_duplicate_vendors(payments_df)
        self.logger.info(f"Found {len(duplicates)} potential duplicate vendors")
        
        total_payments = len(payments_df)
        self.logger.info(f"Processing {total_payments:,} payments with 7-pass matching")
        
        results = []
        exceptions = []
        total_spend = 0
        exception_spend = 0
        match_stats = {
            'exact': 0, 'normalized': 0, 'token_sort': 0, 'partial': 0,
            'levenshtein': 0, 'phonetic': 0, 'obfuscation': 0, 'none': 0
        }
        
        vendor_payments = defaultdict(list)
        vendor_details = defaultdict(lambda: {
            'payments': [],
            'first_seen': None,
            'last_seen': None,
            'count': 0,
            'weekend_count': 0,
            'total_spend': 0
        })
        
        for idx, row in payments_df.iterrows():
            payee = row['payee_name']
            amount = row['amount']
            payment_date = row.get('payment_date', '')
            total_spend += amount
            
            matched_vendor, score, strategy = self.semantic_match_7pass(payee, master_vendors, threshold)
            
            is_exception = matched_vendor is None
            match_stats[strategy] = match_stats.get(strategy, 0) + 1
            
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
            vendor_payments[payee].append(result)
            
            # Track vendor details for risk scoring
            vendor_details[payee]['payments'].append(result)
            vendor_details[payee]['count'] += 1
            vendor_details[payee]['total_spend'] += amount
            
            if payment_date:
                if not vendor_details[payee]['first_seen'] or payment_date < vendor_details[payee]['first_seen']:
                    vendor_details[payee]['first_seen'] = payment_date
                if not vendor_details[payee]['last_seen'] or payment_date > vendor_details[payee]['last_seen']:
                    vendor_details[payee]['last_seen'] = payment_date
                
                try:
                    date_obj = pd.to_datetime(payment_date)
                    if date_obj.dayofweek >= 5:
                        vendor_details[payee]['weekend_count'] += 1
                except:
                    pass
            
            if is_exception:
                exceptions.append(result)
                exception_spend += amount
        
        # Calculate risk scores for exceptions
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
        self.logger.info("Analysis Complete - 7-Pass Semantic Matching Results")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Payments: {len(results):,}")
        self.logger.info(f"Total Spend: R {total_spend:,.2f}")
        self.logger.info(f"Exceptions Found: {len(exceptions):,}")
        self.logger.info(f"Exception Spend: R {exception_spend:,.2f}")
        self.logger.info(f"Control Entropy Score: {entropy_score:.2f}%")
        self.logger.info(f"Duplicate Vendors Found: {len(duplicates)}")
        self.logger.info("Match Strategy Distribution:")
        for strategy, count in sorted(match_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(results) * 100) if len(results) > 0 else 0
            self.logger.info(f"  {strategy}: {count:,} ({percentage:.1f}%)")
        self.logger.info("=" * 60)
        
        return {
            'results': results,
            'exceptions': exception_with_risk,
            'duplicates': duplicates,
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