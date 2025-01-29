# -*- coding: UTF-8 -*-
# cSpell:ignore isot
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime

import astropy.units as u
from astropy.table import Table
from astropy.time import Time

from tofo.target import Target
from tofo.observatory import Observatory


class Source(ABC):
    """Abstract star catalog."""
    name = 'no name'
    
    def __init__(self, 
                 observatory: Observatory, 
                 cache_life_days: float | None = None):
        self.log = logging.getLogger()
        self.observatory: Observatory = observatory
        self.ages_table: Table
        self.age_days: u.Quantity
        
        self.cache_file: Path = observatory.sources_cache_file_name
        if cache_life_days is None:
            src = observatory.sources.get(self.name, None)
            if src is None:
                raise ValueError(f"Could not instantiate source object with {self.name} as the observatory did not have the source settings for it.")
            age = observatory.sources[self.name].cache_life_days
            if age.value < 0.0:
                age = 100_000.0 * u.day # "never" or rather "almost 274 years" :D
            self.cache_life_days: u.Quantity = age 
        else:
            self.cache_life_days: u.Quantity = cache_life_days * u.day
    
    @abstractmethod
    def query_target(self, name: str) -> Target | None:
        """Get a populated Target object from a name, if the catalog has it.

        Args:
            name (str): Name of the target

        Returns:
            Target | None: Either a populated target object or `None`
        """
        raise NotImplementedError()

    def needs_updating(self) -> bool:
        """Give the age and date/time, does the cache need updating?"""
        if self.cache_file.is_file():
            self.ages_table = Table.read(self.cache_file.as_posix(), path='ages')
            start_time_iso = self.ages_table[self.ages_table['source']==self.name]['age']
            if start_time_iso.size > 0:
                start = Time(start_time_iso[:], format="isot")
                self.age_days = (Time(datetime.now()) - start).to(u.day)
            else:
                self.age_days = self.cache_life_days + 1 * u.day   
        else:
            self.ages_table = Table(names=('source','age'), dtype=('str','str'))
            self.age_days = self.cache_life_days + 1 * u.day

        return self.age_days > self.cache_life_days
    
    def update_age(self) -> None:
        """Set the local age to zero and update the age table with the update time (now)."""
        self.age_days = 0 * u.day
        dt_iso = datetime.now().isoformat()
        mask = self.ages_table['source'] == self.name
        if any(mask):
            # if the value exists, replace it
            self.ages_table['age'][mask] = dt_iso
        else:
            # otherwise add a new row
            self.ages_table.add_row([self.name, dt_iso])
        self.ages_table.write(self.cache_file, path='ages', append=True, overwrite=True)
