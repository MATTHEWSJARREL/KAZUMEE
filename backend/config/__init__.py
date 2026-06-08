import json
import os
from typing import Dict, Any

class Config:
    def __init__(self, config_file: str = "backend/config/config.json"):
        self.config_file = config_file
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def __getattr__(self, name: str) -> Any:
        return self._config.get(name)

# Global config instance
config = Config()
