# -*- coding: UTF-8 -*-
# cSpell:ignore crota exoclock
import csv
import numpy as np

import astropy.units as u
from astropy.coordinates import EarthLocation
from astroplan import Observer, AtNightConstraint

from tofo.planner_horizon_constraint import HorizonConstraint


class Observatory:
    """All things related to the observing location and the equipment that is to be used."""    
    
    def __init__(self, data: dict) -> None:
        """Create the observatory object from dictionary.
        
        The dictionary is usually created by reading in the YAML or JSON file with
        appropriate data.
        
        This "constructor" also creates horizon and twilight constraint list, if the right data
        is passed in.
        """
        location = EarthLocation.from_geodetic(lon=data['observatory']['lon_deg'] * u.deg, 
                                               lat=data['observatory']['lat_deg'] * u.deg, 
                                               height=data['observatory']['elevation_m'] * u.m)
        self.observer = Observer(location=location, 
                                 name=data['observatory']['name'], 
                                 timezone=data['observatory']['time_zone'], 
                                 temperature=data['observatory']['temperature_C'] * u.deg_C, 
                                 pressure=data['observatory']['pressure_hPa'] * u.hPa, 
                                 relative_humidity=data['observatory']['rel_humidity_percentage'] / 100.0)
    
        self.focal_length = data['telescope']['focal_length_mm'] * u.mm
        self.aperture = data['telescope']['aperture_mm'] * u.mm
        self.sensor_size_px = [data['telescope']['sensor']['num_pix_x'], data['telescope']['sensor']['num_pix_y']]
        self.sensor_size = (data['telescope']['sensor']['size_x_mm'] *u.mm, data['telescope']['sensor']['size_y_mm'] *u.mm)
        self.fov = (np.arctan(self.sensor_size[0]/self.focal_length).to(u.deg), 
                    np.arctan(self.sensor_size[1]/self.focal_length).to(u.deg))
        
        self.cdelt1 = (self.fov[0]/self.sensor_size_px[0]).value
        self.cdelt2 = (self.fov[1]/self.sensor_size_px[1]).value
        self.crota1 = data['telescope']['sensor']['crota1']
        self.crota2 = data['telescope']['sensor']['crota2']
        self.limiting_mag = data['observations']['min_mag']
        
        self.exo_hours_before = data['observations']['exo_hours_before'] * u.hour
        self.exo_hours_after = data['observations']['exo_hours_after'] * u.hour
        
        # twilight constraint
        self.constraints: list = []
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
        self.horizon = []
        with open(data['observatory']['horizon_file'], 'r', encoding="utf-8") as file:
            csv_reader = csv.reader(file) # pass the file object to reader() to get the reader object
            self.horizon = [(float(e[0]), float(e[1])) for e in list(csv_reader)]
            
            horizon_constraint = HorizonConstraint(self.horizon)
            self.constraints.append(horizon_constraint)

        if data.get('exoclock', []):
            self.exoclock_file = data['exoclock'].get('cache_file', 'exoclock.pickle')
            self.exoclock_file_life_day = data['exoclock'].get('cache_life_days', 1) * u.day
        else:
            self.exoclock_file = 'exoclock.pickle'
            self.exoclock_file_life_day = 1 * u.day
