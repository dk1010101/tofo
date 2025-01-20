# -*- coding: UTF-8 -*-
# cSpell:ignore exoclock isot

import itertools

from io import StringIO
from typing import Dict, List
import json
import urllib

import astropy.units as u
from astropy.time import Time
from astropy.table import Table, Row

from tofo.targets import Target
from tofo.observatory import Observatory

from tofo.sources.source import Source
from tofo.sources.utils import fix_str_types


class ExoClock(Source):
    """Wrapper around Exoclock datasource"""
    name = 'exoclock'
    
    def __init__(self, observatory: Observatory, cache_life_days: float | None = None):
        super().__init__(observatory, cache_life_days)
        
        self.exoplanets_data: Table
        self.exoplanets: Dict[str, Target] = {}
        
        self._load_data()
        
    def _load_data(self) -> None:
        """Load data either from the cache or from online sources."""
        if self.needs_updating():
            # fetch new file and pickle it
            js_str = urllib.request.urlopen('https://www.exoclock.space/database/planets_json').read().decode()
            sio = StringIO(js_str)
            js = json.load(sio)
            common_keys = list(dict.fromkeys(itertools.chain.from_iterable(list(map(lambda c: list(c.keys()), js.values())))))
            v = {k: [dic.get(k, '') for dic in js.values()] for k in common_keys}
            self.exoplanets_data = Table(v, names=common_keys)
            fix_str_types(self.exoplanets_data)
            self.exoplanets_data.write(self.cache_file, path=self.name, append=True, overwrite=True)
            self.update_age()
        else:
            self.exoplanets_data = Table.read(self.cache_file, path=self.name)

        self.exoplanets = {}
        for exo in self.exoplanets_data:
            t = self._create_target(exo)
            self.exoplanets[exo['star']] = t
            self.exoplanets[exo['name']] = t

    def _create_target(self, exo: Row) -> Target:
        """Create a target from the table row."""
        t = Target(observatory=self.observatory, 
                       name=exo['name'],
                       star_name=exo['star'],
                       ra_j2000=exo['ra_j2000'],
                       dec_j2000=exo['dec_j2000'],
                       epoch=self._t_t(exo['ephem_mid_time'], exo['ephem_mid_time_format']),
                       period=exo['ephem_period'] * self._to_u(exo['ephem_period_units']),
                       duration=exo['duration_hours'] * u.hour,
                       eccentricity=exo['eccentricity'],
                       argument_of_periapsis=exo['periastron'] * self._to_u(exo['periastron_units']),
                       is_exoplanet=True) 
        return t
        
    def query_target(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        return self.exoplanets.get(name, None)

    def _to_u(self, exo_unit: str) -> u.Unit:
        if exo_unit == "Days":
            return u.day
        elif exo_unit == "Hours":
            return u.hour
        elif exo_unit == "Seconds":
            return u.second
        elif exo_unit == "Degrees":
            return u.deg
        elif exo_unit == "Radians":
            return u.rad
        else:
            raise ValueError(f"Unsupported unit: {exo_unit}")
        
    def _t_t(self, time_string: str, time_fmt: str) -> Time:
        fmt, scale = time_fmt.split("_")
        if fmt == "BJD" or fmt == "JD":
            f = "jd"
        elif fmt == "MJD":
            f = "mjd"
        else:
            raise ValueError(f"Unknown time format: {fmt}")
        s = scale.lower()
        if s == 'local':
            s = 'Local'
        return Time(time_string, format=f, scale=s, location=self.observatory.location)

    def get_telescope_filtered_targets(self) -> List[Target]:
        """Create a list of Targets that are all observable by the provided observatory."""
        aperture_inches: float = self.observatory.aperture.to(u.imperial.inch).value
        mask = self.exoplanets_data['min_telescope_inches'] <= aperture_inches
        possible_targets_data = self.exoplanets_data[mask]
        return [self._create_target(r) for r in possible_targets_data]
