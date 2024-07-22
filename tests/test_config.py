import os
import json
from typing import Tuple
from pytest import fixture
from crane_pip.config import ServerConfigs, ServerConfig


@fixture
def tmp_server_config_file(tmpdir) -> str:
    "Make config module save configs in a temporary configs.json file. This file is returned"
    config_file = os.path.join(tmpdir, "configs.json")
    ServerConfigs.server_config_file = config_file
    return config_file


@fixture
def tmp_server_configs(tmp_server_config_file) -> ServerConfigs:
    return ServerConfigs()


@fixture
def configs() -> Tuple[ServerConfig, ServerConfig]:
    # Test items
    config1 = ServerConfig(client_id="client1", token_url="token_url1", device_url="device_url1")
    config2 = ServerConfig(client_id="client2", token_url="token_url2", device_url="device_url2")
    return config1, config2


@fixture
def tmp_server_configs_prefilled(tmp_server_configs, configs) -> ServerConfigs:
    """Fill up a tmp config server_configs. Then return a newly created server_configs object to test on."""
    tmp_server_configs["url1"] = configs[0]
    tmp_server_configs["url2"] = configs[1]

    with open(tmp_server_configs.server_config_file, "r") as f:
        stored_on_disk = json.load(f)

    assert "url1" in stored_on_disk
    assert "url2" in stored_on_disk
    return ServerConfigs()


def test_crane_configs():
    raw = json.loads("""
        {
            "client_id":"client1",
            "token_url": "token_url1",
            "device_url":"device_url1"
        }""")
    parsed_config = ServerConfig.from_json(raw)
    assert isinstance(parsed_config, ServerConfig)
    assert parsed_config.client_id == "client1"
    assert parsed_config.token_url == "token_url1"
    assert parsed_config.device_url == "device_url1"

    serialized = parsed_config.to_json()
    assert raw == serialized


def test_initial_server_configs(tmp_server_configs: ServerConfigs, configs):
    assert len(tmp_server_configs) == 0, "starts empty"

    with open(tmp_server_configs.server_config_file, "r") as f:
        stored_on_disk = json.load(f)
    assert stored_on_disk == {}

    tmp_server_configs["url1"] = configs[0]

    assert "url1" in tmp_server_configs, "tmp_server_configs acts as a dictionary"
    assert tmp_server_configs["url1"] == configs[0], "tmp_server_configs acts as a dictionary"

    with open(tmp_server_configs.server_config_file, "r") as f:
        stored_on_disk = json.load(f)

    assert "url1" in stored_on_disk, "Assigning also writes to disk"
    assert stored_on_disk["url1"] == configs[0].to_json(), "Correct json is stored on disk"


def test_existing_server_configs(tmp_server_configs_prefilled: ServerConfigs, configs):
    server_configs = tmp_server_configs_prefilled
    assert len(server_configs) == 2, "Existing server_configs is read correctly"
    assert (
        "url1" in server_configs and "url2" in server_configs
    ), "Existing server_configs is read correctly"
    assert server_configs.get("url1") == configs[0]
    assert server_configs["url2"] == configs[1]
    assert (
        server_configs.get("url3") == None
    ), "get operation works as expected on server_configs object"


def test_deletion_of_server_configs(tmp_server_configs_prefilled: ServerConfigs):
    server_configs = tmp_server_configs_prefilled
    del server_configs["url1"]

    assert len(server_configs) == 1 and "url2" in server_configs

    with open(server_configs.server_config_file, "r") as f:
        stored_on_disk = json.load(f)

    assert len(stored_on_disk) == 1 and "url2" in stored_on_disk
    assert stored_on_disk["url2"] == server_configs["url2"].to_json()


def test_update_of_server_configs(tmp_server_configs_prefilled: ServerConfigs):
    server_configs = tmp_server_configs_prefilled
    server_configs["url1"] = server_configs["url2"]

    assert len(server_configs) == 2 and "url2" in server_configs and "url1" in server_configs

    assert server_configs["url1"].client_id == "client2"

    with open(server_configs.server_config_file, "r") as f:
        stored_on_disk = json.load(f)

    assert len(stored_on_disk) == 2
    assert stored_on_disk["url1"] == server_configs["url2"].to_json()
