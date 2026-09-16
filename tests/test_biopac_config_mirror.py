"""BIOPAC parameters live in two places and both have to be written."""

from bioview_common.datatypes.configuration.biopac import BiopacConfiguration


def _cfg():
    return BiopacConfiguration(
        {
            "model": "MP36",
            "samp_rate": 1000,
            "channels": [1, 1, 0, 0],
            "hardware": {"BIOPAC_MP36": {"channels": [1, 1, 0, 0]}},
        }
    )


def test_channels_reach_the_hardware_entry():
    cfg = _cfg()
    cfg.set_param("channels", [1, 1, 1, 1])

    assert cfg.get_param("channels") == [1, 1, 1, 1]
    assert cfg.hardware["BIOPAC_MP36"]["channels"] == [1, 1, 1, 1]
    assert cfg.get_channels()[:4] == [1, 1, 1, 1]


def test_channels_stay_in_step_with_absolute_channel_nums():
    cfg = _cfg()
    cfg.set_param("channels", [0, 0, 1, 1])
    assert cfg.absolute_channel_nums == [0, 0, 1, 1]


def test_sample_rate_reaches_the_hardware_entry():
    cfg = _cfg()
    cfg.set_param("samp_rate", 2000)
    assert cfg.hardware["BIOPAC_MP36"]["samp_rate"] == 2000


def test_model_change_updates_the_device_code():
    cfg = _cfg()
    cfg.set_param("model", "MP160")
    assert cfg.device_code == 160
    assert cfg.hardware["BIOPAC_MP36"]["model"] == "MP160"


def test_a_config_without_hardware_is_left_alone():
    cfg = BiopacConfiguration({"model": "MP36", "channels": [1, 0, 0, 0]})
    cfg.set_param("channels", [1, 1, 0, 0])
    assert cfg.get_param("channels") == [1, 1, 0, 0]
    assert cfg.get_param("hardware") is None


def test_unrelated_params_are_not_mirrored():
    cfg = _cfg()
    cfg.set_param("disp_ds", 5)
    assert "disp_ds" not in cfg.hardware["BIOPAC_MP36"]
