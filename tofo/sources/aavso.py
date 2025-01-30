# -*- coding: UTF-8 -*-
# cSpell:ignore AAVSO VSX AUID hmsdms tomag UBVR
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, NamedTuple
import numpy as np
import h5py
import requests

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table

from tofo.target import Target
from tofo.observatory import Observatories
from tofo.sources.source import Source
from tofo.sources.utils import create_target, fix_str_types


class RadiusTarget(NamedTuple):
    """Simple specification of the radius search parameters."""
    ra: float
    dec: float
    radius: float
    limiting_mag: float


class VSX(Source):
    """Wrapper around AAVSO VSX datasource"""
    
    name = 'aavso_vsx'
    url= 'https://www.aavso.org/vsx/index.php'
    path_single_target = 'single'
    path_radius_targets = 'radius'
    
    def __init__(self, observatories: Observatories, cache_life_days: float | None = None):
        super().__init__(observatories, cache_life_days)
        self.target_data: Table = Table(names=("Name", "AUID", "OID", "Constellation", 
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
        self.r_target_data: Table = Table(names=(
                                              "ra", "dec", "radius", "limiting_mag",
                                              "Name", "AUID", "OID", "Constellation", 
                                              "RA2000", "Declination2000", "RA DEC",
                                              "VariabilityType",
                                              "MaxMag", "MinMag",
                                              "Period", "Epoch", "EclipseDuration",
                                              "SpectralType", "Category"),
                                          dtype=(
                                              "f8", "f8", "f8", "f8",
                                              "str", "str", "str", "str", 
                                              "str", "str", "str", 
                                              "str", 
                                              "str", "str", 
                                              "f8", "f8", "f8", 
                                              "str", "str", 
                                          ))
        self.targets: Dict[str, Target] = {}
        self.r_targets: Dict[RadiusTarget, Target] = {}
        # cached methods
        self.query_target_cache = lru_cache(maxsize=None)(self._query_target_nocache)
        self.query_radius = lru_cache(maxsize=None)(self._query_radius_nocache)
        
        self._load_data()
        
    def _load_data(self) -> None:
        if not self.needs_updating() and self._create_paths_if_needed():
            self.target_data = Table.read(self.cache_file, path=self.name+'/'+self.path_single_target)
            self.r_target_data = Table.read(self.cache_file, path=self.name+'/'+self.path_radius_targets)
        self.targets = {
            row['Name']: create_target(self.observatories.observatory,
                                       name=row['Name'], 
                                       ra_deg=row['RA2000'],
                                       dec_deg=row['Declination2000'],
                                       epoch=row['Epoch'],
                                       period=row['Period'],
                                       duration=row['EclipseDuration'],
                                       var_type=row['VariabilityType'],
                                       minmag=row['MinMag'],
                                       maxmag=row['MaxMag'],
                                       auid=row['AUID']
                                       ) 
            for row 
            in self.target_data
        }
        old_rt = RadiusTarget(0.0, 0.0, 0.0, 0.0)
        self.r_targets = {}
        for row in self.r_target_data:
            rt = RadiusTarget(row['ra'], row['dec'], row['radius'], row['limiting_mag'])
            if rt != old_rt:
                self.r_targets[rt] = []
                old_rt = rt
            t = create_target(self.observatories.observatory,
                              name=row['Name'], 
                              ra_deg=row['RA2000'],
                              dec_deg=row['Declination2000'],
                              epoch=row['Epoch'],
                              period=row['Period'],
                              duration=row['EclipseDuration'],
                              var_type=row['VariabilityType'],
                              minmag=row['MinMag'],
                              maxmag=row['MaxMag'],
                              auid=row['AUID']
                              ) 
            self.r_targets[rt].append(t)
    
    def query_target(self, name: str) -> Target | None:
        """Query target.
        
        This strange delegated implementation is needed because we are caching the call
        and since the method is abstract pylint complains that is was not implemented
        even though it is (once `__init__` runs)."""
        return self.query_target_cache(name)
                
    def _query_target_nocache(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it and if not try to load it from VSX.
        
        Once a target has been loaded it will be locally cached.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        t: Target | None = self.targets.get(name, None)
        if t is None:
            t = self._query_target_online(name)
        return t

    def _query_target_online(self, name: str) -> Target | None:
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
            self.log.error("Failed to load data from AAVSO VSX for '%s': %d: %s", name, response.status_code, response.reason)
            return None
        js = response.json()
        if 'VSXObject' in js and js['VSXObject']:
            t, _ = self._add_vsx_js_object(js['VSXObject'])
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
        rem_chars = ':*><() UBVRIcj/CN'
        row[8] = row[8].translate({ord(i): None for i in rem_chars})
        row[9] = row[9].translate({ord(i): None for i in rem_chars})
        row[10] = row[10].translate({ord(i): None for i in rem_chars})
        row[11] = row[11].translate({ord(i): None for i in rem_chars})
        row[12] = row[12].translate({ord(i): None for i in rem_chars})
        # conv Period, Epoch and EclipseDuration to floats
        row[10] = conv_float(row[10]) if row[10] != 'null' else np.nan
        row[11] = conv_float(row[11]) if row[11] != 'null' else np.nan
        row[12] = conv_float(row[12]) if row[12] != 'null' else np.nan
        
    def _add_vsx_js_object(self, js: dict, ret_row: bool = False):
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
        
        self._cleanup_vsx_row(new_row)
        self.target_data.add_row(new_row)
        fix_str_types(self.target_data)  # expensive but ...
        self.target_data.write(self.cache_file, path=self.name+'/'+self.path_single_target, append=True, overwrite=True)
        self.update_age()
            
        t = create_target(self.observatories.observatory,
                          name=new_row[0],
                          ra_deg=new_row[4],
                          dec_deg=new_row[5],
                          epoch=new_row[11],
                          period=new_row[10],
                          duration=new_row[12],
                          var_type=new_row[7],
                          minmag=new_row[8],
                          maxmag=new_row[9],
                          auid=new_row[1]
                          )
        self.targets[name] = t
        if ret_row:
            return t, new_row
        else:
            return t, []

    def _create_paths_if_needed(self) -> bool:
        """Check if the correct path exists in the HDF5 file."""        
        p = Path(self.cache_file)
        if not p.exists():
            return False
        with h5py.File(self.cache_file, "r") as f:
            keys = list(f.keys())
            if self.name not in keys:
                g = f.create_group(self.name)
                g.create_dataset(self.path_single_target)
                g.create_dataset(self.path_radius_targets)
            return True

    def _query_radius_nocache(self, 
                              ra: float, dec: float, 
                              radius: float, limiting_mag: float,
                              ) -> List[Target]:
        key = RadiusTarget(ra, dec, radius, limiting_mag)
        tl: List[Target] = self.r_targets.get(key, [])
        if not tl:
            tl = self._query_radius_online(key)
        return tl
    
    def _query_radius_online(self, rt: RadiusTarget) -> List[Target]:
        
        query = {
            'view': 'api.list',
            'ra': rt.ra,
            'dec': rt.dec,
            'radius': rt.radius,
            'tomag': rt.limiting_mag,
            'format': 'json'
        }
        response = requests.get(VSX.url, params=query, timeout=30)
        if response.status_code != 200:
            self.log.error("Failed to load data from AAVSO VSX for radius search: %s", str(rt)) 
            return []
        js = response.json()
        if 'VSXObjects' not in js:
            return []
        
        if isinstance(js['VSXObjects'], list):
            return []
        
        stars = js['VSXObjects'].get('VSXObject', {})
        if not stars:
            return []
        
        self.r_targets[rt] = []
        found_t: List[Target] = []
        rtl = [rt.ra, rt.dec, rt.radius, rt.limiting_mag]
        for s in stars:
            t, row = self._add_vsx_js_object(s, ret_row=True)
            self.r_targets[rt].append(t)
            new_row = rtl + row
            self.r_target_data.add_row(new_row)
            found_t.append(t)
        
        fix_str_types(self.r_target_data)  # expensive but ...
        self.r_target_data.write(self.cache_file, path=self.name+'/'+self.path_radius_targets, append=True, overwrite=True)
        self.update_age()
        return found_t
