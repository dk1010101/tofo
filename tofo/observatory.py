# -*- coding: UTF-8 -*-
# cSpell:ignore crota exoclock tofo
import logging
import csv
import datetime
from pathlib import Path
from typing import Tuple, List, NamedTuple, Any, Dict

import numpy as np
from jsonschema import Draft202012Validator

import astropy.units as u
from astropy.coordinates import EarthLocation
from astroplan import Observer, Constraint, AtNightConstraint

from tofo.schema import observatories_schema
from tofo.constraint.horizon_constraint import HorizonConstraint, get_interpolator


class SourceDefinition(NamedTuple):
    """Wrapper around data source parameters."""
    use: bool
    cache_life_days: float = 0.0


class Observatory:
    """All things related to the observing location and the equipment that is to be used."""    
    
    def __init__(self, data: dict, root: Path) -> None:
        """Create the observatory object from dictionary.
        
        The dictionary is usually created by reading in the YAML or JSON file with
        appropriate data.
        
        This "constructor" also creates horizon and twilight constraint list, if the right data
        is passed in.
        """
        physical_data = data['physical']
        self.location: EarthLocation = EarthLocation.from_geodetic(lon=physical_data['lon_deg'] * u.deg, 
                                                                   lat=physical_data['lat_deg'] * u.deg, 
                                                                   height=physical_data['elevation_m'] * u.m)
        timezone = physical_data['time_zone']
        self.observer: Observer = Observer(location=self.location, 
                                           name=data['name'], 
                                           timezone=timezone, 
                                           temperature=physical_data['temperature_C'] * u.deg_C, 
                                           pressure=physical_data['pressure_hPa'] * u.hPa, 
                                           relative_humidity=physical_data['rel_humidity_percentage'] / 100.0)
        tnow = datetime.datetime.now(self.observer.timezone)
        self.timezone_offset = tnow.utcoffset().total_seconds() * u.s
        instrument = data['instrument']
        self.focal_length: u.Quantity = instrument['optics']['focal_length_mm'] * u.mm
        self.aperture: u.Quantity = instrument['optics']['aperture_mm'] * u.mm
        self.sensor_name: str = instrument['sensor'].get('name', '')
        self.sensor_size_px: Tuple[int, int] = (instrument['sensor']['num_pix_x'], instrument['sensor']['num_pix_y'])
        self.sensor_size: Tuple[u.Quantity, u.Quantity] = (instrument['sensor']['size_x_mm'] *u.mm, instrument['sensor']['size_y_mm'] *u.mm)
        self.fov = ((np.rad2deg(np.arctan(self.sensor_size[0]/self.focal_length))), 
                    (np.rad2deg(np.arctan(self.sensor_size[1]/self.focal_length))))
        
        self.cdelt1: float = (self.fov[0]/self.sensor_size_px[0]).value
        self.cdelt2: float = (self.fov[1]/self.sensor_size_px[1]).value
        self.crota1: float = instrument['sensor']['crota1']
        self.crota2: float = instrument['sensor']['crota2']
        
        config = data['configuration']
        self.limiting_mag: float = config['limiting_mag']
        
        self.exo_hours_before: u.Quantity = config['exo_hours_before'] * u.hour
        self.exo_hours_after: u.Quantity = config['exo_hours_after'] * u.hour
        
        # twilight constraint
        self.constraints: List[Constraint] = []
        twilight = config.get('twilight', '')
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
        if physical_data.get('horizon_file', False):
            hf = physical_data['horizon_file']
            with open(root.joinpath(hf).as_posix(), 'r', encoding="utf-8") as file:
                csv_reader = csv.reader(file) # pass the file object to reader() to get the reader object
                horizon = [(float(e[0]), float(e[1])) for e in list(csv_reader)]
        else:
            horizon = [(0.0, 0.0), (90.0, 0.0), (180.0, 0.0), (270.0, 0.0), (360.0, 0.0)]
        # interpolate the horizon
        interpolator = get_interpolator(horizon)
        az = np.linspace(0, 360, 180+1)  # every 2 degrees
        alt = interpolator(az)
        self.horizon = list(zip(az, alt))
        self.horizon_constraint = HorizonConstraint(self.horizon, az_interpolator=interpolator)
        self.constraints.append(self.horizon_constraint)

    def __eq__(self, other: Any):
        """Equality for all..."""
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
                self.sensor_name == other.sensor_name,
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
                len(self.constraints) == len(other.constraints)
                # we are not checking constraints at the moment (as we don't know how it can be done) so twilight could be different
            ])
        return False


class Observatories:
    """Collection of observatories and instruments we are interested in."""
    
    def __init__(self, data: dict) -> None:
        # validate that the provided json doc is valid
        self.log = logging.getLogger()
        v = Draft202012Validator(observatories_schema)
        errors = sorted(v.iter_errors(data), key=lambda e: e.path)
        if errors:
            self.log.error("Failed to validate `observatories.yaml` file using json schema.")
            for error in errors:
                s = f"{list(error.schema_path)}, {list(error.absolute_path)}, {error.message}"
                self.log.error("  %s", s)
            raise ValueError("Failed to validate `observatories.yaml` file.")
        # now process it
        
        # default observatory
        self.default_observatory: str = data['default_observatory']
        
        # configuration
        config: dict = data['configuration']
        self.root_dir: Path = Path(config['root'])
        self.cache_dir: Path = self.root_dir.joinpath("cache")
        self.cache_file: Path = self.cache_dir.joinpath(config['cache_file'])
        self.cache_image_dir: Path = self.cache_dir.joinpath("imagecache")
        data_sources: list = config['data_sources']
        self.sources = {}
        for source in data_sources:
            self.sources[source['name']] = SourceDefinition(
                use=bool(source.get('use', False)),
                cache_life_days=float(source['cache_life_days']) * u.day
            )
        
        # observatories
        observatories: Dict[str, Observatory] = data['observatories']
        self.observatories = {}
        self._observatory: Observatory|None = None
        for obs in observatories:
            self.observatories[obs['name']] = Observatory(obs, self.root_dir)
            
        self.select_observatory(self.default_observatory)
            
    def select_observatory(self, name: str) -> None:
        """Make the named observatory the selected one."""
        self._observatory = self.observatories[name]
        
    @property
    def observatory(self) -> Observatory:
        """Return the selected observatory."""
        if self._observatory is None:
            self.select_observatory(self.default_observatory)
        return self._observatory

    def __eq__(self, other: Any):
        """Equality for all..."""
        if isinstance(other, Observatories):
            return all([
                self.default_observatory == other.default_observatory,
                self.cache_dir == other.cache_dir,
                self.cache_file == other.cache_file,
                self.sources == other.sources,
                self.observatories == other.observatories,
                self.observatory == other.observatory,
                
            ])
        else:
            return False
