# cSpell:ignore exoclock
import sys
import cProfile
import pstats
from pathlib import Path
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from astropy.time import Time

sys.path.append("..")
from tofo.observatory import Observatory
from tofo.exoclock_targets import ExoClockTargets


def runme():
    """Fn to profile"""
    with open(Path("observatory.yaml"), "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    o = Observatory(obs_js)

    archive = ExoClockTargets(o)
    
    start_time = Time("2025-01-01 18:00")
    end_time = Time("2025-01-02 05:00")
    _ = archive.get_all_transits(start_time, end_time)
    
    start_time = Time("2025-01-10 18:00")
    end_time = Time("2025-01-11 05:00")
    _ = archive.get_all_transits(start_time, end_time)
    
    
if __name__ == '__main__':
    
    profiler = cProfile.Profile()
    profiler.enable()
    runme()
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.dump_stats('data_exoclock_targets.perf')
