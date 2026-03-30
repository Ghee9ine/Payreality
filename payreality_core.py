"""
PayReality Core Module
Professional data validation, error handling, and matching engine
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from rapidfuzz import fuzz, process
import re

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class PayRealityEngine:
    def __init__(self, log_level=logging.INFO):
        """Initialize the PayReality engine with logging"""
        self.setup_logging(log_level)
        self.master_df = None
        self.payments_df = None
        self.results = []
        self.exceptions = []
        
    def setup_logging(self, log_level):
        """Configure professional logging"""
        self.logger = logging.getLogger('PayReality')
        self.logger.setLevel(log_level)
        
        # File handler
        log_file = f"payreality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        self.logger.info(f"PayReality engine initialized. Log file: {log_file}")
    
    def validate_file(self, filepath: str, expected_columns: List[str], file_type: str) -> pd.DataFrame:
        """
        Validate file exists, can be read, and has required columns
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
        
        for encoding in encodings:
            try:
                if filepath.endswith('.csv'):
                    df = pd.read_csv(filepath, encoding=encoding)
                elif filepath.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(filepath)
                else:
                    raise DataValidationError(f"Unsupported file format: {filepath}")
                
                self.logger.info(f"Successfully read file with {encoding} encoding")
                break
            except Exception as e:
                self.logger.warning(f"Failed with {encoding}: {str(e)}")
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
        
        self.logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Data quality checks
        null_counts = df[expected_columns].isnull().sum()
        for col, null_count in null_counts.items():
            if null_count > 0:
                self.logger.warning(f"{col} has {null_count} null values ({null_count/len(df)*100:.1f}%)")
        
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
            self.logger.warning(f"Found {len(negative_amounts)} payments with negative amounts")
        
        return self.master_df, self.payments_df
    
    def clean_name(self, name: str, config: Dict = None) -> str:
        """
        Advanced name cleaning with configurable rules
        """
        if pd.isna(name):
            return ""
        
        # Default cleaning rules
        rules = {
            'lowercase': True,
            'remove_punctuation': True,
            'remove_extra_spaces': True,
            'strip_suffixes': True,
            'replace_numbers': False,
            'suffixes': [' ltd', ' inc', ' corp', ' llc', ' pty', 
                        ' technologies', ' solutions', ' group', 
                        ' holdings', ' international', ' systems',
                        ' pty ltd', ' cc', ' partnership']
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
    
    def advanced_fuzzy_match(self, payee: str, master_vendors: List[str], 
                             threshold: int = 80, use_phonetic: bool = True) -> Tuple[Optional[str], int]:
        """
        Advanced fuzzy matching with multiple strategies
        """
        payee_clean = self.clean_name(payee)
        
        # Strategy 1: Direct match after cleaning
        for vendor in master_vendors:
            vendor_clean = self.clean_name(vendor)
            if payee_clean == vendor_clean:
                return vendor, 100
        
        # Strategy 2: Token sort ratio (handles word order)
        result = process.extractOne(
            payee_clean, 
            [self.clean_name(v) for v in master_vendors],
            scorer=fuzz.token_sort_ratio
        )
        
        if result and result[1] >= threshold:
            idx = result[2]
            return master_vendors[idx], result[1]
        
        # Strategy 3: Partial ratio (handles extra words)
        result = process.extractOne(
            payee_clean,
            [self.clean_name(v) for v in master_vendors],
            scorer=fuzz.partial_ratio
        )
        
        if result and result[1] >= threshold:
            idx = result[2]
            return master_vendors[idx], result[1]
        
        # Strategy 4: Phonetic matching (for similar sounding names)
        if use_phonetic:
            # Simple soundex-like matching for common typos
            def phonetic_key(word):
                word = word.lower()
                # Remove vowels and common variations
                word = re.sub(r'[aeiou]', '', word)
                word = re.sub(r'(ph|gh)', 'f', word)
                word = re.sub(r'(ck|c)', 'k', word)
                return word[:10]
            
            payee_phonetic = phonetic_key(payee_clean)
            for vendor in master_vendors:
                vendor_phonetic = phonetic_key(self.clean_name(vendor))
                if payee_phonetic == vendor_phonetic:
                    return vendor, 85
        
        return None, 0
    
    def run_analysis(self, master_file: str, payments_file: str, 
                     threshold: int = 80) -> Dict:
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
        self.logger.info(f"Loaded {len(master_vendors)} approved vendors")
        
        # Process payments
        self.logger.info("Processing payments...")
        results = []
        exceptions = []
        total_spend = 0
        exception_spend = 0
        
        for idx, row in payments_df.iterrows():
            payee = row['payee_name']
            amount = row['amount']
            total_spend += amount
            
            # Try to match
            matched_vendor, score = self.advanced_fuzzy_match(payee, master_vendors, threshold)
            
            is_exception = matched_vendor is None
            
            result = {
                'payee_name': payee,
                'matched_vendor': matched_vendor,
                'match_score': score,
                'is_exception': is_exception,
                'amount': amount,
                'row_index': idx
            }
            
            results.append(result)
            
            if is_exception:
                exceptions.append(result)
                exception_spend += amount
            
            # Progress logging every 1000 rows
            if (idx + 1) % 1000 == 0:
                self.logger.info(f"Processed {idx + 1}/{len(payments_df)} payments")
        
        # Calculate Control Entropy Score
        entropy_score = (exception_spend / total_spend * 100) if total_spend > 0 else 0
        
        self.logger.info("=" * 60)
        self.logger.info("Analysis Complete")
        self.logger.info(f"Total Payments: {len(payments_df):,}")
        self.logger.info(f"Total Spend: R {total_spend:,.2f}")
        self.logger.info(f"Exceptions Found: {len(exceptions):,}")
        self.logger.info(f"Exception Spend: R {exception_spend:,.2f}")
        self.logger.info(f"Control Entropy Score: {entropy_score:.2f}%")
        self.logger.info("=" * 60)
        
        return {
            'results': results,
            'exceptions': exceptions,
            'total_payments': len(payments_df),
            'total_spend': total_spend,
            'exception_count': len(exceptions),
            'exception_spend': exception_spend,
            'entropy_score': entropy_score,
            'master_vendor_count': len(master_vendors)
        }

# Test the core module
if __name__ == "__main__":
    engine = PayRealityEngine()
    
    # Test with sample files
    try:
        results = engine.run_analysis('vendor_master.csv', 'payments.csv')
        print(f"\nAnalysis successful!")
        print(f"Control Entropy Score: {results['entropy_score']:.2f}%")
        print(f"Exceptions found: {results['exception_count']}")
    except DataValidationError as e:
        print(f"Validation error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")