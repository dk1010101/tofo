# -*- coding: UTF-8 -*-
# cSpell:ignore astropy AAVSO
import copy

from typing import List, Tuple, Any

import pytz
import numpy as np

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroplan import FixedTarget, EclipsingSystem, TimeConstraint, is_event_observable

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
                 epoch: Time | None = None,
                 period: u.Quantity | None = None,
                 duration: u.Quantity | None = None,
                 eccentricity: float = 0.0,
                 argument_of_periapsis: u.Quantity = 0.0 * u.deg,
                 observation_time: Time | None = None,
                 observation_duration: u.Quantity = None,
                 is_exoplanet: bool = False
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
        self._ra_j2000: str | float = ""
        self._dec_j2000: str | float = ""
        self._epoch: Time | None
        self.epoch_format: str = 'JD'
        self.epoch_scale: str = 'TDB'
        self._period: u.Quantity | None = None
        self._duration: u.Quantity | None = None 
        self._observation_time: Time | None = None
        self._observation_duration: u.Quantity | None = None
        self.eclipsing_system: EclipsingSystem = None
        self.is_exoplanet: bool = is_exoplanet
        self.c: SkyCoord = None
        self.target: FixedTarget = None
        self.observable_targets_all_times: list = []
        self.observable_targets_some_times: list = []
        self.eccentricity = eccentricity
        self.argument_of_periapsis: u.Quantity = argument_of_periapsis
        
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
    
    def to_utc(self, dt: Time) -> Time:
        """Convert time to UTC time."""
        tz = self.observatory.observer.timezone
        ndt = tz.normalize(tz.localize(dt.to_datetime())).astimezone(pytz.utc)
        return Time(ndt, location=self.observatory.location)

    def to_ltz(self, dt: Time) -> Time:
        """Convert time to local time zone time."""
        tzutc = pytz.utc
        ndt = tzutc.localize(dt.to_datetime())
        lt = ndt.astimezone(self.observatory.observer.timezone)
        return Time(lt.replace(tzinfo=None), location=self.observatory.location)
    
    def _set_position(self) -> None:
        """Calculate the sky position and create a fixed target for the object."""
        if self._ra_j2000 and self._dec_j2000 and self._name:
            if isinstance(self._ra_j2000, float) and isinstance(self._dec_j2000, float):
                self.c = SkyCoord(ra=self._ra_j2000*u.deg, dec=self._dec_j2000*u.deg)
            elif isinstance(self._ra_j2000, str) and isinstance(self._dec_j2000, str):
                self.c = SkyCoord(f"{self._ra_j2000} {self._dec_j2000}", unit=(u.hourangle, u.deg))
            else:
                raise ValueError(f"RA and DEC need to be either both floats or strings. Anything else is sus. {self._ra_j2000=} {self._dec_j2000=}")
            self.target = FixedTarget(name=self.name, coord=self.c)
    
    def _calc_transits(self) -> None:
        """Once we have all the data, create the eclipsing system and work out when next eclipses will happen given the observation parameters."""
        if all([self.ra_j2000, 
                self.dec_j2000, 
                self.name, 
                self.observation_time,
                ((self.observation_duration is not None) and not np.isnan(self.observation_duration.value)),
                ]):
                
            if self.epoch is not None and self.period is not None:  # it is a transit-like thing
                if self.duration is None:
                    duration = 1. * u.minute  # in case we don't have duration, we will just assume it is something short
                else:
                    duration = self.duration
                self.eclipsing_system = EclipsingSystem(primary_eclipse_time=self.epoch, 
                                                        orbital_period=self.period, 
                                                        duration=duration, 
                                                        name=self.name,
                                                        eccentricity=self.eccentricity,
                                                        argument_of_periapsis=self.argument_of_periapsis)
                num_obs = np.ceil((self._observation_duration.to(u.day) / (self.period * u.day)).value)
                midtransit_times = self.eclipsing_system.next_primary_eclipse_time(self.observation_time, num_obs)
            else:  # it is just a fixed object - so always visible
                # TODO: fix non-exo main target observability
                midtransit_times = [self.observation_time+self.observation_duration/2.0]
            transit_observability = self.check_observability(midtransit_times)
            self.observable_targets_all_times = [t for t, o in zip(midtransit_times, transit_observability) if o[0]]
            self.observable_targets_some_times = [t for t, o in zip(midtransit_times, transit_observability) if o[1]]
            
    def has_transits(self, fully_visible: bool = True) -> bool:
        """Does this target have any transits in the specified observation time."""
        if fully_visible:
            return len(self.observable_targets_all_times) > 0
        else:
            return len(self.observable_targets_some_times) > 0
    
    def check_observability(self, mid_times: List[Time]) -> Tuple[List[bool], List[bool]]:
        """Check if the transit is visible.

        Args:
            mid_times (List[Time]): List of mid-transit times
            fully_visible (bool, optional): Should we check if all parts of the transit are visible or just some. Defaults 
                to True meaning all should be visible.

        Returns:
            Tuple[List[bool], List[bool]]: a List of booleans, one for each transit time where transit is always visible and one list for
                transits where transit is visible at least at some point.
        """
        time_c = TimeConstraint(min=self.observation_time,
                                max=self.observation_end_time)

        # we need to filter the times as otherwise we will be doing a lot of unnecessary calculations
        all_transit_times = [self._transit_times(t) for t in mid_times if self.observation_time <= t <= self.observation_end_time]
        
        visibility: List[bool] = []
        for _, times in all_transit_times:
            vis = [is_event_observable([time_c, *self.observatory.constraints], self.observatory.observer, self.target, t)
                    for t in times
                    ]
            visibility.append(
                (all(vis), any(vis))
            )
        return visibility
    
    def get_transit_details(self, fully_visible: bool = True) -> list:
        """return all the timing details for the first visible transit, if any."""
        obs = []
        if fully_visible:
            obs = self.observable_targets_all_times
        else:
            obs = self.observable_targets_some_times
        if not obs:
            return []
        first_visible_transit = obs[0]
        return self._transit_times(first_visible_transit)
    
    def _transit_times(self, t: Time) -> Tuple[Tuple[Time, Time, Time, Time, Time], Tuple[Time, Time, Time, Time, Time]]:
        """For some mid-transit time, get full set of transit times as a tuple along with a tuple containing those times 
        adjusted for the barycentric offset."""
        d: u.Quantity 
        if self.duration is None or np.isnan(self.duration):
            d = 0.5 * u.minute
        else:
            d = self.duration / 2.0  # since offset if 1/2 the duration from the mid-point...
       
        tt = (
            t - d - self.observatory.exo_hours_before,
            t - d,
            t,
            t + d,
            t + d + self.observatory.exo_hours_after
        )
        deltas = [t.light_travel_time(self.target.coord, kind='barycentric', location=self.observatory.location) for t in tt]
        return tt, tuple([t - d for t, d in zip(tt, deltas)])
    
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
        if isinstance(self._ra_j2000, str):
            return self._ra_j2000.strip()
        else:
            return self._ra_j2000
    
    @property
    def dec_j2000(self) -> str:
        """DEC for the object in the DMS notation."""
        if isinstance(self._dec_j2000, str):
            return self._dec_j2000.strip()
        else:
            return self._dec_j2000
    
    @ra_j2000.setter
    def ra_j2000(self, ra: str | float) -> None:
        self._ra_j2000 = ra
        self._set_position()
        
    @dec_j2000.setter
    def dec_j2000(self, dec: str | float) -> None:
        self._dec_j2000 = dec
        self._set_position()
        
    @property
    def epoch(self) -> Time | None:
        """Event epoch."""
        return self._epoch
    
    @property
    def period(self) -> u.Quantity | None:
        """Event period."""
        return self._period
    
    @property
    def duration(self) -> u.Quantity | None:
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
    def epoch(self, e: float | Time | None) -> None:
        if isinstance(e, float):
            e = Time(e, format=self.epoch_format, scale=self.epoch_scale)
        self._epoch = e
        self._calc_transits()
    
    @period.setter
    def period(self, p: u.Quantity | None) -> None:
        self._period = p
        self._calc_transits()
    
    @duration.setter
    def duration(self, d: u.Quantity | None) -> None:
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
        s += f"{self.observable_targets_all_times}"
        return s

    def __eq__(self, other: Any):
        """Equality..."""
        if isinstance(other, Target):
            return all([self.name == other.name,
                        self.observatory == other.observatory,
                        self.star_name == other.star_name,
                        self.ra_j2000 == other.ra_j2000,
                        self.dec_j2000 == other.dec_j2000,
                        np.isclose(self.epoch.jd, other.epoch.jd, equal_nan=True),
                        self.epoch_format == other.epoch_format,
                        self.epoch_scale == other.epoch_scale,
                        np.isclose(self.period, other.period, equal_nan=True),
                        np.isclose(self.duration, other.duration, equal_nan=True),
                        self.is_exoplanet == other.is_exoplanet,
                        np.isclose(self.eccentricity, other.eccentricity, equal_nan=True),
                        np.isclose(self.argument_of_periapsis, other.argument_of_periapsis, equal_nan=True),
                        self.observation_time == other.observation_time,
                        self.observation_duration == other.observation_duration                        
            ])
        return False
