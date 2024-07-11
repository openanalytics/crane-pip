# Allow self reference of TokenCache in the classmethod: https://stackoverflow.com/a/53450349
# Note that starting from 3.11 type annotations Self is allows as per PEP 637
from __future__ import annotations

from collections import UserDict
from datetime import datetime
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

@dataclass
class CraneTokens:
    "Token information for a given crane server."

    access_token: str
    access_token_exp_time: datetime
    refresh_token: str
    refresh_token_exp_time: datetime

    @classmethod
    def from_json(cls, cache: Dict[str, str]) -> CraneTokens:
        "Generate a TokenCache from a the read cache dictionary."
        return cls(
            access_token=cache["access_token"],
            access_token_exp_time=datetime.fromisoformat(cache["access_token_exp_time"]),
            refresh_token=cache["refresh_token"],
            refresh_token_exp_time=datetime.fromisoformat(cache["refresh_token_exp_time"]),
        )

    def to_json(self) -> Dict[str, str]:
        "Return dictionary to be stored in the json cache file"
        return {
            "access_token": self.access_token,
            "access_token_exp_time": self.access_token_exp_time.isoformat(),
            "refresh_token": self.refresh_token,
            "refresh_token_exp_time": self.refresh_token_exp_time.isoformat(),
        }

    def access_token_expired(self) -> bool:
        return self.access_token_exp_time < datetime.now()

    def refresh_token_expired(self) -> bool:
        return self.refresh_token_exp_time < datetime.now()

    def expired_but_can_refresh(self) -> bool:
        return self.access_token_expired() and not self.refresh_token_expired()

    def is_expired(self) -> bool:
        return self.access_token_expired() and self.refresh_token_expired()


class TokenCache(UserDict[str, CraneTokens]):
    """Dictionary with the cached crane server tokens. Key = crane server url, 
    
    Setting an item also writes away the the in-memory cached state to disk.

    Other modules should interact with the configs via the token_cache object 
    and do not directly access this class! Else multiple in-memory states will get out of sync.
    """

    cache_dir = os.path.join(Path.home(), ".cache", "crane", "python")
    os.makedirs(cache_dir, exist_ok=True)
    token_cache_file = os.path.join(cache_dir, "tokens.json")
    
    def __init__(self):
        with open(self.token_cache_file, "r") as f:
            self.data = {url: CraneTokens.from_json(tokens) for url, tokens in json.load(f)}

    def __setitem__(self, key: str, item: CraneTokens) -> None:
        self.data[key] = item
        self._write()

    def _write(self):
        "Write current in memory state of the cache to disk"
        to_write = {url: tokens.to_json() for url, tokens in self.data.items()}
        with open(self.token_cache_file, "w") as f:
            f.write(json.dumps(to_write))

token_cache = TokenCache()
