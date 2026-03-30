"""
PayReality Configuration Module
Settings management and logging configuration
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

class PayRealityConfig:
    def __init__(self, config_file: str = "payreality_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        default_config = {
            'matching': {
                'threshold': 80,
                'use_phonetic': True,
                'name_cleaning': {
                    'lowercase': True,
                    'remove_punctuation': True,
                    'strip_suffixes': True,
                    'suffixes': ['ltd', 'inc', 'corp', 'llc', 'pty', 'technologies', 'solutions']
                }
            },
            'reporting': {
                'company_name': 'AI Securewatch',
                'client_name': 'Client',
                'logo_path': None,
                'output_format': 'pdf'
            },
            'security': {
                'delete_files_after_processing': True,
                'encrypt_reports': False,
                'audit_logging': True
            },
            'processing': {
                'batch_size': 10000,
                'max_file_size_mb': 500
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
                    print(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_logging(self):
        """Setup professional logging"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"payreality_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('PayReality')
        self.logger.info(f"Logging initialized: {log_file}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default