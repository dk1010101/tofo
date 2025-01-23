from tqdm import tqdm
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import astropy.units as u
from astropy.table import Table
from astropy.coordinates import Angle, SkyCoord

from tofo.observatory import Observatory
from tofo.sources.aavso import VSX
from tofo.sources.exoclock import ExoClock


def load_obs()-> Observatory:
    with open("observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    return Observatory(obs_js)
    

if __name__=="__main__":
    # load observatory
    observatory: Observatory = load_obs()
    vsx = VSX(observatory)
    exoclock = ExoClock(observatory)
    
    # get all exoclock targets in the northern hemisphere
    ecd: Table = exoclock.exoplanets_data
    min_dec = -(90 * u.deg - observatory.location.lat)
    
    print(f"Filtering exoclock obects for dec >= {min_dec}")
    visible_targets = ecd[Angle(ecd['dec_j2000'], unit=(u.deg)) >= min_dec]
    
    print("Getting data for each target...")
    # for each, get the radius search and save it in the hdf5
    for row in tqdm(visible_targets):
        c = SkyCoord(f"{row['ra_j2000']} {row['dec_j2000']}", unit=(u.hourangle, u.deg))
        vsx.query_radius(c.ra.deg, c.dec.deg, 0.6747090467121688, 15.0)
