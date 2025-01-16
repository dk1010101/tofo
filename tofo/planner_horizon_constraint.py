import copy

from typing import List, Tuple

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from astroplan import Constraint
from astroplan.constraints import _get_altaz


class HorizonConstraint(Constraint):
    """
    Constrain the altitude of the target to the provided horizon.

    .. note::
        This can misbehave if you try to constrain to negative altitudes, as
        the `~astropy.coordinates.AltAz` frame tends to mishandle negatives.

        Also this may or may not work correctly. It is not clear atm :D
    """

    def __init__(self, 
                 horizon: List[Tuple[float, float]] | None=None, 
                 boolean_constraint: bool=True):
        """_summary_

        Args:
            horizon (List[Tuple[float, float] | None, optional): List of compass positions and 
                altitudes of the horizon. Defaults to None with will produce a zero horizon.
            boolean_constraint (bool, optional): If True, the constraint is treated as a boolean 
                (True for within the limits and False for outside). If False, the constraint 
                returns a float on [0, 1], where 0 is the min altitude and 1 is the max. 
                Defaults to True. Not tested as it is not really used. TODO: test...
        """
        if min is None:
            h = [ (0, 0), (90, 0), (180, 0), (270, 0), (360, 0)]
        else:
            h = copy.deepcopy(horizon)
        if h[-1][0] != 360:
            h.append((360, h[0][1]))
        
        self.min_val = min([e[1] for e in h])
        self.az_interp = RegularGridInterpolator([np.array([e[0] for e in h])], np.array([e[1] for e in h]), 'linear', bounds_error=False, fill_value = None)

        self.boolean_constraint = boolean_constraint

    def compute_constraint(self, times, observer, targets):
        """Compute the constraint.
        
        Args:
            times (List[Time]): The times to compute the constraint.
            observer (astroplan.Observer): The observation location from which to apply the constraints.
            targets (List[astroplan.Target]): The targets on which to apply the constraints.

        Returns:
            List[List[bool]] | List[List[float]]: 2D array of float or bool. The constraints, with targets along the first 
                index and times along the second.
        """
        cached_altaz = _get_altaz(times, observer, targets)
        altaz = cached_altaz['altaz']
        if self.boolean_constraint:
            azs = altaz.az
            alts = altaz.alt
            res = []
            for target_azs, target_alts in zip(azs, alts):
                interpolated_alt = self.az_interp([e.degree for e in target_azs])
                alt = np.array([e.degree for e in target_alts])
                mask = interpolated_alt < alt
                res.append(mask)
                
            return res
        else:
            # return max_best_rescale(alt, self.min, self.max, greater_than_max=0)
            azs = altaz.az
            alts = altaz.alt
            res = []
            for target_azs, target_alts in zip(azs, alts):
                vals = np.array([e.degree for e in target_alts])
                rescaled = (vals - self.min_val) / (90. - self.min_val)
                interpolated_horizon = self.az_interp([e.degree for e in target_azs])
                mask = vals < interpolated_horizon
                rescaled[mask] = 0        
                res.append(rescaled)
            return res
