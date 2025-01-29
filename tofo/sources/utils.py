# -*- coding: UTF-8 -*-
# cSpell:ignore isot auid
import numpy as np
import astropy.units as u
from astropy.coordinates import Angle
from astropy.table import Table
from astropy.time import Time

from tofo.target import Target
from tofo.observatory import Observatory


def fix_str_types(tab: Table) ->  None:
    """Replace all 'O' types (which are really strings) with string types.
    
    HDF5 does not like dtype 'O' while NumPy does...
    
    Args:
        tab (Table): table to modify
    """
    for col in tab.colnames:
        t = tab.dtype[col]
        if t=='O':
            tab[col] = tab[col].astype('str')


def create_target(observatory: Observatory, 
                  name: str, 
                  ra_deg: str, dec_deg: str, 
                  epoch: str,
                  period: str, duration: str,
                  epoch_format: str = 'jd',
                  epoch_scale: str = 'tcb',
                  var_type: str = '', minmag: str = '', maxmag: str = '', auid: str = '') -> Target:
    """Create the target object from string data representations.

    Args:
        observatory (Observatory): ref to the observatory
        name (str): name of the object
        ra_deg (str): object RA in degrees
        dec_deg (str): object DEC in degrees
        epoch (str): Epoch or blank string if missing
        period (str): Period or blank string if missing
        duration (str): Duration or blank string if missing
        epoch_format (str, optional): Epoch format. Defaults to 'jd' meaning Julian Date.
            We support lots of formats but the most useful are 'fits', 'gps', 'iso', 'isot',
            'jd', 'mjd', 'unix' and 'unix_tai' although 'jd' and 'mjd' will probably be most used.
            'jd' date would look be eg `2460677.25' with 'mjd' for the same would be `60676.75`
        epoch_scale (str, optional): Epoch scale. Defaults to 'tcb' meaning Barycentric Coordinate Time.
            We support International Atomic Time (tai), Barycentric Coordinate Time (tcb), 
            Geocentric Coordinate Time (tcg), Barycentric Dynamical Time (tdb), Terrestrial Time (tt), 
            Universal Time (ut1), Coordinated Universal Time (utc) and Local Time Scale (local).
        var_type (str): Type of the variability, if any
        minmag (str): Minimum magnitude. This could include non-numerical information.
        maxmag (str): Maximum magnitude. This could include non-numerical information.
        auid (str): AUID for this object

    Returns:
        Target: New Target object
    """
    ra = Angle(float(ra_deg) * u.deg).hms
    dec = Angle(float(dec_deg) * u.deg).dms
    if epoch and ((isinstance(epoch, str) and "nan" not in epoch) or 
                  ((isinstance(epoch, float) or isinstance(epoch, np.float32) or isinstance(epoch, np.float64)) and 
                   not np.isnan(epoch))):
        e = Time(epoch, format=epoch_format, scale=epoch_scale)
    else:
        e = None
    if period:
        p = float(period) * u.day
    else:
        p = None
    if duration:
        d = float(duration) * u.hour
    else:
        d = None
    return Target(observatory=observatory,
                    name=name,
                    ra_j2000=f"{int(ra.h):02d}:{int(abs(ra.m)):02d}:{abs(ra.s):04.1f}",
                    dec_j2000=f"{int(dec.d):+3d}:{int(abs(dec.m)):02d}:{abs(dec.s):04.1f}",
                    epoch=e,
                    period=p,
                    duration=d,
                    var_type=var_type,
                    minmag=minmag,
                    maxmag=maxmag,
                    auid=auid,
                    is_exoplanet=True)
