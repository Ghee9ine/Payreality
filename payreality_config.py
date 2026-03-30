"""
PayReality Configuration Module
Settings management, logging configuration, and validation
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class PayRealityConfig:
    def __init__(self, config_file: str = "payreality_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.setup_logging()
        self.validate_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        default_config = {
            'version': '1.0.0',
            'matching': {
                'threshold': 80,
                'use_phonetic': True,
                'batch_size': 10000,
                'name_cleaning': {
                    'lowercase': True,
                    'remove_punctuation': True,
                    'strip_suffixes': True,
                    'remove_common_words': True,
                    'suffixes': ['ltd', 'inc', 'corp', 'llc', 'pty', 
                                'technologies', 'solutions', 'group', 
                                'holdings', 'international', 'systems']
                }
            },
            'reporting': {
                'company_name': 'AI Securewatch',
                'client_name': 'Client',
                'logo_path': None,
                'output_format': 'pdf',
                'include_methodology': True,
                'include_recommendations': True,
                'max_exceptions_in_report': 20
            },
            'security': {
                'delete_files_after_processing': False,
                'encrypt_reports': False,
                'audit_logging': True,
                'hash_data': True
            },
            'processing': {
                'batch_size': 10000,
                'max_file_size_mb': 500,
                'timeout_seconds': 3600,
                'memory_limit_mb': 1024
            },
            'output': {
                'default_directory': None,
                'save_logs': True,
                'save_exceptions': True,
                'save_full_results': False
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Update default with loaded values
                    self._deep_update(default_config, loaded)
                    self.logger = logging.getLogger('PayReality')
                    print(f"✓ Loaded configuration from {self.config_file}")
            except Exception as e:
                print(f"⚠ Error loading config: {e}")
                print("Using default configuration")
        
        return default_config
    
    def _deep_update(self, target: Dict, source: Dict):
        """Recursively update nested dictionaries"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            return False
    
    def setup_logging(self):
        """Setup professional logging with file rotation"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"payreality_{datetime.now().strftime('%Y%m%d')}.log")
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('PayReality')
        self.logger.info(f"✓ Logging initialized: {log_file}")
    
    def validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Validate matching threshold
        threshold = self.get('matching.threshold', 80)
        if not 0 <= threshold <= 100:
            errors.append("matching.threshold must be between 0 and 100")
        
        # Validate batch size
        batch_size = self.get('processing.batch_size', 10000)
        if batch_size < 100 or batch_size > 100000:
            errors.append("processing.batch_size should be between 100 and 100000")
        
        # Validate max file size
        max_size = self.get('processing.max_file_size_mb', 500)
        if max_size < 1 or max_size > 10000:
            errors.append("processing.max_file_size_mb should be between 1 and 10000")
        
        if errors:
            for error in errors:
                self.logger.warning(f"Config validation: {error}")
        
        return len(errors) == 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
                if value is None:
                    return default
            return value
        except (KeyError, TypeError, AttributeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        try:
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
            return True
        except (KeyError, TypeError):
            return False
    
    def get_output_directory(self) -> str:
        """Get the output directory, with fallback to desktop"""
        output_dir = self.get('output.default_directory')
        
        if output_dir and os.path.exists(output_dir):
            return output_dir
        
        # Fallback to desktop
        desktop = Path.home() / 'Desktop' / 'PayReality_Reports'
        desktop.mkdir(exist_ok=True)
        return str(desktop)