"""
PayReality File Parser Module
Handles multiple file formats: CSV, Excel, PDF
"""

import pandas as pd
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
import re
import PyPDF2
import pdfplumber
from datetime import datetime

class FileParser:
    def __init__(self):
        self.logger = logging.getLogger('PayReality')
    
    def parse_file(self, filepath: str, file_type: str = None) -> pd.DataFrame:
        """
        Parse any supported file format into a DataFrame
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Detect file type if not specified
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
        
        if file_type == 'csv':
            return self._parse_csv(filepath)
        elif file_type == 'excel':
            return self._parse_excel(filepath)
        elif file_type == 'pdf':
            return self._parse_pdf(filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _parse_csv(self, filepath: str) -> pd.DataFrame:
        """Parse CSV file with multiple encoding attempts"""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                self.logger.info(f"Successfully parsed CSV with {encoding} encoding")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.logger.warning(f"Failed with {encoding}: {str(e)}")
                continue
        
        raise ValueError(f"Could not parse CSV file with any encoding")
    
    def _parse_excel(self, filepath: str) -> pd.DataFrame:
        """Parse Excel file (both .xlsx and .xls)"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(filepath)
            sheet_names = excel_file.sheet_names
            
            self.logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")
            
            # Try to find the sheet with payment data
            for sheet in sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet)
                
                # Check if this sheet has payment-like columns
                cols_lower = [c.lower() for c in df.columns]
                if any('vendor' in c or 'payee' in c for c in cols_lower) and any('amount' in c or 'value' in c for c in cols_lower):
                    self.logger.info(f"Using sheet: {sheet}")
                    return df
            
            # If no obvious sheet, use the first one
            self.logger.info("Using first sheet")
            return pd.read_excel(filepath, sheet_name=0)
            
        except Exception as e:
            raise ValueError(f"Error parsing Excel file: {str(e)}")
    
    def _parse_pdf(self, filepath: str) -> pd.DataFrame:
        """
        Parse PDF files to extract payment data
        """
        self.logger.info("Extracting data from PDF...")
        
        payments = []
        
        # Try multiple methods
        try:
            # Method 1: Try pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Try to extract using regex patterns
                    payments.extend(self._extract_from_text(text, page_num + 1))
                    
            if payments:
                self.logger.info(f"Extracted {len(payments)} payments using pdfplumber")
                return pd.DataFrame(payments)
                
        except Exception as e:
            self.logger.debug(f"pdfplumber extraction failed: {str(e)}")
        
        try:
            # Method 2: Try PyPDF2
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        payments.extend(self._extract_from_text(text, page_num + 1))
            
            if payments:
                self.logger.info(f"Extracted {len(payments)} payments using PyPDF2")
                return pd.DataFrame(payments)
                
        except Exception as e:
            self.logger.debug(f"PyPDF2 extraction failed: {str(e)}")
        
        if not payments:
            raise ValueError("Could not extract payment data from PDF")
        
        return pd.DataFrame(payments)
    
    def _extract_from_text(self, text: str, page_num: int) -> List[Dict]:
        """Extract vendor names and amounts from text"""
        payments = []
        
        # Common patterns for vendor and amount
        patterns = [
            # Pattern: Vendor Name then Amount
            r'([A-Z][A-Za-z\s\.]+(?:Inc|Ltd|Corp|LLC|Pty|Technologies|Solutions|Services)?)\s+([\d,]+\.?\d*)\s*$',
            # Pattern: Amount then Vendor Name
            r'([\d,]+\.?\d*)\s+([A-Z][A-Za-z\s\.]+(?:Inc|Ltd|Corp|LLC|Pty|Technologies|Solutions|Services)?)\s*$',
            # Pattern: Invoice format
            r'(?:Invoice|Payment|Vendor|Supplier)[:\s]+([A-Z][A-Za-z\s\.]+)\s+(?:Amount|Total)[:\s]+([\d,]+\.?\d*)',
            # Pattern: Simple line
            r'([A-Z][A-Za-z\s\.]{3,30})\s+([\d,]+\.?\d{2})\s*$',
        ]
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        # Determine which is vendor and which is amount
                        if groups[0].replace(',', '').replace('.', '').replace(' ', '').isdigit():
                            amount = self._extract_amount(groups[0])
                            vendor = groups[1].strip()
                        else:
                            vendor = groups[0].strip()
                            amount = self._extract_amount(groups[1])
                        
                        if vendor and amount and len(vendor) > 2:
                            payments.append({
                                'payee_name': vendor,
                                'amount': amount,
                                'page': page_num
                            })
                            break  # Found a match, move to next line
        
        return payments
    
    def _extract_amount(self, value: Any) -> float:
        """Extract and convert amount to float"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.-]', '', value)
            try:
                return float(cleaned)
            except:
                return 0.0
        
        return 0.0
    
    def detect_file_format(self, filepath: str) -> Dict:
        """Analyze file and suggest column mapping"""
        ext = os.path.splitext(filepath)[1].lower()
        
        info = {
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath),
            'extension': ext,
            'recommended_parser': 'csv' if ext == '.csv' else 'excel' if ext in ['.xlsx', '.xls'] else 'pdf'
        }
        
        return info