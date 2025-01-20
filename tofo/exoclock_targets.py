# -*- coding: UTF-8 -*-
# cSpell:ignore exoclock astropy
from functools import lru_cache

from astropy.time import Time

from tofo.sources.exoclock import ExoClock
from tofo.observatory import Observatory


class ExoClockTargets():
    """Collection of methods used to get exoplanet transits for a specific period."""
    
    def __init__(self, observatory: Observatory):
        """Initialise the object and load the exoclock data.

        Args:
            observatory (Observatory): Observatory used to perform observations.
        """
        self.observatory = observatory
        self.archive = ExoClock(self.observatory)
        self.targets = self.archive.get_telescope_filtered_targets()
        self.get_all_transits = lru_cache(maxsize=None)(self._get_all_transits)
        
    def _get_all_transits(self, time_start: Time, time_end: Time) -> list:
        """Return a list of all transits visible from the observatory between the start and end times.
        
        ..note:
            All calls to this function are cached since each call could take some time. The cache is a
            "forever cache" and is only dependent on the start and end times.

        Args:
            time_start (astropy.time.Time): Observation start time
            time_end (astropy.time.Time): Observation end time

        Returns:
            list: List of tuples. Each tuple has as first element an array with name, epoch, period and duration.
                The second element is the next transit time. They will all be visible between specified datetimes
                but they may not be visible at the observatory due to horizon limitations.
        """
        for exo in self.targets:
            exo.observation_time = time_start
            exo.observation_end_time = time_end
        return [t for t in self.targets if t.has_transits()]
