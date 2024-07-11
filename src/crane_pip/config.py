# Allow self reference of Tokenkache in the classmethod: https://stackoverflow.com/a/53450349
# Note that starting from 3.11 type annotations Self is allows as per PEP 637
from __future__ import annotations

from collections import UserDict
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

@dataclass
class CraneServerConfig:
    "Configuration for a given crane server."

    # Auth related stuff:
    client_id: str
    token_url: str
    device_code_url: str

    @classmethod
    def from_json(cls, config: Dict[str, str]) -> CraneServerConfig:
        return cls(**config)

    def to_json(self) -> Dict[str, str]:
        # Url is used as the key and thus not stored in the indivual config object itself.
        return {
            "client_id": self.client_id,
            "token_url": self.token_url,
            "device_code_url": self.device_code_url,
        }

class CraneServerConfigs(UserDict[str, CraneServerConfig]):
    """A dictionary representing the stored crane server configs on disk. Key = crane server url, 
    
    Setting an item also saves the config on disk.

    Other code should not directly create this object but rather use the already 
    initilized `crane_configs` object in this module.
    """
    config_dir = os.path.join(Path.home(), ".kache", "crane", "python")
    os.makedirs(config_dir, exist_ok=True)
    index_config_file = os.path.join(config_dir, "tokens.json")
    
    def __init__(self):
        with open(self.index_config_file, "r") as f:
            self.data = {url: CraneServerConfig.from_json(config) for url, config in json.load(f)}

    def __setitem__(self, key: str, item: CraneServerConfig) -> None:
        self.data[key] = item
        self._write()

    def _write(self):
        "Write current in memory state of the config to disk"
        to_write = {url: tokens.to_json() for url, tokens in self.data.items()}
        with open(self.index_config_file, "w") as f:
            f.write(json.dumps(to_write))

crane_configs = CraneServerConfigs()
