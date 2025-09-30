"""
Configuration loader for Trade Sourcer
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any


class Config:
    """Configuration manager for the application"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config.yaml file
        """
        # Load environment variables
        load_dotenv()
        
        # Determine paths
        self.base_dir = Path(__file__).parent.parent.parent
        if config_path is None:
            config_path = self.base_dir / "config" / "config.yaml"
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Replace environment variables in config
        self._replace_env_vars(self.config)
    
    def _replace_env_vars(self, obj: Any) -> Any:
        """
        Recursively replace ${ENV_VAR} patterns with environment variables
        
        Args:
            obj: Object to process (dict, list, str, or other)
        
        Returns:
            Processed object
        """
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            return os.getenv(env_var, "")
        return obj
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'analysis.schedule_days')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access"""
        return self.get(key)
    
    @property
    def data_dir(self) -> Path:
        """Get data directory path"""
        return self.base_dir / "data"
    
    @property
    def reports_dir(self) -> Path:
        """Get reports directory path"""
        return self.base_dir / self.get('reporting.output_directory', 'reports')
    
    @property
    def cache_dir(self) -> Path:
        """Get cache directory path"""
        cache_path = self.base_dir / self.get('data_sources.cache_directory', 'data/cache')
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory path"""
        log_file = self.get('logging.log_file', 'logs/trade_sourcer.log')
        logs_path = self.base_dir / Path(log_file).parent
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path


# Global configuration instance
_config = None


def get_config(config_path: str = None) -> Config:
    """
    Get or create global configuration instance
    
    Args:
        config_path: Path to config.yaml file
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
