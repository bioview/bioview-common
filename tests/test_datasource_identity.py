"""A source says what it *is* over the wire, not only what it is called."""

from bioview_common import DataSource


def test_a_plain_source_serializes_exactly_as_it_did():
    """Older readers and saved display-source lists must keep working."""
    source = DataSource(group_id="USRP1", channel=0, label="Ch1", disp_freq=1000.0)
    assert source.to_dict() == {
        "group_id": "USRP1",
        "channel": 0,
        "label": "Ch1",
        "disp_freq": 1000.0,
    }


def test_the_tx_and_rx_a_row_came_from_survive_the_round_trip():
    source = DataSource(group_id="USRP1", channel=3, label="Tx2Rx1")
    source.tx_idx = 1
    source.rx_idx = 0
    source.tx_label = 2
    source.rx_label = 1
    source.component = "phase"

    restored = DataSource.from_dict(source.to_dict())

    assert (restored.tx_idx, restored.rx_idx) == (1, 0)
    assert (restored.tx_label, restored.rx_label) == (2, 1)
    assert restored.component == "phase"
    assert restored.is_cal_ref is False


def test_a_calibration_reference_is_identifiable_as_one():
    """Not by its label: the client must be able to exclude it from the channel"""
    source = DataSource(group_id="USRP1", channel=4, label="CalRef_Tx1")
    source.tx_idx = 0
    source.rx_idx = -1
    source.is_cal_ref = True

    restored = DataSource.from_dict(source.to_dict())

    assert restored.is_cal_ref is True
    assert restored.tx_idx == 0


def test_identity_is_still_group_and_channel_only():
    """Sources are dict keys for routing; the new fields must not split one."""
    a = DataSource(group_id="USRP1", channel=0, label="Tx1Rx1")
    b = DataSource(group_id="USRP1", channel=0, label="Tx1Rx1")
    a.tx_idx, b.tx_idx = 0, 7

    assert a == b
    assert len({a, b}) == 1


def test_a_source_the_backend_built_pairs_with_its_reference():
    """The end-to-end shape the statistics panel relies on."""
    from bioview_common.datatypes.configuration.usrp_channel_map import (
        resolve_channel_map,
    )

    hardware = {
        "radio": {
            "tx_channels": [0, 1],
            "rx_channels": [0, 1],
            "if_freq": [100e3, 110e3],
        }
    }
    sources, _registry, _pairs = resolve_channel_map("USRP1", None, hardware)

    cal_ref = DataSource(group_id="USRP1", channel=len(sources), label="CalRef_Tx2")
    cal_ref.tx_idx = 1
    cal_ref.is_cal_ref = True

    wire = [s.to_dict() for s in sorted(sources, key=lambda s: s.channel)]
    wire.append(cal_ref.to_dict())
    restored = [DataSource.from_dict(d) for d in wire]

    references = {s.tx_idx: s for s in restored if s.is_cal_ref}
    driven_by_tx2 = [s for s in restored if not s.is_cal_ref and s.tx_idx in references]

    assert references.keys() == {1}
    assert {s.label for s in driven_by_tx2} == {"Tx2Rx1", "Tx2Rx2"}
