# Allow self reference of Tokenkache in the classmethod: https://stackoverflow.com/a/53450349
# Note that starting from 3.11 type annotations Self is allows as per PEP 637
from __future__ import annotations

from collections import UserDict
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, TYPE_CHECKING


@dataclass
class ServerConfig:
    "Configuration for a given crane server."

    # Auth related stuff:
    client_id: str
    token_url: str
    device_url: str

    @classmethod
    def from_json(cls, config: Dict[str, str]) -> ServerConfig:
        return cls(**config)

    def to_json(self) -> Dict[str, str]:
        # Url is used as the key and thus not stored in the indivual config object itself.
        return {
            "client_id": self.client_id,
            "token_url": self.token_url,
            "device_url": self.device_url,
        }


# Starting from 3.9 this is not needed anymore: https://stackoverflow.com/a/72436468
if TYPE_CHECKING:
    TypedUserDict = UserDict[str, ServerConfig]
else:
    TypedUserDict = UserDict


class ServerConfigs(TypedUserDict):
    """A dictionary representing the stored crane server configs on disk. Key = crane server url,

    Setting an item also saves the config on disk.

    Other modules should interact with the configs via the server_configs object
    and do not directly access this class! Else multiple in-memory states will get out of sync.
    """

    config_dir = os.path.join(Path.home(), ".local", "share", "crane", "python")
    os.makedirs(config_dir, exist_ok=True)
    server_config_file = os.path.join(config_dir, "servers.json")

    def __init__(self):
        if not os.path.isfile(self.server_config_file):
            with open(self.server_config_file, "w") as f:
                f.write(json.dumps({}))
            self.data = {}
        else:
            with open(self.server_config_file, "r") as f:
                raw_data = json.load(f)
                self.data = {
                    url: ServerConfig.from_json(config) for url, config in raw_data.items()
                }

    def __setitem__(self, key: str, item: ServerConfig) -> None:
        self.data[key] = item
        self._write()

    def __delitem__(self, key) -> None:
        del self.data[key]
        self._write()

    def _write(self):
        "Write current in memory state of the config to disk"
        to_write = {url: tokens.to_json() for url, tokens in self.data.items()}
        with open(self.server_config_file, "w") as f:
            f.write(json.dumps(to_write))


server_configs = ServerConfigs()
