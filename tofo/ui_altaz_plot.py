# -*- coding: UTF-8 -*-
# cSpell:ignore altaz 

from typing import List
import numpy as np
import astropy.units as u
from astropy.time import Time
from astroplan import Observer, FixedTarget
from matplotlib.axes import Axes



def plot_altaz_sky(target: FixedTarget, 
                   observer: Observer, 
                   time: Time|List[Time], 
                   ax: Axes, 
                   style_kwargs:dict|None=None,
                   midpoint: int=180):
    """Plot fixed target position in the altaz sky given a point in time or a list of times.

    Args:
        target (FixedTarget): Target to plot
        observer (Observer): Location etc of the observer
        time (Time | List[Time]): Time(s) at which to plot the position
        ax (Axes): Axes to use for plotting.
        style_kwargs (dict | None, optional): Styles to pass to the matplotlib plotting function. Defaults to None.
        midpoint (int, optional): Azimuth angle which will be in the middle of the plot. Defaults to 180 meaning that 
            South will be in the middle while both left and right extremes will be North. This value can only be between
            0 and 360.
    """
    def map_az(x, midpoint=180):
        azmin = midpoint-180
        azmax = azmin + 360
        nv = x
        if x > azmax:
            nv = x-(azmax-azmin)
        elif nv < azmin:
            nv=x+(azmax-azmin)
        return nv.value
    
    if ax is None:
        raise ValueError("ax cannot be None")
    if style_kwargs is None:
        style_kwargs = {}
    style_kwargs = dict(style_kwargs)
    style_kwargs.setdefault('marker', 'o')
    if not hasattr(target, 'name'):
        target_name = ''
    else:
        target_name = target.name
    style_kwargs.setdefault('label', target_name)
    
    altitude = (observer.altaz(time, target).alt) * (1/u.deg)
    azimuth = (observer.altaz(time, target).az)* (1/u.deg)
    time = Time(time)
    if time.isscalar:
        time = Time([time])
    # We only want to plot positions above the horizon.
    az_plot = None
    for alt in range(0, len(altitude)):  # pylint:disable=consider-using-enumerate
        if altitude[alt] <= 90.0:
            if az_plot is None:
                az_plot = np.array([azimuth[alt]])
            else:
                az_plot = np.append(az_plot, azimuth[alt])
    
    alt_plot = altitude[altitude <= 91.0]
    if az_plot is None:
        az_plot = []
    else:
        az_plot=[map_az(v, midpoint) for v in az_plot]
    ax.scatter(az_plot, alt_plot, **style_kwargs)
