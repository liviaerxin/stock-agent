# config.py
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class Config:
    """Configuration handler for the application."""
    
    def __init__(self, config_path: str = None, stock_symbols_path: str=None):
        """
        Initialize configuration from JSON file.
        
        Args:
            config_path(str): Path to config file. If None, uses default location.
            stock_symbols_path(str): Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.json"
        
        if stock_symbols_path is None:
            stock_symbols_path = Path(__file__).parent.parent / "stock_symbols.json"
        
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        self.config_path = config_path
        self.stock_symbols_path = stock_symbols_path
        self.PERIOD: int = config_data["period"]
        self.NUM_NEWS: int = config_data["num_news"]
        self.FROM_EMAIL: str = config_data["from_email"]
        self.TO_EMAILS: List[str] = config_data["to_emails"]
        self.SMTP_SERVER: str = config_data["smtp_server"]
        self.LLM_MODEL: str = config_data["llm_model"]
        
        # Load stock symbols
        self.STOCK_SYMBOLS: Optional[List[str]] = self._load_stock_symbols()

        self.DATA_DIR: str = None

    def _load_stock_symbols(self) -> Optional[List[str]]:
        """Load stock symbols from JSON file if it exists."""        
        if os.path.exists(self.stock_symbols_path) and os.path.isfile(self.stock_symbols_path):
            with open(self.stock_symbols_path, "r") as f:
                return json.load(f)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "period": self.PERIOD,
            "num_news": self.NUM_NEWS,
            "from_email": self.FROM_EMAIL,
            "to_emails": self.TO_EMAILS,
            "smtp_server": self.SMTP_SERVER,
            "llm_model": self.LLM_MODEL,
            "stock_symbols": self.STOCK_SYMBOLS,
            "data_dir": self.DATA_DIR
        }

# Create a default instance for import
config = Config()

# Create `data` folder
_data_path = Path(__file__).parent.parent / "data"
_data_path.mkdir(parents=True, exist_ok=True)

config.DATA_DIR = _data_path.as_posix()