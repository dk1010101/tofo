# -*- coding: UTF-8 -*-
# cSpell:ignore exoclock gcvs

from typing import List, Any

from tofo.observatory import Observatory
from tofo.targets import Target
from tofo.sources.aavso import VSX
from tofo.sources.gcvs import GCVS
from tofo.sources.nasa_exo import NasaExoArchive
from tofo.sources.exoclock import ExoClock
from tofo.sources.exo_score import ExoScore, TargetScore
from tofo.sources.image_cache import ImageCache


class ObjectDB():
    """Collection of all different data sources and mechanisms to query them."""
    def __init__(self, observatory: Observatory):
        self.observatory = observatory
        
        if VSX.name in observatory.sources.keys():
            self.vsx = VSX(observatory)
        else:
            raise ValueError("the observatory file must have the ExoClock section.")
        if GCVS.name in observatory.sources.keys():
            self.gcvs = GCVS(observatory)
        else:
            self.gcvs = None
        if NasaExoArchive.name in observatory.sources.keys():
            self.nasa_exo = NasaExoArchive(observatory)
        else:
            self.nasa_exo = None
        if ExoClock.name in observatory.sources.keys():
            self.exoclock = ExoClock(observatory)
        else:
            raise ValueError("the observatory file must have the ExoClock section.")
        if ExoScore.name in observatory.sources.keys():
            self.exo_score = ExoScore(observatory, vsx=self.vsx)
        else:
            self.exo_score = None
            
        self.image_cache = ImageCache(observatory)
        
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
        if self.exoclock:
            t = self.exoclock.query_target(name)
            if t is not None:
                return t
        if self.nasa_exo:
            t = self.nasa_exo.query_target(name)
            if t is not None:
                return t
        if self.gcvs:
            t = self.gcvs.query_target(name)
            if t is not None:
                return t
        if self.vsx:
            t = self.vsx.query_target(name)
            if t is not None:
                return t
        return None

    def query_radius(self,
                     ra: float, dec: float, 
                     radius: float, limiting_mag: float) -> List[Target]:
        """_summary_

        Args:
            ra (float): _description_
            dec (float): _description_
            radius (float): _description_
            limiting_mag (float): _description_

        Returns:
            List[Target]: _description_
        """
        return self.vsx.query_radius(ra, dec, radius, limiting_mag)
    
    def get_exoplanet_scores(self, targets: List[Target]) -> List[TargetScore | None]:
        """_summary_

        Args:
            targets (List[Target]): _description_

        Returns:
            List[TargetScore | None]: _description_
        """
        if self.exo_score:
            return self.exo_score.get_scores(targets)
        else:
            return None
    
    def get_exoplanet_score(self, target: Target) -> TargetScore | None:
        """_summary_

        Args:
            targets (Target): _description_

        Returns:
            TargetScore | None: _description_
        """
        if self.exo_score:
            return self.exo_score.get_score(target)
        else:
            return None

    def get_fits(self, target: Target) -> Any:
        """_summary_

        Args:
            target (Target): _description_

        Returns:
            Any: _description_
        """
        if self.image_cache:
            return self.image_cache.get_fits(target)
        else:
            return None
