import pytest

from core.loads import DistributedLoad, PointLoad, SupportType


def test_point_load_valid():
    pl = PointLoad(magnitude=1000, position=1.5)
    assert pl.magnitude == 1000
    assert pl.position == 1.5


def test_point_load_negative_rejected():
    with pytest.raises(Exception):
        PointLoad(magnitude=-1, position=1.0)
    with pytest.raises(Exception):
        PointLoad(magnitude=0, position=1.0)
    with pytest.raises(Exception):
        PointLoad(magnitude=100, position=-0.1)


def test_distributed_load_valid():
    dl = DistributedLoad(magnitude=2000, start=0.0, end=2.0)
    assert dl.magnitude == 2000


def test_distributed_load_bad_span():
    with pytest.raises(Exception):
        DistributedLoad(magnitude=2000, start=2.0, end=1.0)
    with pytest.raises(Exception):
        DistributedLoad(magnitude=2000, start=1.0, end=1.0)
    with pytest.raises(Exception):
        DistributedLoad(magnitude=-1, start=0, end=1)


def test_support_types_present():
    assert SupportType.SIMPLY_SUPPORTED.value == "simply_supported"
    assert SupportType.CANTILEVER.value == "cantilever"
