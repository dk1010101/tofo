# -*- coding: UTF-8 -*-
# cSpell:ignore gcvs astropy isot
from typing import Dict

import numpy as np

import astropy.units as u
from astropy.table import Table
from astroquery.utils.tap.core import Tap

from tofo.observatory import Observatories
from tofo.target import Target
from tofo.sources.source import Source
from tofo.sources.utils import fix_str_types, create_target


class GCVS(Source):
    """Collection of methods used to get exoplanet transits for a specific period."""
    name = 'gcvs'
    query="""
SELECT "B/gcvs/gcvs_cat".GCVS, "B/gcvs/gcvs_cat".VarName as name, "B/gcvs/gcvs_cat".RAJ2000, "B/gcvs/gcvs_cat".DEJ2000,
       "B/gcvs/gcvs_cat".VarType, "B/gcvs/gcvs_cat".VarTypeII, "B/gcvs/gcvs_cat".magMax,
       "B/gcvs/gcvs_cat".Epoch, "B/gcvs/gcvs_cat".Period, "B/gcvs/gcvs_cat"."M-m/D",
       "B/gcvs/gcvs_cat".SpType
FROM "B/gcvs/gcvs_cat"
"""
    
    def __init__(self, observatories: Observatories, cache_life_days: float | None = None):
        super().__init__(observatories, cache_life_days)
        self.tap = Tap(url="https://TAPVizieR.cds.unistra.fr/TAPVizieR/tap")
        
        self.exoplanets: Dict[str, Target] = {}
        self.exoplanets_data: Table
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Check local gcvs cache and if too old, get the new copy then load the lot in to memory."""
        if self.needs_updating():
            # fetch new file and pickle it
            job = self.tap.launch_job_async(self.query, background=False)  # has to be async as sync has limit of 2000 rows
            if job.failed:
                raise ValueError("Failed to load GCVS")
            
            self.exoplanets_data = job.get_results()
            
            fix_str_types(self.exoplanets_data)
            self.exoplanets_data['M-m_D'] = np.strings.replace(self.exoplanets_data['M-m_D'], ":", "")
            self.exoplanets_data['M-m_D'] = np.strings.replace(self.exoplanets_data['M-m_D'], "*", "")
            
            # calc duration
            mask = np.full(len(self.exoplanets_data), True)
            # we could use the .mask here but for M-m/D it doesn't appear to be right...
            mask[self.exoplanets_data['M-m_D'] == ''] = False
            mask[self.exoplanets_data['Period'] == ''] = False
            self.exoplanets_data['Duration'] = np.full(len(self.exoplanets_data), 0.0)
            p = np.asarray(self.exoplanets_data['Period'][mask], dtype=float)
            d = np.asarray(self.exoplanets_data['M-m_D'][mask], dtype=float)
            self.exoplanets_data['Duration'][mask] = ((p * d / 100.0) * u.day).to(u.hour).value
            
            # finally save
            self.exoplanets_data.write(self.cache_file, path=self.name, append=True, overwrite=True)
            self.update_age()
            
        else:
            self.exoplanets_data = Table.read(self.cache_file, path=self.name)

        self.exoplanets = {}
        for row in self.exoplanets_data:
            self.log.debug(row['name'])
            if row["Epoch"]:
                e = str(row["Epoch"])
                if 'nan' in e.lower():
                    epoch = ''
                else:
                    epoch = '24'+ e  # because GCVS decided to just remove the 24 from the from of all JDs
            else:
                epoch = ''
            ra = str(row['RAJ2000'])
            if not ra or 'nan' in ra.lower() or "--" in ra:
                self.log.warning("Target '%s' does not have legal RA: %s. Ignoring the Object.", row['name'], row['RAJ2000'])  # pylint:disable=consider-using-f-string
                continue
            dec = str(row['DEJ2000'])
            if not dec or 'nan' in dec.lower() or "--" in dec:
                self.log.warning("Target '%s' does not have legal DEC: %s. Ignoring the Object.", row['name'], row['DEJ2000'])  # pylint:disable=consider-using-f-string
                continue
                
            name = (' '.join(row['name'].split())).strip()
            gcvs_name = (' '.join(row['GCVS'].split())).strip()
            t = create_target(self.observatories.observatory,
                              name,
                              ra,
                              dec,
                              epoch,
                              row["Period"],
                              row["Duration"]
                              )
            self.exoplanets[name] = t
            if gcvs_name != name:
                self.exoplanets[gcvs_name] = t
            
    def query_target(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        return self.exoplanets.get(name, None)
