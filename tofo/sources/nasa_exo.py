# -*- coding: UTF-8 -*-
# cSpell:ignore tranmid trandur orbeccen votable isot

from io import BytesIO
from typing import Dict, Any

import requests

import numpy as np

import astropy.units as u
from astropy.time import Time
from astropy.table import Table

from tofo.target import Target
from tofo.observatory import Observatory

from tofo.sources.source import Source
from tofo.sources.utils import fix_str_types


class NasaExoArchive(Source):
    """Wrapper around nasa exoplanet archive datasource.
    
    Uses TAP to get the latest dataset. This is a large dataset and it will take some time to load.
    """
    name = 'nasa_exo_archive'
    
    def __init__(self, observatory: Observatory, cache_life_days: float | None = None):
        super().__init__(observatory, cache_life_days)
        
        self.exoplanets: Dict[str, Target] = {}
        self.exoplanets_data: Table
        
        self._load_data()
        
    def _load_data(self) -> None:
        """Check local cache and if too old, get the new copy then load the lot in to memory."""
        if self.needs_updating():
            # fetch new file and pickle it
            r = requests.get('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+*+from+ps+where+tran_flag=1+and+default_flag=1+order+by+pl_name&format=votable',
                             timeout=60*5)  # five min timeout as this is LARGE
            if r.status_code != 200:
                raise ValueError("Failed to load the NASA Exoplanet Archive")
            vot = BytesIO(r.text.encode())
            self.exoplanets_data = Table.read(vot, format='votable')
            fix_str_types(self.exoplanets_data)
            
            self.exoplanets_data.write(self.cache_file, path=self.name, append=True, overwrite=True)
            self.update_age()            
        else:
            self.exoplanets_data = Table.read(self.cache_file, path=self.name)
        
        def _not_valid_field(e: Any) -> bool:
            return not e or ((isinstance(e, float) or isinstance(e, np.float32) or isinstance(e, np.float64)) and np.isnan(e)) or (isinstance(e, str) and e.lower() == 'nan')
        
        self.exoplanets = {}
        for exo in self.exoplanets_data:
            e = exo['pl_tranmid']
            if _not_valid_field(e):
                e = None
            else:
                e = Time(e, format="jd", scale="tcb")
            p = exo['pl_orbper']
            if _not_valid_field(p):
                p = None
            else:
                p *= u.day
            d = exo['pl_trandur']
            if _not_valid_field(d):
                d = None
            else:
                d *= u.hour
            ex = exo['pl_orbeccen']
            if _not_valid_field(ex):
                ex = 0.0
            
            t = Target(observatory=self.observatory, 
                       name=exo['hostname'], 
                       ra_j2000=exo['ra'],
                       dec_j2000=exo['dec'],
                       epoch=e,
                       period=p,
                       duration=d,
                       eccentricity=ex,
                       argument_of_periapsis=0.0 * u.deg,  # unknown
                       is_exoplanet=True)
            
            t.mag_v = np.nan
            t.mag_r = exo.get('sy_rmag', np.nan)
            t.mag_g = exo.get('sy_gaiamag', np.nan)
            
            self.exoplanets[exo['hostname']] = t
            if exo['hd_name']:
                self.exoplanets[exo['hd_name']] = t
            if exo['hip_name']:
                self.exoplanets[exo['hip_name']] = t
            if exo['tic_id']:
                self.exoplanets[exo['tic_id']] = t
            if exo['gaia_id']:
                self.exoplanets[exo['gaia_id']] = t
        
    def query_target(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        return self.exoplanets.get(name, None)
