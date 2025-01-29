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
from tofo.sources.image_cache import ImageCache
from tofo.sources.exoclock import ExoClock


def load_obs()-> Observatory:
    with open("observatory.yaml", "r", encoding="utf-8") as f:
        obs_js = load(f, Loader=Loader)
    return Observatory(obs_js)
    

if __name__=="__main__":
    # load observatory
    observatory: Observatory = load_obs()
    ic = ImageCache(observatory)
    exoclock = ExoClock(observatory)
    
    # get all exoclock targets in the northern hemisphere, visible from our location
    ecd: Table = exoclock.exoplanets_data
    min_dec = -(90 * u.deg - observatory.location.lat)
    
    print(f"Filtering exoclock obects for dec >= {min_dec}")
    visible_targets = ecd[Angle(ecd['dec_j2000'], unit=(u.deg)) >= min_dec]
    
    print("Getting image for each target for the current observatory FOV.\nThis may take some time...")
    # for each, get the radius search and save it in the hdf5
    for rows_set in tqdm(range(len(visible_targets) // 32 + 1)):
        targets = [exoclock.query_target(t[0]) for t in visible_targets[rows_set * 32:(rows_set + 1) * 32]]
        ic.preload_images(targets)
