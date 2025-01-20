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
from tofo.sources.exoclock import ExoClock


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
    g = ExoClock(obs, cache_life_days=10)
    yield g
    

def test_load(obs, archive):  # pylint:disable=redefined-outer-name
    assert archive.exoplanets_data
    assert archive.exoplanets
    
    a2 = ExoClock(obs, cache_life_days=10)
    
    assert archive.age_days < a2.age_days

    
def test_query_target(archive):  # pylint:disable=redefined-outer-name
    t = archive.query_target("CoRoT-2")
    assert t
    assert t.name == "CoRoT-2b"
    assert t.star_name == "CoRoT-2"
    assert t.ra_j2000 == "19:27:06.4944"
    assert t.dec_j2000 == "+01:23:01.357"
    assert t.epoch.jd == 2457683.44158
    assert t.period == 1.74299705 * u.day
    assert t.duration == 2.28 * u.hour
    assert t.eccentricity == 0.0
    
    t2 = archive.query_target("CoRoT-2b")
    assert t == t2


def test_telescope_filter(archive):  # pylint:disable=redefined-outer-name
    archive.observatory.aperture = 153.6 * u.mm  # smaller telescope, 6"
    targets = archive.get_telescope_filtered_targets()
    assert len(archive.exoplanets) > len(targets)
