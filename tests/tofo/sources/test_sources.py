# pylint:disable=missing-function-docstring
from pathlib import Path
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import pytest

from tofo.observatory import Observatory
from tofo.sources.aavso import VSX
from tofo.sources.exoclock import ExoClock
from tofo.sources.gcvs import GCVS
from tofo.sources.nasa_exo import NasaExoArchive


@pytest.fixture
def obs(shared_datadir):
    with open(shared_datadir / "observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    obervatory = Observatory(obs_js)
    obervatory.sources_cache_file_name = (Path(shared_datadir) / Path(obervatory.sources_cache_file_name)).as_posix()
    yield obervatory
    # cleanup here (eventually)


def test_load_all(obs):  # pylint:disable=redefined-outer-name
    """Test that they all work happily together..."""
    vsx = VSX(obs, cache_life_days=10)
    exc = ExoClock(obs, cache_life_days=10)
    gcvs = GCVS(obs, cache_life_days=10)
    narc = NasaExoArchive(obs, cache_life_days=10)
    
    vsx_t = vsx.query_target("HAT-P-42")
    exc_t = exc.query_target("CoRoT-2")
    gcvs_t = gcvs.query_target("X Ari")
    narc_t = narc.query_target("AU Mic")
    
    vsx2 = VSX(obs, cache_life_days=10)
    exc2 = ExoClock(obs, cache_life_days=10)
    gcvs2 = GCVS(obs, cache_life_days=10)
    narc2 = NasaExoArchive(obs, cache_life_days=10)
    
    vsx_t2 = vsx2.query_target("HAT-P-42")
    exc_t2 = exc2.query_target("CoRoT-2")
    gcvs_t2 = gcvs2.query_target("X Ari")
    narc_t2 = narc2.query_target("AU Mic")
    
    assert vsx_t == vsx_t2
    assert exc_t == exc_t2
    assert gcvs_t == gcvs_t2
    assert narc_t == narc_t2
