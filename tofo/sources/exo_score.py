# -*- coding: UTF-8 -*-
# cSpell:ignore isot exoclock tofo radec aavso

from pathlib import Path
from typing import List, Dict, NamedTuple

import numpy as np

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time

from tofo.targets import Target
from tofo.sources.source import Source
from tofo.sources.aavso import VSX
from tofo.sources.exoclock import ExoClock


class TargetScore(NamedTuple):
    """Simple target score record."""
    target: str
    priority: str
    score: float


class ExoScore(Source):
    """Load and/or calculate exoplanet target score based on number of observations,
    number of targets of opportunity and the shortness of tofo period/duration."""
    
    name = "exo_score"
    
    def __init__(self, 
                 observatory, cache_life_days = None, 
                 vsx: VSX = None):
        super().__init__(observatory, cache_life_days)
        if vsx is None:
            vsx = VSX(observatory)
        self.vsx: VSX = vsx
        self.scores_data: Table
        self.scores: Dict[str, TargetScore] = {}
        self._load_data()
        
    def query_target(self, name: str) -> Target | None:
        """We don't implement this one for this source."""
        raise NotImplementedError
    
    def _load_data(self) -> None:
        """Either load or calculate and save the score data."""
        if self.needs_updating():
            self._calc_and_save()
        else:
            self.scores_data = Table.read(self.cache_file, path=self.name)
        self.scores = {
            row[0]: TargetScore(row[0], row[1], row[7])
            for row in self.scores_data
        }
                
    def get_scores(self, targets: List[Target]) -> List[TargetScore | None]:
        """For a list of targets get all the scores."""
        return [self.scores.get(target.name, None) for target in targets]
    
    def get_score(self, target: Target) -> TargetScore | None:
        """For a list of targets get all the scores."""
        return self.scores.get(target.name, None)
    
    def _calc_and_save(self) -> None:
        """Calculate the score based on various rankings."""
        # setup exoclock data
        exoclock: ExoClock = ExoClock(self.observatory)  # we need a local copy
        ec = exoclock.exoplanets_data
        ec['radec'] = [f"{r} {d}" for r,d in zip(ec['ra_j2000'], ec['dec_j2000'])]
        ec['c'] = SkyCoord(ec['radec'], unit=(u.hour, u.deg))
        ec['ra'] = ec['c'].ra.deg
        ec['dec'] = ec['c'].dec.deg

        g = self.vsx.r_target_data.group_by(['ra','dec','radius','limiting_mag'])
        num_tofo = np.diff(g.groups.indices)
                
        # match aavso radius search with exoclock targets
        a1 = np.array(list(map(list, g.groups.keys[['ra','dec']].as_array())))
        a2 = np.array(list(map(list, ec[['ra','dec']].as_array())))
        exoclock_vsx_map = list(map(
            lambda x: np.argmax(
                np.isclose(x[0], a2[:,0], 1e-4) & np.isclose(x[1], a2[:,1], 1e-4)
            ), 
            a1))
        
        # create temp table that will be used to get the score
        tt = Table([ec[exoclock_vsx_map]['name'], 
            ec[exoclock_vsx_map]['priority'], 
            ec[exoclock_vsx_map]['exoclock_observations'], 
            ec[exoclock_vsx_map]['exoclock_observations_recent'], 
            num_tofo,
            g.groups.aggregate(np.nanmin)['Period'],
            g.groups.aggregate(np.nanmin)['EclipseDuration']
            ], names=('target', 
                      'priority', 'exoclock_observations','exoclock_observations_recent', 
                      'num tofo', 'min_period', 'min_duration'))
        tt['min_period'] = np.nan_to_num(tt['min_period'])
        tt['min_duration'] = np.nan_to_num(tt['min_duration'])
        tt['exoclock_observations'] = np.nan_to_num(tt['exoclock_observations'],nan=0)
        tt['exoclock_observations_recent'] = np.nan_to_num(tt['exoclock_observations_recent'],nan=0)

        # now calc the score
        def odiv(a1, a2):
            """division where zeros do work in a special way..."""
            t1 = np.copy(a1)
            t2 = np.copy(a2)
            t1[t1==0.0] = 1.0
            t2[t2==0.0] = 1.0
            return 1.-t1/t2

        t = Table([tt['target'], 
                   tt['priority'],
                   ((-tt['exoclock_observations']).argsort().argsort()+1.0) / len(tt),
                   (odiv(tt['exoclock_observations_recent'], tt['exoclock_observations']).argsort().argsort()+1.0) / len(tt),
                   (tt['num tofo'].argsort().argsort()+1.0) / len(tt),
                   ((-tt['min_period']).argsort().argsort()+1.0) / len(tt),
                   ((-tt['min_duration']).argsort().argsort()+1.0) / len(tt),
                   ],
                  names=(
                      'target', 
                      'priority',
                      'num_obs_rank',
                      'recent_obs_rank',
                      'tofo_rank',
                      'min_p_rank',
                      'min_d_rank')
                  )
        t['score'] = np.power(t['num_obs_rank'] * 
                              t['recent_obs_rank'] * t['recent_obs_rank'] * t['recent_obs_rank'] *
                              t['tofo_rank'] * t['tofo_rank'] * t['tofo_rank'] *
                              t['min_p_rank'] * t['min_p_rank'] * 
                              t['min_d_rank'], 1.0/10.0)
        t.sort('score')
        t.write(self.cache_file, path=self.name, append=True, overwrite=True)
        self.scores_data = [
            [row[0], row[1], row[7]]
            for row in t
        ]
        self.update_age()
    
    def needs_updating(self) -> bool | None:
        """This source needs updating if exoclock or vsx update times are after this source's update time needs updating."""
        p = Path(self.cache_file)
        if p.is_file():
            self.ages_table = Table.read(self.cache_file, path='ages')
            start_time_iso = self.ages_table[self.ages_table['source']==self.name]['age']
            vsx_start_time_iso = self.ages_table[self.ages_table['source']==VSX.name]['age']
            exoclock_start_time_iso = self.ages_table[self.ages_table['source']==ExoClock.name]['age']
            if start_time_iso.size > 0:
                t_s = Time(start_time_iso[:], format='isot')
            else:
                return True
            if vsx_start_time_iso.size == 0 and exoclock_start_time_iso.size == 0:
                return None
            
            if vsx_start_time_iso.size > 0:
                t_v = Time(vsx_start_time_iso[:], format='isot')
            else:
                t_v = Time("1970-01-01T00:00:00", format='isot')
            if exoclock_start_time_iso.size > 0:
                t_e = Time(exoclock_start_time_iso[:], format='isot')
            else:
                t_e = Time("1970-01-01T00:00:00", format='isot')            
        else:
            # we don't have hdf5 file so we don't have anything at all
            return None

        return t_v > t_s or t_e > t_s
