# -*- coding: UTF-8 -*-
# cSpell:ignore exoclock astropy
import copy
import time
from pathlib import Path
import urllib

import numpy as np
import pandas as pd

import astropy.units as u
import astropy.time as atime
from astropy.coordinates import SkyCoord
from astroplan import FixedTarget, EclipsingSystem, LocalTimeConstraint, is_event_observable

from tofo.observatory import Observatory


class ExoClock():
    """Collection of methods used to get exoplanet transits for a specific period."""
    
    def __init__(self, observatory: Observatory):
        """Initialise the object and load the exoclock data.

        Args:
            observatory (Observatory): Observatory used to perform observations.
        """
        self.observatory = observatory
        self.exoplanets: pd.DataFrame
        self.observable: list
        self.exo_simple: np.ndarray
        
        self._load_exoclock_data()
    
    def _load_exoclock_data(self) -> None:
        """Check local exoclock cache and if too old, get the new copy then load the lot in to memory."""
        p = Path(self.observatory.exoclock_file)
        if p.is_file():
            mod_time = p.stat().st_mtime
            age_days = (time.time() - mod_time) / (24*60*60) * u.day
        else:
            age_days = self.observatory.exoclock_file_life_day + 1

        if age_days > self.observatory.exoclock_file_life_day:
            # fetch new file and pickle it
            js_str = urllib.request.urlopen('https://www.exoclock.space/database/planets_json').read()
            df = pd.read_json(js_str)
            ndf = df.transpose()
            ndf.to_pickle(self.observatory.exoclock_file)
        else:
            ndf = pd.read_pickle(self.observatory.exoclock_file)
        # we can't do this earlier as the observatory may have changed
        mask = ndf['min_telescope_inches'] <= self.observatory.aperture.to(u.inch).value
        self.exoplanets = ndf[mask]
        self.exo_simple = self.exoplanets[['name', 'ephem_mid_time', 'ephem_period', 'duration_hours', 'ra_j2000', 'dec_j2000']].to_numpy()
        self.observable = [
            EclipsingSystem(primary_eclipse_time=atime.Time(e[1], format='jd'), 
                            orbital_period=e[2]*u.day, 
                            duration=e[3]*u.hour, 
                            name=e[0]) 
            for e in self.exo_simple]
            
    def get_all_transits(self, time_start: atime.Time, time_end: atime.Time) -> list:
        """Return a list of all transits visible from the observatory between the start and end times.

        Args:
            time_start (astropy.time.Time): Observation start time
            time_end (astropy.time.Time): Observation end time

        Returns:
            list: List of tuples. Each tuple has as first element an array with name, epoch, period and duration.
                The second element is the next transit time. They will all be visible between specified datetimes
                but they may not be visible at the observatory due to horizon limitations.
        """
        mtt = [o.next_primary_eclipse_time(time_start, n_eclipses=1) for o in self.observable]
        constraints = copy.deepcopy(self.observatory.constraints)
        constraints.append(LocalTimeConstraint(min=time_start.datetime.time(),
                                               max=time_end.datetime.time()))
        targets = [FixedTarget(SkyCoord(f"{obj[4]} {obj[5]}", unit=(u.hourangle, u.deg))) for obj in self.exo_simple]
        observables = [is_event_observable(constraints, self.observatory.observer, targets, times=midtransit_time) for midtransit_time in mtt]
                
        return [(name, t) for name, t, o in zip(self.exo_simple, mtt, observables) if o]
