# -*- coding: UTF-8 -*-
# cSpell:ignore crota exoclock
import csv
import datetime
from typing import Tuple, List, NamedTuple, Any

import numpy as np

import astropy.units as u
from astropy.coordinates import EarthLocation
from astroplan import Observer, Constraint, AtNightConstraint

from tofo.constraint.planner_horizon_constraint import HorizonConstraint


class SourceDefinition(NamedTuple):
    """Wrapper around data source parameters."""
    use: bool
    cache_life_days: float = 0.0


class Observatory:
    """All things related to the observing location and the equipment that is to be used."""    
    
    def __init__(self, data: dict) -> None:
        """Create the observatory object from dictionary.
        
        The dictionary is usually created by reading in the YAML or JSON file with
        appropriate data.
        
        This "constructor" also creates horizon and twilight constraint list, if the right data
        is passed in.
        """
        self.location: EarthLocation = EarthLocation.from_geodetic(lon=data['observatory']['lon_deg'] * u.deg, 
                                                                   lat=data['observatory']['lat_deg'] * u.deg, 
                                                                   height=data['observatory']['elevation_m'] * u.m)
        timezone = data['observatory']['time_zone']
        self.observer: Observer = Observer(location=self.location, 
                                           name=data['observatory']['name'], 
                                           timezone=timezone, 
                                           temperature=data['observatory']['temperature_C'] * u.deg_C, 
                                           pressure=data['observatory']['pressure_hPa'] * u.hPa, 
                                           relative_humidity=data['observatory']['rel_humidity_percentage'] / 100.0)
        tnow = datetime.datetime.now(self.observer.timezone)
        self.timezone_offset = tnow.utcoffset().total_seconds() * u.s
        self.focal_length: u.Quantity = data['telescope']['focal_length_mm'] * u.mm
        self.aperture: u.Quantity = data['telescope']['aperture_mm'] * u.mm
        self.sensor_size_px: Tuple[int, int] = (data['telescope']['sensor']['num_pix_x'], data['telescope']['sensor']['num_pix_y'])
        self.sensor_size: Tuple[u.Quantity, u.Quantity] = (data['telescope']['sensor']['size_x_mm'] *u.mm, data['telescope']['sensor']['size_y_mm'] *u.mm)
        self.fov = (np.arctan(self.sensor_size[0]/self.focal_length).to(u.deg), 
                    np.arctan(self.sensor_size[1]/self.focal_length).to(u.deg))
        
        self.cdelt1: float = (self.fov[0]/self.sensor_size_px[0]).value
        self.cdelt2: float = (self.fov[1]/self.sensor_size_px[1]).value
        self.crota1: float = data['telescope']['sensor']['crota1']
        self.crota2: float = data['telescope']['sensor']['crota2']
        self.limiting_mag: float = data['observations']['min_mag']
        
        self.exo_hours_before: u.Quantity = data['observations']['exo_hours_before'] * u.hour
        self.exo_hours_after: u.Quantity = data['observations']['exo_hours_after'] * u.hour
        
        # twilight constraint
        self.constraints: List[Constraint] = []
        twilight = data['observations'].get('twilight', '')
        if twilight:
            if twilight == 'civil':
                self.constraints.append(AtNightConstraint.twilight_civil())
            elif twilight == 'nautical':
                self.constraints.append(AtNightConstraint.twilight_nautical())
            elif twilight == 'astronomical':
                self.constraints.append(AtNightConstraint.twilight_astronomical())
            else:
                raise ValueError(f"Unrecognised twilight specification: '{twilight}'")
        
        # load horizon
        self.horizon: List[Tuple[float, float]] = []
        if data['observatory'].get('horizon_file', False):
            with open(data['observatory']['horizon_file'], 'r', encoding="utf-8") as file:
                csv_reader = csv.reader(file) # pass the file object to reader() to get the reader object
                self.horizon = [(float(e[0]), float(e[1])) for e in list(csv_reader)]
        else:
            self.horizon = [(0.0, 0.0), (90.0, 0.0), (180.0, 0.0), (270.0, 0.0), (360.0, 0.0)]      
        horizon_constraint = HorizonConstraint(self.horizon)
        self.constraints.append(horizon_constraint)

        self.sources = {}
        sources: dict = data["sources"]
        self.sources_cache_file_name = sources["cache_file"]
        for k, v in sources.items():
            if k=='cache_file':
                continue
            self.sources[k] = SourceDefinition(use=v.get("use", True), 
                                               cache_life_days=v.get('cache_life_days', 0.0)*u.day)

    def __eq__(self, other: Any):
        """Equality..."""
        if isinstance(other, Observatory):
            return all([
                self.location.lat == other.location.lat,
                self.location.lon == other.location.lon,
                self.location.height == other.location.height,
                self.observer.location.lat == other.observer.location.lat,
                self.observer.location.lon == other.observer.location.lon,
                self.observer.location.height == other.observer.location.height,
                self.observer.name == other.observer.name,
                self.observer.timezone == other.observer.timezone,
                self.observer.temperature == other.observer.temperature,
                self.observer.pressure == other.observer.pressure,
                self.observer.relative_humidity == other.observer.relative_humidity,
                self.focal_length == other.focal_length,
                self.aperture == other.aperture,
                self.sensor_size_px == other.sensor_size_px,
                self.sensor_size == other.sensor_size,
                self.fov == other.fov,
                self.cdelt1 == other.cdelt1,
                self.cdelt2 == other.cdelt2,
                self.crota1 == other.crota1,
                self.crota2 == other.crota2,
                self.limiting_mag == other.limiting_mag,
                self.exo_hours_before == other.exo_hours_before,
                self.exo_hours_after == other.exo_hours_after,
                self.horizon == other.horizon,
                self.sources_cache_file_name == other.sources_cache_file_name,
                self.sources == other.sources,
                len(self.constraints) == len(other.constraints)
                # we are not checking constraints at the moment (as we don't know how it can be done) so twilight could be different
            ])
        return False
