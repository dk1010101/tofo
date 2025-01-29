import copy
from typing import Dict, List, Any

import astropy.units as u
from astropy.time import Time

from astroplan.scheduling import Transitioner, ObservingBlock

from tofo.target import Target
from tofo.observatory import Observatory


class TransitScheduler():
    """Mechanism to generate all possible transit++ schedules.
    
    This is a bit of a cheat. While we do use `astroplan` we don't use `astroplan` schedulers
    as the way the schedule things is ... overly complicated for what we want. The problem is
    that transits are fixed in time while their schedulers only schedule things that can move
    around. If we give `astroplan` scheduler observing blocks that conflict, nothing actually
    gets scheduled or, at best, one thing may be scheduled.
    
    What we do is create all possible schedules and then look at the ones with most observations
    and with highest scores and return those. We also then provide a mechanism to create
    `astroplan` schedule from one of possible schedules.
    """
    
    @u.quantity_input(max_pre_ingress_delta=u.second)
    @u.quantity_input(max_post_egress_delta=u.second)
    def __init__(self, 
                 observatory: Observatory,
                 targets: List[Target],
                 start_obs_time: Time,
                 end_obs_time: Time,
                 max_pre_ingress_delta: u.Quantity = (15 * u.hour).to(u.second),
                 max_post_egress_delta: u.Quantity = (15 * u.hour).to(u.second),
                 transitioner: Transitioner = None
    ):
        self.observatory: Observatory = observatory
        self.targets: List[Target] = targets
        self.start_obs_time: Time = start_obs_time
        self.end_obs_time: Time = end_obs_time
        self.max_pre_ingress_delta: u.Quantity = max_pre_ingress_delta
        self.max_post_egress_delta: u.Quantity = max_post_egress_delta
        self.transitioner: Transitioner = transitioner
        
        # make sure all targets have observation time set
        for t in self.targets:
            if t.observation_time is None:
                t.observation_time = self.start_obs_time
            if t.observation_end_time is None:
                t.observation_end_time = self.end_obs_time
        
        self.target_block: Dict[str, ObservingBlock] = []
        self.target_data: Dict[str, Any] = {}
        self.target_name: List[str] = []
        self._make_target_data_names_block()
        
        self.possible_sequences: List[Any] = self._find_all_sequences()
        
    def _make_target_data_names_block(self) -> None:
        """Create the data and names from targets that were passed in during construction."""
        # data
        ts = [target.to_tuple() for target in self.targets]
        ts = [t for t in ts if t is not None]
        sl = sorted(ts, key=lambda x: x[2])
        self.target_data = {
            e[0]: [*e][1:]
            for e in sl
        }
        # names
        self.target_name = list(self.target_data.keys())
        # blocks
        self.target_block = {t[0]: ObservingBlock(t[4], (t[3] - t[2]).to(u.second), t[1]) for t in ts}
        
    def _find_all_sequences(self) -> None:
        local_l = copy.copy(self.target_name)
        res = []
        while local_l:
            e = local_l.pop(0)
            r = self._find_all(local_l, [], e)
            if r:
                res.extend(r)
        return res
    
    def _find_all(self, 
                  names: list, 
                  ws: list|None = None, 
                  e: str|None = None):
        if not names:
            return []
        if ws is None:
            ws = []
        local_l = copy.copy(names)
        res = []
        if e is None:
            e = local_l.pop(0)
        if '|' in e:
            ename, _ = e.split("|")
        else:
            ename = e
        for ie2, e2 in enumerate(local_l):
            if '|' in e2:
                e2name, _ = e2.split("|")
            else:
                e2name = e2
            if ename == e2name:
                continue
            local_ws = copy.copy(ws)
            transition = self.transitioner(self.target_block[e], self.target_block[e2], self.target_data[e2][1], self.observatory.observer)
            if transition:
                dur = transition.duration
            else:
                dur = 0.0 * u.minute
            if (self.target_data[e][2] + dur) <= self.target_data[e2][1]:  # if e2 starts after e is done        
                # print(f"  ok")
                if local_ws:
                    local_ws.extend([e2])
                else:
                    local_ws = [e, e2]
                res.append(local_ws)
                r = self._find_all(local_l[ie2+1:], local_ws, e2)
                if r:
                    res.extend(r)
        return res
    
    