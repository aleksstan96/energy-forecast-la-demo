from simulation.zones import TERNA_LOAD, ZONES, meteologica_area


def test_every_zone_has_a_terna_name():
    assert set(TERNA_LOAD) == set(ZONES)
    assert len(set(TERNA_LOAD.values())) == len(ZONES)


def test_meteologica_area_label():
    assert meteologica_area("CNOR") == "Italy CNOR"
