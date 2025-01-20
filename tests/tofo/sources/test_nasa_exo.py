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
from tofo.sources.nasa_exo import NasaExoArchive


@pytest.fixture
def obs(shared_datadir):
    with open(shared_datadir / "observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    obervatory = Observatory(obs_js)
    obervatory.sources_cache_file_name = (Path(shared_datadir) / Path(obervatory.sources_cache_file_name)).as_posix()
    yield obervatory
    # cleanup here (eventually)
    
    
@pytest.fixture
def archive(obs):  # pylint:disable=redefined-outer-name
    g = NasaExoArchive(obs, cache_life_days=10)
    yield g
    

def test_load(obs, archive):  # pylint:disable=redefined-outer-name
    assert archive.exoplanets_data
    assert archive.exoplanets
    
    a2 = NasaExoArchive(obs, cache_life_days=10)
    
    assert archive.age_days < a2.age_days

    
def test_query_target(archive):  # pylint:disable=redefined-outer-name
    t = archive.query_target("AU Mic")
    assert t
    assert t.name == "AU Mic"
    assert t.ra_j2000 == 311.2911369
    assert t.dec_j2000 == -31.34245
    assert t.epoch.jd == 2458342.224
    assert t.period == 18.85969 * u.day
    assert t.duration == 4.236 * u.hour
    assert t.eccentricity == 0.00338

    t2 = archive.query_target("HD 197481")
    t3 = archive.query_target("HIP 102409")
    t4 = archive.query_target("TIC 441420236")
    t5 = archive.query_target("Gaia DR2 6794047652729201024")
    
    assert t == t2 == t3 == t4 == t5
