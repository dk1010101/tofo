# pylint:disable=missing-function-docstring
from pathlib import Path
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import astropy.units as u

import pytest

from tofo.observatory import Observatory
from tofo.sources.aavso import VSX


@pytest.fixture
def obs(shared_datadir):
    with open(shared_datadir / "observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    obervatory = Observatory(obs_js)
    obervatory.sources_cache_file_name = (Path(shared_datadir) / Path(obervatory.sources_cache_file_name)).as_posix()
    yield obervatory
    # cleanup here (eventually)

def test_create_no_cld(obs):  # pylint:disable=redefined-outer-name
    archive = VSX(obs)
    assert archive.cache_life_days == float(obs.sources[VSX.name]['cache_life_days']) * u.day


def test_load(obs):  # pylint:disable=redefined-outer-name
    archive = VSX(obs, cache_life_days=10)
    assert len(archive.exoplanets_data) == 0
    assert archive.exoplanets == {}

    
def test_query_target(obs):  # pylint:disable=redefined-outer-name
    archive = VSX(obs, cache_life_days=10)
    t = archive.query_target("HAT-P-42")
    assert t
    assert t.name == "HAT-P-42"
    assert t.ra_j2000 == '09:01:22.6'
    assert t.dec_j2000 == '+6:05:50.0'
    assert t.epoch.jd == 2455952.526
    assert t.period == 4.641878 * u.day
    assert t.duration == 3.62 * u.hour
    
    assert len(archive.exoplanets_data) == 1
    
    a2 = VSX(obs, cache_life_days=10)
    t2 = a2.query_target("HAT-P-42")
    assert t == t2
