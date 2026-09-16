import ipaddress
from importlib.metadata import version

import numpy as np

from bioview_common.utils import (
    apply_filter,
    emit_signal,
    get_app_info,
    get_cache_file,
    get_filter,
    get_ip,
    is_local_request,
    suppress_stdout,
)


def test_ip():
    try:
        ipaddress.ip_address(get_ip())
    except ValueError as e:
        raise AssertionError(f"Invalid IP address format: {e}") from e


def test_local_address():
    assert is_local_request("127.0.0.1"), "Local request misidentified as remote"
    assert is_local_request("192.168.1.10"), "LAN request misidentified as remote"
    assert is_local_request("10.0.0.5"), "LAN request misidentified as remote"
    assert is_local_request("0.0.0.0"), "Local request misidentified as remote"

    assert not is_local_request("8.8.8.8"), "Remote request misidentified as local"
    assert not is_local_request("not-an-ip"), "Malformed address must not be local"


def test_app_info():
    app_info = get_app_info()
    assert "hostname" in app_info, "Hostname not found"

    assert "name" in app_info, "Application name not found"
    assert app_info["name"] == "BioView", f"Invalid application {app_info['name']}"

    assert "version" in app_info, "Application version not found"
    assert app_info["version"] == version(
        "bioview_common"
    ), f"Invalid application version {app_info['version']}"


def test_suppress_stdout_and_emit_signal():
    with suppress_stdout():
        print("this should be suppressed")

    emit_signal(None)

    called = {"v": False}

    def cb(x):
        called["v"] = x

    emit_signal(cb, True)
    assert called["v"] is True


def test_get_cache_file_is_created_somewhere_writable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    assert get_cache_file("testfile.txt").exists()


def test_filtering_roundtrip():
    filt = get_filter([1, 100], 1000)
    data = np.random.randn(1000)
    filtered, _zf = apply_filter(data, filt)
    assert filtered.shape == data.shape
