# -*- coding: UTF-8 -*-
# cSpell:ignore exoclock gcvs
from tofo.observatory import Observatory
from tofo.targets import Target
from tofo.sources.aavso import VSX
from tofo.sources.gcvs import GCVS
from tofo.sources.nasa_exo import NasaExoArchive
from tofo.sources.exoclock import ExoClock


class ObjectDB():
    """Collection of all different data sources and mechanisms to query them."""
    def __init__(self, observatory: Observatory):
        self.observatory = observatory
        
        self.vsx = VSX(observatory)
        self.gcvs = GCVS(observatory)
        self.nasa_exo = NasaExoArchive(observatory)
        self.exoclock = ExoClock(observatory)
        
    def find_object(self, name: str) -> Target | None:
        """Find the general object using local databases.
        
        The sequence is (since we most often look for exoplanets):
            1. exoclock
            2. nasa exoplanet archive
            3. gcvs
            4. vsx

        We prefer GCVS over VSX since we have it locally, immediately.

        Args:
            name (str): name of the object we are looking for

        Returns:
            Target | None: representation of the object or None if the object was not found.
        """
        t = self.exoclock.query_target(name)
        if t is not None:
            return t
        t = self.nasa_exo.query_target(name)
        if t is not None:
            return t
        t = self.gcvs.query_target(name)
        if t is not None:
            return t
        t = self.exoclock.query_target(name)
        if t is not None:
            return t
        return None
