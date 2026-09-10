"""Server-level faults are turned into something a window can show, once."""

from bioview_common import server_diagnostics


def _info(**backends):
    return {"hostname": "lab-pc", "backends": backends}


def test_a_loaded_backend_is_not_a_diagnostic():
    assert server_diagnostics(_info(usrp={"available": True, "error": ""})) == []


def test_a_missing_uhd_is_explained_rather_than_echoed():
    (issue,) = server_diagnostics(
        _info(usrp={"available": False, "error": "No module named 'uhd'"})
    )

    assert issue["device_type"] == "usrp"
    assert issue["level"] == "error"
    assert "UHD" in issue["title"]
    assert "install" in issue["message"].lower()
    # The raw error is kept for a bug report, not shown as the explanation.
    assert issue["detail"] == "No module named 'uhd'"


def test_an_fpga_version_mismatch_is_recognised():
    (issue,) = server_diagnostics(
        _info(
            usrp={
                "available": False,
                "error": "RuntimeError: Expected FPGA compatibility number 40",
            }
        )
    )

    assert "FPGA" in issue["title"]
    assert "uhd_images_downloader" in issue["message"]


def test_an_unrecognised_reason_still_produces_a_usable_diagnostic():
    (issue,) = server_diagnostics(
        _info(biopac={"available": False, "error": "something odd happened"})
    )

    assert "BIOPAC" in issue["title"]
    assert "lab-pc" in issue["message"]
    assert issue["detail"] == "something odd happened"


def test_ids_are_stable_so_a_window_can_show_each_fault_once():
    payload = _info(usrp={"available": False, "error": "No module named 'uhd'"})
    first = server_diagnostics(payload)
    second = server_diagnostics(payload)

    assert [i["id"] for i in first] == [i["id"] for i in second]


def test_ids_distinguish_servers_and_backends():
    a = server_diagnostics(
        {"hostname": "a", "backends": {"usrp": {"available": False, "error": "x"}}}
    )
    b = server_diagnostics(
        {"hostname": "b", "backends": {"usrp": {"available": False, "error": "x"}}}
    )
    c = server_diagnostics(
        {"hostname": "a", "backends": {"biopac": {"available": False, "error": "x"}}}
    )

    assert len({a[0]["id"], b[0]["id"], c[0]["id"]}) == 3


def test_a_payload_with_no_backend_report_is_silent():
    """An older server says nothing about its backends; that is not a fault."""
    assert server_diagnostics({"hostname": "old"}) == []
    assert server_diagnostics(None) == []
    assert server_diagnostics({"backends": "not a mapping"}) == []


def test_every_unloadable_backend_is_reported():
    issues = server_diagnostics(
        _info(
            usrp={"available": False, "error": "no uhd"},
            biopac={"available": False, "error": "MPDRVERR"},
            microphone={"available": True},
        )
    )

    assert {i["device_type"] for i in issues} == {"usrp", "biopac"}
