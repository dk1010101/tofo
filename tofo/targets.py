# cSpell:ignore astropy AAVSO
import copy
import requests

from typing import List, Tuple

import numpy as np

import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.time import Time
from astroplan import FixedTarget, EclipsingSystem, LocalTimeConstraint, is_event_observable

from tofo.observatory import Observatory


class Target():
    """Wrapper around observation targets.
    
    Targets are assumed to be stars or exoplanets around stars. If the class is used to get the details
    of the object, it will try AAVSO Variable Star Index and if that fails, it will give up so valid
    targets (when looking up) are really only variable stars of exoplanets.
    """    
    def __init__(self,
                 observatory: Observatory,
                 name: str,
                 star_name: str = "",
                 ra_j2000: str = "",
                 dec_j2000: str = "",
                 epoch: float = np.nan,
                 period: float = np.nan,
                 duration: float = np.nan,
                 observation_time: Time | None = None,
                 observation_duration: u.Quantity = None
                 ):
        """Create the Target object.

        Args:
            observatory (Observatory): Wrapper of all observatory information needed to work out visibility of the target.
            name (str): Name of the object.
            star_name (str, optional): Name of the star the object is associated with. Defaults to "" meaning that the star and the object are the same.
            ra_j2000 (str, optional): RA of the object as an HMS string. Defaults to "".
            dec_j2000 (str, optional): DEC of the object as a DMS string. Defaults to "".
            epoch (float, optional): Epoch of the event. Defaults to np.nan.
            period (float, optional): Period of the event. Defaults to np.nan.
            duration (float, optional): DUration of the event. Defaults to np.nan.
            observation_time (Time | None, optional): Start time of the observation. Defaults to None.
            observation_duration (u.Quantity, optional): Duration of the possible observation run as a proper astropy quantity. Defaults to None.
        """
        self.observatory = observatory
        self._name: str = ""
        self._star_name: str = ""
        self._ra_j2000: str = ""
        self._dec_j2000: str = ""
        self._epoch: float = np.nan
        self._period: float = np.nan
        self._duration: float = np.nan
        self._observation_time: Time | None = None
        self._observation_duration: u.Quantity | None = None
        self.eclipsing_system: EclipsingSystem = None
        self.c: SkyCoord = None
        self.target: FixedTarget = None
        self.transits: list = []
        
        # assignments
        self.ra_j2000 = ra_j2000
        self.dec_j2000 = dec_j2000

        self.name = name
        self.star_name = star_name

        self.epoch = epoch
        self.period = period
        self.duration = duration
        
        self.observation_duration = observation_duration
        self.observation_time = observation_time
    
    def _set_position(self) -> None:
        """Calculate the sky position and create a fixed target for the object."""
        if self._ra_j2000 and self._dec_j2000 and self._name:
            self.c = SkyCoord(f"{self._ra_j2000} {self._dec_j2000}", unit=(u.hourangle, u.deg))
            self.target = FixedTarget(name=self.name, coord=self.c)
    
    def _calc_transits(self) -> None:
        """Once we have all the data, create the eclipsing system and work out when next eclipses will happen given the observation parameters."""
        if all([self.ra_j2000, 
               self.dec_j2000, 
               self.name, 
               self.observation_time,
               ((self.observation_duration is not None) and not np.isnan(self.observation_duration.value)),
               self.period != 0.0]):
            constraints = copy.deepcopy(self.observatory.constraints)
            constraints.append(LocalTimeConstraint(min=self.observation_time.datetime.time(),
                                                    max=(self.observation_time+self.observation_duration).datetime.time()))
                
            if not any(np.isnan([self.epoch, self.period])):  # it is a transit-like thing
                duration = 1. * u.minute  # in case we don't have duration, we will just assume it is something short
                if not np.isnan(self.duration):
                    duration = self.duration * u.hour  # if we have the duration (transit, eclipse) then use it
                self.eclipsing_system = EclipsingSystem(primary_eclipse_time=Time(self.epoch, format='jd'), 
                                                        orbital_period=self.period * u.day, 
                                                        duration=duration, 
                                                        name=self.name)
                num_obs = np.ceil((self._observation_duration.to(u.day) / (self.period*u.day)).value)
                transits = self.eclipsing_system.next_primary_eclipse_time(self.observation_time, num_obs)
                observables = [is_event_observable(constraints, self.observatory.observer, self.target, times=midtransit_time) for midtransit_time in transits]
                self.transits = [t for t, o in zip(transits, observables) if o]
                
            else:  # it is just a fixed object - so always visible
                transits = [self.observation_time]
                observables = [is_event_observable(constraints, self.observatory.observer, self.target, times=midtransit_time) for midtransit_time in transits]
                self.transits = [t for t, o in zip(transits, observables) if o]
            
    def get_transit_details(self) -> List[Tuple[Time, Time, Time, Time, Time]]:
        """Get full transit timings for all possible transits."""
        if not self.transits:
            self._calc_transits()
        if not self.transits:
            return []
        if self.duration is None or np.isnan(self.duration):
            if self.transits:
                td = [(self.observation_time, self.observation_time, self.observation_time + self.observation_duration / 2.0, self.observation_end_time, self.observation_end_time)]
            else:
                td = []
        else:
            delta = (self.duration / 2.0) * u.hour
            td = [(t-delta-self.observatory.exo_hours_before, t-delta, t, t+delta, t+delta+self.observatory.exo_hours_after) for t in self.transits]
        return td
    
    def lookup_object_details(self) -> bool:
        """Use online databases to find object position and other details."""
        url= f'https://www.aavso.org/vsx/index.php'
        query = {
            'view': 'api.object',
            'ident': self.star_name,
            'format': 'json'
        }
        
        response = requests.get(url, params=query, timeout=30)
        js = response.json()
        print(js)
        if 'VSXObject' in js and js['VSXObject']:            
            ra = Angle(float(js['VSXObject']['RA2000'])*u.deg).hms
            dec = Angle(float(js['VSXObject']['Declination2000'])*u.deg).dms
            self.ra_j2000 = f"{int(ra.h):02d}:{int(abs(ra.m)):02d}:{abs(ra.s):04.1f}"
            self.dec_j2000 = f"{int(dec.d):+3d}:{int(abs(dec.m)):02d}:{abs(dec.s):04.1f}"
            
            self.epoch = float(js['VSXObject'].get('Epoch', '2400000.0000'))
            self.period = float(js['VSXObject'].get('Period', 0.0))
            self.duration = float(js['VSXObject'].get('EclipseDuration', 0.0))
            return True
        else:
            return False
    
    @property
    def name(self) -> str:
        """Object Name"""
        return self._name
    
    @property
    def star_name(self) -> str:
        """Star Name, if different from object name."""
        return self._star_name
    
    @name.setter
    def name(self, s: str) -> str:
        self._name = s
        if not self._star_name:
            self._star_name = s
        self._set_position()
    
    @star_name.setter
    def star_name(self, s: str) -> str:
        if s:
            self._star_name = s
        else:
            self._star_name = self.name
    
    @property
    def ra_j2000(self) -> str:
        """RA for the object in the HMS notation."""
        return self._ra_j2000
    
    @property
    def dec_j2000(self) -> str:
        """DEC for the object in the DMS notation."""
        return self._dec_j2000
    
    @ra_j2000.setter
    def ra_j2000(self, ra: str) -> None:
        self._ra_j2000 = ra
        self._set_position()
        
    @dec_j2000.setter
    def dec_j2000(self, dec: str) -> None:
        self._dec_j2000 = dec
        self._set_position()
        
    @property
    def epoch(self) -> float:
        """Event epoch."""
        return self._epoch
    
    @property
    def period(self) -> float:
        """Event period."""
        return self._period
    
    @property
    def duration(self) -> float:
        """Event duration."""
        return self._duration

    @property
    def observation_time(self) -> Time | None:
        """When will the event be observed from?"""
        return self._observation_time
    
    @property
    def observation_duration(self) -> u.Quantity | None:
        """Duration of the observation as an `astropy.units.Quantity`."""
        return self._observation_duration
    
    @property
    def observation_end_time(self) -> Time | None:
        """Fake observation end time from the start time and duration."""
        if self._observation_time is None or self._observation_duration is None:
            return None
        return self.observation_time + self.observation_duration
    
    @epoch.setter
    def epoch(self, e: float) -> None:
        self._epoch = e
        self._calc_transits()
    
    @period.setter
    def period(self, p: float) -> None:
        self._period = p
        self._calc_transits()
    
    @duration.setter
    def duration(self, d: float) -> None:
        self._duration = d
        self._calc_transits()
        
    @observation_time.setter
    def observation_time(self, t: Time | None) -> None:
        self._observation_time = t
        self._calc_transits()
    
    @observation_duration.setter
    def observation_duration(self, d: u.Quantity | None) -> None:
        self._observation_duration = d
        self._calc_transits()

    @observation_end_time.setter
    def observation_end_time(self, t: Time) -> None:
        duration = (t - self.observation_time).to(u.hour)
        self.observation_duration = duration

    def __repr__(self) -> str:
        """Representation of the object."""
        s = f"{self.name} {self.star_name} ({self.ra_j2000} {self.dec_j2000}) - "
        s += f"[{self.epoch}, {self.period}, {self.duration}] @ {self.observation_time} for {self.observation_duration} : "
        s += f"{self.transits}"
        return s
