"""
PayReality Core Module
Professional data validation, error handling, and matching engine
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from rapidfuzz import fuzz, process
import re
import hashlib

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class MatchingError(Exception):
    """Custom exception for matching errors"""
    pass

class PayRealityEngine:
    def __init__(self, log_level=logging.INFO, config: Dict = None):
        """Initialize the PayReality engine with configuration"""
        self.config = config or {}
        self.setup_logging(log_level)
        self.master_df = None
        self.payments_df = None
        self.results = []
        self.exceptions = []
        self.hash_cache = {}
        
    def setup_logging(self, log_level):
        """Configure professional logging with file rotation"""
        self.logger = logging.getLogger('PayReality')
        self.logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler with rotation (simple version)
        log_file = os.path.join(log_dir, f"payreality_{datetime.now().strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file, mode='a')
        fh.setLevel(log_level)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        self.logger.info(f"PayReality engine initialized")
    
    def validate_file(self, filepath: str, expected_columns: List[str], file_type: str) -> pd.DataFrame:
        """
        Validate file exists, can be read, and has required columns
        Returns: DataFrame with validated data
        """
        self.logger.info(f"Validating {file_type}: {filepath}")
        
        # Check file exists
        if not os.path.exists(filepath):
            raise DataValidationError(f"{file_type} file not found: {filepath}")
        
        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise DataValidationError(f"{file_type} file is empty: {filepath}")
        
        self.logger.info(f"File size: {file_size:,} bytes")
        
        # Try to read file with multiple encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                if filepath.lower().endswith('.csv'):
                    df = pd.read_csv(filepath, encoding=encoding)
                elif filepath.lower().endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(filepath)
                else:
                    raise DataValidationError(f"Unsupported file format: {filepath}")
                
                used_encoding = encoding
                self.logger.info(f"Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                self.logger.warning(f"Failed with {encoding} encoding")
                continue
            except Exception as e:
                self.logger.warning(f"Failed with {encoding}: {str(e)[:100]}")
                continue
        
        if df is None:
            raise DataValidationError(f"Could not read {file_type} file with any encoding")
        
        # Check for required columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            raise DataValidationError(
                f"Missing required columns in {file_type}: {missing_columns}\n"
                f"Found columns: {list(df.columns)}"
            )
        
        # Check for empty data
        if len(df) == 0:
            raise DataValidationError(f"{file_type} file has no data rows")
        
        self.logger.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
        
        # Data quality checks
        null_counts = df[expected_columns].isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                percentage = (null_count / len(df)) * 100
                self.logger.warning(f"Column '{col}' has {null_count:,} null values ({percentage:.1f}%)")
        
        return df
    
    def load_files(self, master_file: str, payments_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load and validate both input files
        """
        self.logger.info("=" * 60)
        self.logger.info("Loading and validating input files")
        self.logger.info("=" * 60)
        
        # Validate vendor master
        self.master_df = self.validate_file(
            master_file, 
            ['vendor_name'], 
            'Vendor Master'
        )
        
        # Validate payments file
        self.payments_df = self.validate_file(
            payments_file,
            ['payee_name', 'amount'],
            'Payments'
        )
        
        # Additional validation: check for negative amounts
        negative_amounts = self.payments_df[self.payments_df['amount'] < 0]
        if len(negative_amounts) > 0:
            self.logger.warning(f"Found {len(negative_amounts):,} payments with negative amounts")
            # Optionally filter them out? We'll keep them but note in report
        
        return self.master_df, self.payments_df
    
    def clean_name(self, name: str, config: Dict = None) -> str:
        """
        Advanced name cleaning with configurable rules
        """
        if pd.isna(name):
            return ""
        
        # Merge default config with provided config
        rules = {
            'lowercase': True,
            'remove_punctuation': True,
            'remove_extra_spaces': True,
            'strip_suffixes': True,
            'replace_numbers': False,
            'remove_common_words': False,
            'suffixes': [' ltd', ' inc', ' corp', ' llc', ' pty', 
                        ' technologies', ' solutions', ' group', 
                        ' holdings', ' international', ' systems',
                        ' pty ltd', ' cc', ' partnership', ' and',
                        ' the', ' co', ' company', ' enterprises']
        }
        
        if config:
            rules.update(config)
        
        name = str(name)
        
        if rules.get('lowercase'):
            name = name.lower()
        
        if rules.get('remove_punctuation'):
            name = re.sub(r'[^\w\s]', ' ', name)
        
        if rules.get('remove_common_words') and rules.get('remove_common_words') != False:
            common_words = ['the', 'and', 'for', 'with', 'limited', 'company']
            for word in common_words:
                name = re.sub(rf'\b{word}\b', '', name)
        
        if rules.get('strip_suffixes'):
            for suffix in rules['suffixes']:
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break
        
        if rules.get('replace_numbers'):
            name = re.sub(r'\d+', '', name)
        
        if rules.get('remove_extra_spaces'):
            name = ' '.join(name.split())
        
        return name.strip()
    
    def advanced_fuzzy_match(self, payee: str, master_vendors: List[str], 
                             threshold: int = 80, use_phonetic: bool = True) -> Tuple[Optional[str], int, str]:
        """
        Advanced fuzzy matching with multiple strategies
        Returns: (matched_vendor, score, strategy_used)
        """
        payee_clean = self.clean_name(payee)
        
        # Strategy 1: Direct match after cleaning
        for vendor in master_vendors:
            vendor_clean = self.clean_name(vendor)
            if payee_clean == vendor_clean:
                return vendor, 100, "exact_clean"
        
        # Strategy 2: Token sort ratio (handles word order)
        result = process.extractOne(
            payee_clean, 
            [self.clean_name(v) for v in master_vendors],
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= threshold:
            idx = result[2]
            return master_vendors[idx], result[1], "token_sort"
        
        # Strategy 3: Partial ratio (handles extra words)
        result = process.extractOne(
            payee_clean,
            [self.clean_name(v) for v in master_vendors],
            scorer=fuzz.partial_ratio
        )
        
        if result and result[1] >= threshold:
            idx = result[2]
            return master_vendors[idx], result[1], "partial"
        
        # Strategy 4: Phonetic matching (for similar sounding names)
        if use_phonetic:
            def phonetic_key(word):
                word = word.lower()
                # Simple soundex-like matching
                word = re.sub(r'[aeiou]', '', word)
                word = re.sub(r'(ph|gh)', 'f', word)
                word = re.sub(r'(ck|c)', 'k', word)
                word = re.sub(r'(sh|ch)', 'x', word)
                word = re.sub(r'(tion|sion)', 'shun', word)
                return word[:10]
            
            payee_phonetic = phonetic_key(payee_clean)
            for i, vendor in enumerate(master_vendors):
                vendor_phonetic = phonetic_key(self.clean_name(vendor))
                if payee_phonetic == vendor_phonetic:
                    return vendor, 85, "phonetic"
        
        # Strategy 5: Quick ratio (last resort)
        result = process.extractOne(
            payee_clean,
            [self.clean_name(v) for v in master_vendors],
            scorer=fuzz.QRatio
        )
        
        if result and result[1] >= threshold - 10:
            idx = result[2]
            return master_vendors[idx], result[1], "quick"
        
        return None, 0, "none"
    
    def run_analysis(self, master_file: str, payments_file: str, 
                     threshold: int = 80, batch_size: int = 10000) -> Dict:
        """
        Main analysis engine with comprehensive results
        """
        self.logger.info("=" * 60)
        self.logger.info("Starting PayReality Analysis")
        self.logger.info("=" * 60)
        
        # Load files
        master_df, payments_df = self.load_files(master_file, payments_file)
        
        # Get master vendor list
        master_vendors = master_df['vendor_name'].tolist()
        self.logger.info(f"Loaded {len(master_vendors):,} approved vendors")
        
        # Process payments in batches
        total_payments = len(payments_df)
        self.logger.info(f"Processing {total_payments:,} payments in batches of {batch_size:,}")
        
        results = []
        exceptions = []
        total_spend = 0
        exception_spend = 0
        match_stats = {
            'exact_clean': 0,
            'token_sort': 0,
            'partial': 0,
            'phonetic': 0,
            'quick': 0,
            'none': 0
        }
        
        for start_idx in range(0, total_payments, batch_size):
            end_idx = min(start_idx + batch_size, total_payments)
            batch = payments_df.iloc[start_idx:end_idx]
            
            self.logger.info(f"Processing batch {start_idx//batch_size + 1}/{(total_payments + batch_size - 1)//batch_size} (rows {start_idx+1}-{end_idx})")
            
            for idx, row in batch.iterrows():
                payee = row['payee_name']
                amount = row['amount']
                total_spend += amount
                
                # Try to match
                matched_vendor, score, strategy = self.advanced_fuzzy_match(payee, master_vendors, threshold)
                
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
                
                if is_exception:
                    exceptions.append(result)
                    exception_spend += amount
        
        # Calculate Control Entropy Score
        entropy_score = (exception_spend / total_spend * 100) if total_spend > 0 else 0
        
        self.logger.info("=" * 60)
        self.logger.info("Analysis Complete")
        self.logger.info(f"Total Payments: {len(results):,}")
        self.logger.info(f"Total Spend: R {total_spend:,.2f}")
        self.logger.info(f"Exceptions Found: {len(exceptions):,}")
        self.logger.info(f"Exception Spend: R {exception_spend:,.2f}")
        self.logger.info(f"Control Entropy Score: {entropy_score:.2f}%")
        self.logger.info(f"Match Strategy Distribution:")
        for strategy, count in sorted(match_stats.items(), key=lambda x: x[1], reverse=True):
            self.logger.info(f"  {strategy}: {count:,} ({count/len(results)*100:.1f}%)")
        self.logger.info("=" * 60)
        
        return {
            'results': results,
            'exceptions': exceptions,
            'total_payments': len(results),
            'total_spend': total_spend,
            'exception_count': len(exceptions),
            'exception_spend': exception_spend,
            'entropy_score': entropy_score,
            'master_vendor_count': len(master_vendors),
            'match_stats': match_stats
        }
    
    def generate_data_hash(self, df: pd.DataFrame) -> str:
        """Generate a hash of the data for audit purposes"""
        data_string = df.to_csv(index=False).encode('utf-8')
        return hashlib.sha256(data_string).hexdigest()[:16]