# -*- coding: UTF-8 -*-
# cSpell:ignore NGTS exos 
# pylint:disable=missing-function-docstring
from pathlib import Path
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import astropy.units as u
from astropy.time import Time

import pytest

from tofo.observatory import Observatory
from tofo.exoclock_targets import ExoClockTargets


# we have to manually take away 8 hours as Time is UTC by design
transits_times_names = [
    (Time("2025-01-01T16:00:00")+8*u.hour, Time("2025-01-02T06:00:00")+8*u.hour, set([
        'HAT-P-42b',
        'HAT-P-68b',
        'HD15906b',
        'HD93963Ac',
        'HD260655b',
        'K2-141b',
        'K2-405b',
        'KELT-24b',
        'LHS1478b',
        'LTT3780b',
        'NGTS-1b',
        'NGTS-10b',
        'TIC257060897b',
        'TOI-544b',
        'TOI-561b',
        'TOI-564b',
        'TOI-674b',
        'TOI-1442b',
        'TOI-1685b',
        'TOI-1693b',
        'TOI-2025b',
        'TOI-2445b',
        'TOI-2842b',
        'TOI-3629b',
        'TOI-4087b',
        'TOI-5704b',
        'V1298Tauc',
        'WASP-12b',
        'WASP-65b',
        'WASP-72b',
        'WASP-138b',
        'WASP-140b',
        'WASP-141b',
        'WASP-175b',
        'WASP-189b'])),
    (Time("2025-01-10T16:00:00")+8*u.hour, Time("2025-01-11T06:00:00")+8*u.hour, set([
        '55Cnce',
        'EPIC211945201b',
        'G9-40b',
        'GJ436b',
        'GJ3473b',
        'GJ9827d',
        'HAT-P-30b',
        'HAT-P-56b',
        'HAT-P-62b',
        'HAT-P-68b',
        'HATS-38b',
        'HD63935b',
        'HD86226c',
        'HD191939b',
        'HD219134b',
        'K2-30b',
        'K2-370b',
        'KELT-1b',
        'KELT-3b',
        'KELT-18b',
        'LHS1678c',
        'LP791-18b',
        'LTT1445Ac',
        'NGTS-6b',
        'NGTS-10b',
        'Qatar-9b',
        'TOI-431b',
        'TOI-530b',
        'TOI-561b',
        'TOI-778b',
        'TOI-1181b',
        'TOI-1442b',
        'TOI-1693b',
        'TOI-1728b',
        'TOI-1807b',
        'TOI-1820b',
        'TOI-2445b',
        'TOI-3819b',
        'TOI-4145Ab',
        'TOI-4603b',
        'WASP-42b',
        'WASP-53b',
        'WASP-71b',
        'WASP-72b',
        'WASP-93b',
        'WASP-140b',
        'WASP-159b',
        'WASP-161b',
        'WASP-167b',
        'WASP-171b',
        'XO-7b'])),
]

@pytest.fixture
def obs(shared_datadir):
    with open(shared_datadir / "observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    o = Observatory(obs_js)
    o.sources_cache_file_name = shared_datadir / o.sources_cache_file_name
    yield o


@pytest.fixture
def archive(obs):  # pylint:disable=redefined-outer-name

    e = ExoClockTargets(obs)
    yield e


@pytest.mark.parametrize("start_time,end_time,exos", transits_times_names)
def test_get_all_transits(archive, start_time, end_time, exos):  # pylint:disable=redefined-outer-name
    transits = archive.get_all_transits(start_time, end_time)
    assert len(transits) == len(exos)
    assert exos == set([t.name for t in transits])
