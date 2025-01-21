# -*- coding: UTF-8 -*-
# cSpell:ignore AAVSO VSX AUID hmsdms
import logging
from pathlib import Path
from typing import Dict
import numpy as np
import h5py
import requests

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table

from tofo.targets import Target
from tofo.observatory import Observatory

from tofo.sources.source import Source
from tofo.sources.utils import create_target, fix_str_types


class VSX(Source):
    """Wrapper around AAVSO VSX datasource"""
    
    name = 'aavso_vsx'
    url= 'https://www.aavso.org/vsx/index.php'
    
    def __init__(self, observatory: Observatory, cache_life_days: float | None = None):
        super().__init__(observatory, cache_life_days)
        self.log = logging.getLogger()
        self.exoplanets_data: Table = Table(names=("Name", "AUID", "OID", "Constellation", 
                                                   "RA2000", "Declination2000", "RA DEC",
                                                   "VariabilityType",
                                                   "MaxMag", "MinMag",
                                                   "Period", "Epoch", "EclipseDuration",
                                                   "SpectralType", "Category"),
                                            dtype=("str", "str", "str", "str", 
                                                   "str", "str", "str", 
                                                   "str", 
                                                   "str", "str", 
                                                   "f8", "f8", "f8", 
                                                   "str", "str", 
                                                   ))
        self.exoplanets: Dict[str, Target] = {}
        self._load_data()
        
    def _load_data(self) -> None:
        if not self.needs_updating() and self._path_exists():
            self.exoplanets_data = Table.read(self.cache_file, path=self.name)
        self.exoplanets = {
            row['Name']: create_target(self.observatory,
                                       row['Name'], 
                                       row['RA2000'],
                                       row['Declination2000'],
                                       row['Epoch'],
                                       row['Period'],
                                       row['EclipseDuration'],
                                       ) 
            for row 
            in self.exoplanets_data
        }
                
    def query_target(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it and if not try to load it from VSX.
        
        Once a target has been loaded it will be locally cached.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        t: Target | None = self.exoplanets.get(name, None)
        if t is None:
            t = self.query_target_online(name)
        return t

    def query_target_online(self, name: str) -> Target | None:
        """Get a populated Target object from a name, from VSX online source.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        query = {
            'view': 'api.object',
            'ident': name,
            'format': 'json'
        }
        response = requests.get(VSX.url, params=query, timeout=30)
        if response.status_code != 200:
            self.log.error("Failed to load data from AAVSO VSX for '%s': %d: %s" % (name, response.status_code, response.reason))  # pylint:disable=consider-using-f-string
            return None
        js = response.json()
        if 'VSXObject' in js and js['VSXObject']:
            t, _ = self.add_vsx_js_object(name, js['VSXObject'])
            return t
        else:
            return None

    def _cleanup_vsx_row(self, row: list) -> None:
        """Clean up and numerical values so that they are actually parsable numbers."""
        def conv_float(a):
            if a:
                return np.float64(a)
            else:
                return np.nan
        # MaxMag, MinMag, Period, Epoch and EclipseDuration
        row[8] = row[8].replace(":", "").replace("*", "")
        row[9] = row[9].replace(":", "").replace("*", "")
        row[10] = row[10].replace(":", "").replace("*", "")
        row[11] = row[11].replace(":", "").replace("*", "")
        row[12] = row[12].replace(":", "").replace("*", "")
        # conv Period, Epoch and EclipseDuration to floats
        row[10] = conv_float(row[10])
        row[11] = conv_float(row[11])
        row[12] = conv_float(row[12])
        

    def add_vsx_js_object(self, js: dict, ret_row: bool = False):
        """Add a new object to the cache and clean it up."""
        c = SkyCoord(ra=float(js['RA2000'])*u.degree, dec=float(js['Declination2000'])*u.degree)
        name = js['Name']
        new_row = [
                name,
                js.get('AUID', ''),
                js.get('OID', ''),
                js.get('Constellation', ''),
                js['RA2000'],
                js['Declination2000'],
                c.to_string('hmsdms'),
                js.get('VariabilityType', ''),
                js.get('MaxMag', ''),
                js.get('MinMag', ''),
                js.get('Period', ''),
                js.get('Epoch', ''),
                js.get('EclipseDuration', ''),
                js.get('SpectralType', ''),
                js.get('Category', '')
            ]
        print(new_row)
        self._cleanup_vsx_row(new_row)
        print(new_row)
        self.exoplanets_data.add_row(new_row)
        fix_str_types(self.exoplanets_data)  # expensive but ...
        self.exoplanets_data.write(self.cache_file, path=self.name, append=True, overwrite=True)
        self.update_age()
            
        t =  create_target(self.observatory,
                               new_row[0],
                               new_row[4], 
                               new_row[5],
                               new_row[11], 
                               new_row[10],
                               new_row[12])
        self.exoplanets[name] = t
        if ret_row:
            return t, new_row
        else:
            return t, []

    def _path_exists(self) -> bool:
        """Check if the correct path exists in the HDF5 file."""        
        p = Path(self.cache_file)
        if not p.exists():
            return False
        with h5py.File(self.cache_file, "r") as f:
            keys = list(f.keys())
            return self.name in keys
