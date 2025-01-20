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
from tofo.sources.gcvs import GCVS

@pytest.fixture
def obs(shared_datadir):
    with open(shared_datadir / "observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    obervatory = Observatory(obs_js)
    obervatory.sources_cache_file_name = (Path(shared_datadir) / Path(obervatory.sources_cache_file_name)).as_posix()
    yield obervatory
    # cleanup here (eventually)
    
    
@pytest.fixture
def gcvs(obs):  # pylint:disable=redefined-outer-name
    g = GCVS(obs, cache_life_days=10)
    yield g
    

def test_load(gcvs):  # pylint:disable=redefined-outer-name
    assert gcvs.exoplanets_data
    assert gcvs.exoplanets
    

def test_load_multiple(obs, gcvs):   # pylint:disable=redefined-outer-name
    
    gcvs2 = GCVS(obs, cache_life_days=10)
    
    assert gcvs.age_days < gcvs2.age_days


def test_query_target(gcvs):  # pylint:disable=redefined-outer-name
    t = gcvs.query_target("X Ari")
    assert t
    assert t.name == "X Ari"
    assert t.ra_j2000 == "03:08:30.9"
    assert t.dec_j2000 == "+10:26:45.2"
    assert t.epoch.jd == 2452894.804
    assert t.period == 0.6511628 * u.day
    assert t.duration == 0.6511628 * 13.0 / 100.0 * u.day
