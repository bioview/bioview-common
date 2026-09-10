"""A config file that names one key of a nested block keeps the rest."""

from bioview_common import Configuration, USRPConfiguration
from bioview_common.datatypes.configuration.config import merged_with_defaults
from bioview_common.signal_schemes.calibration import BurstEnvelope


def test_partial_calibration_block_keeps_the_other_defaults():
    cfg = USRPConfiguration(
        {"calibration": {"enabled": True, "record_reference": False}}
    )
    calibration = cfg.get_param("calibration")

    assert calibration["enabled"] is True
    assert calibration["record_reference"] is False
    # Not mentioned by the config, so still the defaults rather than absent.
    assert calibration["num_pulses"] == 5
    assert calibration["pulse_duration_s"] == 0.1
    assert calibration["packet_spacing_s"] == 1.0
    assert calibration["shape"] == "triangle"


def test_burst_timings_are_editable_from_a_config_file():
    cfg = USRPConfiguration(
        {
            "calibration": {
                "num_pulses": 3,
                "pulse_duration_s": 0.02,
                "packet_spacing_s": 0.5,
            }
        }
    )
    calibration = cfg.get_param("calibration")

    assert calibration["num_pulses"] == 3
    assert calibration["pulse_duration_s"] == 0.02
    assert calibration["packet_spacing_s"] == 0.5
    # Everything else survived the partial block.
    assert calibration["modulation_depth"] == 0.2


def test_the_default_pulse_duration_matches_the_reference_envelope_frequency():
    """0.1 s is 1 / 10 Hz, so making the duration explicit changed nothing."""
    cfg = USRPConfiguration({})
    calibration = cfg.get_param("calibration")

    explicit = BurstEnvelope(
        fs=1000,
        num_pulses=calibration["num_pulses"],
        pulse_duration_s=calibration["pulse_duration_s"],
        packet_spacing_s=calibration["packet_spacing_s"],
        envelope_freq_hz=calibration["envelope_freq_hz"],
    )
    derived = BurstEnvelope(
        fs=1000,
        num_pulses=calibration["num_pulses"],
        pulse_duration_s=None,
        packet_spacing_s=calibration["packet_spacing_s"],
        envelope_freq_hz=calibration["envelope_freq_hz"],
    )

    assert explicit.pulse_freq_hz == derived.pulse_freq_hz
    assert explicit.burst_len == derived.burst_len


def test_the_timings_survive_a_round_trip_through_a_loaded_configuration():
    config = Configuration(
        {
            "RF": {
                "type": "USRP",
                "calibration": {"num_pulses": 7, "pulse_duration_s": 0.05},
            }
        }
    )
    calibration = config.devices["RF"].get_param("calibration")

    assert calibration["num_pulses"] == 7
    assert calibration["pulse_duration_s"] == 0.05
    assert calibration["packet_spacing_s"] == 1.0
    assert config.to_dict()["RF"]["calibration"]["num_pulses"] == 7


def test_a_non_dict_override_still_replaces_the_default():
    """Only dict-on-dict merges; anything else is a plain override."""
    assert merged_with_defaults({"a": {"x": 1}}, {"a": None}) == {"a": None}
    assert merged_with_defaults({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}


def test_defaults_the_config_does_not_mention_are_not_invented():
    """The merge only touches keys the config actually names."""
    assert merged_with_defaults({"a": 1, "b": 2}, {"b": 3}) == {"b": 3}
