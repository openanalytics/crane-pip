# Allow self reference of TokenCache in the classmethod: https://stackoverflow.com/a/53450349
# Note that starting from 3.11 type annotations Self is allows as per PEP 637
from __future__ import annotations

from collections import UserDict
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

@dataclass
class CraneConfig:
    "Crane configuration for a givne index."

    client_id: str
    token_url: str
    device_code_url: str

    @classmethod
    def parse(cls, config: Dict[str, str]) -> CraneConfig:
        "Generate a IndexConfig from a the read config dictionary."
        return cls(**config)

    def serialize(self) -> Dict[str, str]:
        "Return dictionary to be stored in the json cache file"
        return {
            "client_id": self.client_id,
            "token_url": self.token_url,
            "device_code_url": self.device_code_url,
        }

class Config(UserDict[str, CraneConfig]):
    """Configuration for the registred indexes.
    
    Setting a config item also writes away the the in-memory config state to disk.
    """
    config_dir = os.path.join(Path.home(), ".cache", "crane", "python")
    os.makedirs(config_dir, exist_ok=True)
    index_config_file = os.path.join(config_dir, "tokens.json")
    
    def __init__(self):
        with open(self.index_config_file, "r") as f:
            self.data = {url: CraneConfig.parse(config) for url, config in json.load(f)}

    def __setitem__(self, key: str, item: CraneConfig) -> None:
        self.data[key] = item
        self._write()

    def _write(self):
        "Write current in memory state of the config to disk"
        to_write = {url: tokens.serialize() for url, tokens in self.data.items()}
        with open(self.index_config_file, "w") as f:
            f.write(json.dumps(to_write))

config = Config()
