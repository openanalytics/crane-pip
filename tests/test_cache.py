from datetime import datetime, timedelta
import os
import json
from typing import Tuple
from pytest import fixture 
from crane_pip.cache import CraneTokens, TokenCache

@fixture
def tmp_token_cache_file(tmpdir) -> str:
    "Make cache module save tokens in a temporary tokens.json file. This file is returned"
    token_cache_file = os.path.join(tmpdir, "tokens.json")
    TokenCache.token_cache_file = token_cache_file
    return token_cache_file 

@fixture
def tmp_cache(tmp_token_cache_file) -> TokenCache:
   return TokenCache() 


@fixture
def tokens() -> Tuple[CraneTokens, CraneTokens]:
    # Test items
    token1 = CraneTokens(
        access_token="token1",
        access_token_exp_time=datetime.now() + timedelta(minutes=5),
        refresh_token="refresh_token1",
        refresh_token_exp_time=datetime.now() + timedelta(days=30)
    )
    token2 = CraneTokens(
        access_token="token2",
        access_token_exp_time=datetime.now() + timedelta(minutes=5),
        refresh_token="refresh_token2",
        refresh_token_exp_time=None
    )
    return token1, token2

@fixture
def tmp_cache_prefilled(tmp_cache, tokens) -> TokenCache:
    """Fill up a tmp token cache. Then return a newly created cache object to test on."""
    tmp_cache["url1"] = tokens[0]
    tmp_cache["url2"] = tokens[1]
    
    with open(tmp_cache.token_cache_file, "r") as f:
       stored_on_disk = json.load(f) 

    assert "url1" in stored_on_disk
    assert "url2" in stored_on_disk
    return TokenCache()

def test_crane_tokens():

    raw = json.loads('''
        {
            "access_token":"token1",
            "access_token_exp_time": "2024-01-01T00:00:00",
            "refresh_token":"refresh_token1",
            "refresh_token_exp_time": "2024-03-01T00:00:00"
        }''')
    parsed_token = CraneTokens.from_json(raw)
    assert isinstance(parsed_token, CraneTokens)
    assert parsed_token.access_token == 'token1'
    assert parsed_token.access_token_exp_time == datetime.fromisoformat("2024-01-01T00:00:00")
    assert parsed_token.refresh_token == 'refresh_token1'
    assert parsed_token.refresh_token_exp_time == datetime.fromisoformat("2024-03-01T00:00:00")

    serialized = parsed_token.to_json()
    assert raw == serialized

    raw = json.loads('''
        {
            "access_token":"token2",
            "access_token_exp_time": "2024-01-01T00:00:00",
            "refresh_token":"refresh_token2"
        }''')
    parsed_token = CraneTokens.from_json(raw)
    assert parsed_token.refresh_token_exp_time is None

    serialized = parsed_token.to_json()
    assert raw == serialized


def test_initial_cache(tmp_cache: TokenCache, tokens):

    assert len(tmp_cache) == 0, "starts empty"

    with open(tmp_cache.token_cache_file, "r") as f:
       stored_on_disk = json.load(f) 
    assert stored_on_disk == {}
    
    tmp_cache["url1"] = tokens[0]

    assert "url1" in tmp_cache, "tmp_cache acts as a dictionary"
    assert tmp_cache["url1"] == tokens[0], "tmp_cache acts as a dictionary"

    with open(tmp_cache.token_cache_file, "r") as f:
       stored_on_disk = json.load(f) 

    assert "url1" in stored_on_disk, "Assigning also writes to disk"
    assert stored_on_disk["url1"] == tokens[0].to_json(), "Correct json is stored on disk"

def test_existing_cache(tmp_cache_prefilled: TokenCache, tokens):

    cache = tmp_cache_prefilled
    assert len(cache) == 2, "Existing cache is read correctly"
    assert "url1" in cache and "url2" in cache, "Existing cache is read correctly"
    assert cache.get("url1") == tokens[0]
    assert cache["url2"] == tokens[1]
    assert cache.get('url3') == None, "get operation works as expected on cache object"


def test_deletion_of_cache(tmp_cache_prefilled: TokenCache):

    cache = tmp_cache_prefilled
    del cache["url1"]

    assert len(cache)==1 and "url2" in cache

    with open(cache.token_cache_file, "r") as f:
       stored_on_disk = json.load(f) 
    
    assert len(stored_on_disk)==1 and "url2" in stored_on_disk
    assert stored_on_disk["url2"] == cache["url2"].to_json()

def test_update_of_cache(tmp_cache_prefilled: TokenCache):
    cache = tmp_cache_prefilled
    cache["url1"] = cache['url2']

    assert len(cache)==2 and "url2" in cache and "url1" in cache

    assert cache['url1'].access_token == "token2"
    
    with open(cache.token_cache_file, "r") as f:
       stored_on_disk = json.load(f) 
    
    assert len(stored_on_disk)==2 
    assert stored_on_disk["url1"] == cache["url2"].to_json()
