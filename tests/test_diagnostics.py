"""The shared catalogue of recognised failures.

Both GUIs render errors through this, so an entry added here changes the
wording in the Monitor and the Configurator at once.
"""
import json
from pathlib import Path

import pytest

from bioview_common import describe_failure, explain, load_known_issues
from bioview_common.diagnostics import KnownIssue


CATALOGUE = (
    Path(__file__).resolve().parents[1]
    / "bioview_common"
    / "diagnostics"
    / "known_issues.json"
)


class TestCatalogueFile:
    def test_the_catalogue_ships_with_the_package(self):
        assert (
            CATALOGUE.is_file()
        ), "the JSON must be packaged, not just present in the repo"

    def test_every_entry_is_usable(self):
        raw = json.loads(CATALOGUE.read_text(encoding="utf-8"))
        assert raw["issues"], "an empty catalogue explains nothing"
        for entry in raw["issues"]:
            assert entry.get("id"), entry
            assert entry.get("summary"), entry["id"]
            assert entry.get(
                "action"
            ), f"{entry['id']} says what is wrong but not what to do"
            assert entry.get("match_any") or entry.get("match_all"), entry["id"]

    def test_ids_are_unique(self):
        ids = [i.id for i in load_known_issues()]
        assert len(ids) == len(set(ids))


class TestRecognisingFailures:
    def test_a_driver_blocked_by_memory_integrity_is_named_as_such(self):
        issue = explain("mp36usb.sys is not compatible with hypervisor enforcement")
        assert issue.id == "driver-blocked-by-memory-integrity"
        assert "memory integrity" in issue.action.lower()

    def test_memory_integrity_wins_over_the_generic_driver_error(self):
        """A blocked driver is also an MPDRVERR; the specific cause is the useful one."""
        issue = explain(
            "BIOPAC connection failed: MPDRVERR (code 2). Memory Integrity "
            "(hypervisor-enforced code integrity) is switched on"
        )
        assert issue.id == "driver-blocked-by-memory-integrity"

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("MPDRVERR (code 2)", "biopac-driver-not-responding"),
            ("MPDLLBUSY (code 3)", "biopac-unit-busy"),
            ("MPNOTCON (code 5)", "biopac-no-unit"),
            ("No module named 'wmi'", "backend-unavailable"),
            (
                "could not resolve the serial number for MyB210_7",
                "usrp-serial-unresolved",
            ),
            ("INITIALIZE_DEVICES timed out after 300s", "device-operation-timeout"),
        ],
    )
    def test_known_failures_are_recognised(self, text, expected):
        assert explain(text).id == expected

    def test_matching_ignores_case(self):
        assert explain("mpdrverr (code 2)") is not None

    @pytest.mark.parametrize("text", [None, "", "something nobody has seen before"])
    def test_an_unknown_error_is_not_forced_into_a_category(self, text):
        assert explain(text) is None


class TestDescribeFailure:
    def test_a_recognised_error_gains_a_cause_and_a_fix(self):
        described = describe_failure("MPDLLBUSY (code 3)")
        assert "Another program" in described
        assert "close" in described.lower()

    def test_the_servers_own_words_are_kept_alongside_the_explanation(self):
        described = describe_failure("MPDRVERR (code 2)")
        assert "MPDRVERR (code 2)" in described, "the raw error is still evidence"

    def test_the_original_can_be_left_out_when_it_would_only_repeat(self):
        described = describe_failure("MPDLLBUSY", include_original=False)
        assert "MPDLLBUSY" not in described

    def test_an_unknown_error_is_passed_through_untouched(self):
        assert describe_failure("weird failure 0x99") == "weird failure 0x99"

    def test_nothing_in_gives_nothing_out(self):
        assert describe_failure(None) == ""

    def test_a_non_string_error_is_accepted(self):
        assert "MPDRVERR" in describe_failure(RuntimeError("MPDRVERR (code 2)"))


class TestResilience:
    def test_an_unreadable_catalogue_does_not_break_error_reporting(self, monkeypatch):
        """Explanations are a convenience; losing them must not lose the error."""
        import bioview_common.diagnostics as diag

        monkeypatch.setattr(diag, "_CATALOGUE_PATH", Path("nonexistent.json"))
        monkeypatch.setattr(diag, "_cache", None)

        assert diag.load_known_issues(force_reload=True) == []
        assert diag.describe_failure("MPDRVERR") == "MPDRVERR"

    def test_an_entry_with_no_patterns_matches_nothing(self):
        assert not KnownIssue({"id": "x", "summary": "y"}).matches("anything")
