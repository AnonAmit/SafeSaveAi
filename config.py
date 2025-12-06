import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "target_root": "D:\\APPLICATIONs",
    "size_unit": "GB", # GB or MB
    "theme": "Standard",
    "llm_mode": "none",  # none, cloud, local
    "cloud": {
        "provider": "openai", # openai, gemini
        "api_key": "",
        "model": "gpt-4o-mini"
    },
    "local": {
        "base_url": "http://localhost:11434/v1/chat/completions",
        "model": "llama3"
    }
}

class Config:
    def __init__(self):
        self._data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load config from file, creating it if missing."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    # Deep merge or update to ensure all keys exist
                    self._update_recursive(self._data, loaded)
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self.save()

    def _update_recursive(self, base: Dict, update: Dict):
        for k, v in update.items():
            if isinstance(v, dict) and k in base:
                self._update_recursive(base[k], v)
            else:
                base[k] = v

    def save(self):
        """Save current config to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    # Accessors
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()
    
    @property
    def target_root(self) -> str:
        return self._data.get("target_root", "D:\\APPLICATIONs")
    
    @target_root.setter
    def target_root(self, value: str):
        self._data["target_root"] = value
        self.save()

    @property
    def size_unit(self) -> str:
        return self._data.get("size_unit", "GB")

    @size_unit.setter
    def size_unit(self, value: str):
        self._data["size_unit"] = value
        self.save()

    @property
    def theme(self) -> str:
        return self._data.get("theme", "Standard")

    @theme.setter
    def theme(self, value: str):
        self._data["theme"] = value
        self.save()

    @property
    def llm_mode(self) -> str:
        return self._data.get("llm_mode", "none")

    @llm_mode.setter
    def llm_mode(self, value: str):
        self._data["llm_mode"] = value
        self.save()
    
    @property
    def cloud_config(self) -> Dict:
        return self._data.get("cloud", {})
    
    @property
    def local_config(self) -> Dict:
        return self._data.get("local", {})

# Singleton instance
cfg = Config()
