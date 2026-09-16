"""Optional readouts are switched per session, not compiled in."""

from bioview_common import ExperimentConfiguration
from bioview_common.datatypes.configuration import FEATURE_DEFAULTS


def test_both_statistics_ship_enabled():
    config = ExperimentConfiguration({})
    assert config.get_feature("statistics_snr") is True
    assert config.get_feature("statistics_harmonics") is True


def test_a_configuration_file_can_turn_one_off():
    config = ExperimentConfiguration({"features": {"statistics_harmonics": False}})
    assert config.get_feature("statistics_harmonics") is False


def test_naming_one_flag_does_not_silently_disable_the_others():
    """The experiment block is built without merged_with_defaults, so a partial"""
    config = ExperimentConfiguration({"features": {"statistics_harmonics": False}})
    assert config.get_feature("statistics_snr") is True


def test_an_unknown_flag_is_off_rather_than_an_error():
    config = ExperimentConfiguration({})
    assert config.get_feature("statistics_telepathy") is False


def test_a_flag_flipped_at_runtime_holds_for_the_rest_of_the_session():
    config = ExperimentConfiguration({})
    config.set_feature("statistics_snr", False)

    assert config.get_feature("statistics_snr") is False
    assert FEATURE_DEFAULTS["statistics_snr"] is True


def test_the_flags_survive_a_round_trip_through_to_dict():
    config = ExperimentConfiguration({})
    config.set_feature("statistics_harmonics", False)

    restored = ExperimentConfiguration(config.to_dict())
    assert restored.get_feature("statistics_harmonics") is False
