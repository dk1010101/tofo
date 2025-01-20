# -*- coding: UTF-8 -*-
# cSpell:ignore AAVSO VSX AUID
import logging
from pathlib import Path
from typing import Dict
import numpy as np
import h5py
import requests

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
        self.exoplanets_data: Table = Table(names=("Name", "AUID", "RA2000", "Declination2000","VariabilityType",
                                                   "Period", "Epoch", "EclipseDuration",
                                                   "MaxMag", "MinMag",
                                                   "Category", "OID", "Constellation"),
                                            dtype=("str", "str", "f8", "f8", "str", 
                                                   "f8", "f8", "f8", 
                                                   "str", "str", 
                                                   "str", "str", "str"))
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
            new_row = [
                name,
                js['VSXObject'].get('AUID', ''),
                js['VSXObject']['RA2000'],
                js['VSXObject']['Declination2000'],
                js['VSXObject'].get('VariabilityType', ''),
                np.float64(js['VSXObject'].get('Period', np.nan)),
                np.float64(js['VSXObject'].get('Epoch', np.nan)),
                np.float64(js['VSXObject'].get('EclipseDuration', np.nan)),
                js['VSXObject'].get('MaxMag', ''),
                js['VSXObject'].get('MinMag', ''),
                js['VSXObject'].get('Category', ''),
                js['VSXObject'].get('OID', ''),
                js['VSXObject'].get('Constellation', ''),
            ]
            self.exoplanets_data.add_row(new_row)
            fix_str_types(self.exoplanets_data)  # expensive but ...
            self.exoplanets_data.write(self.cache_file, path=self.name, append=True, overwrite=True)
            self.update_age()
            
            t =  create_target(self.observatory,
                               name,
                               js['VSXObject']['RA2000'], 
                               js['VSXObject']['Declination2000'],
                               js['VSXObject'].get('Epoch', ''), 
                               js['VSXObject'].get('Period', ''),
                               js['VSXObject'].get('EclipseDuration', ''))
            self.exoplanets[name] = t
            return t

    def _path_exists(self) -> bool:
        """Check if the correct path exists in the HDF5 file."""        
        p = Path(self.cache_file)
        if not p.exists():
            return False
        with h5py.File(self.cache_file, "r") as f:
            keys = list(f.keys())
            return self.name in keys
