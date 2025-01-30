# -*- coding: UTF-8 -*-
# cSpell:ignore tofo
import logging
import concurrent.futures

from pathlib import Path
from typing import Any, List, Set, Tuple

from astropy.io import fits
from pyvo import registry

from tofo.target import Target
from tofo.observatory import Observatories


class ImageCache():
    """Simple file-based cache for fist images."""
    def __init__(self, observatories: Observatories):
        self.log = logging.getLogger()
        self.observatories = observatories
        
        # get the cache directory for this observatory and sensor
        path = observatories.cache_image_dir.joinpath(self.observatories.observatory.observer.name)
        path = path.joinpath(self.observatories.observatory.sensor_name)
        path.mkdir(parents=True, exist_ok=True)
        self.path: Path = path
        
        # "sia" is "image". See https://pyvo.readthedocs.io/en/latest/api/pyvo.registry.Servicetype.html#pyvo.registry.Servicetype
        self.dss_services = registry.search(registry.Servicetype('sia'), registry.Waveband('optical'), registry.Freetext("DSS"))
        
        self.in_processing: Set[str] = set()
        
    def get_fits(self, target: Target) -> Any:
        """Given a target name, get the image in the fov for the current observatory/telescope"""
        res = self._load_from_cache(target)
        if res is None:
            _, res = self._get_remote_fits(self.dss_services, self.observatories.observatory.fov, self.path, target)
        return res
        
    @staticmethod
    def _get_remote_fits(dss_services: registry.RegistryResults, fov: Tuple[float, float], save_path: Path, target: Target) -> Any:
        """Load image from the services"""
        log = logging.getLogger()
        log.debug("_get_remote_fits: %s", target.name)
        im_table = dss_services[0].search(pos=target.c, 
                                          size=[fov[0]*1.2, fov[1]*1.2],
                                          format='image/fits', intersect='COVERS')
        url = im_table[0].getdataurl()
        url = url.replace("pixels=300%2C300", "pixels=2000%2C2000")  # since we don't know a better way
        hdul = fits.open(url)
        if len(hdul) > 0:
            path = save_path.joinpath(f"{target.name}.fits")
            try:
                hdul[0].writeto(path)
                log.debug("_get_remote_fits: %s - image saved", target.name)
            except FileExistsError:
                # we are ok with this
                log.debug("_get_remote_fits: %s - failed to save image", target.name)
            return target.name, hdul[0]
        else:
            log.debug("_get_remote_fits: %s - could not load image", target.name)
            return target.name, None
    
    def _load_from_cache(self, target: Target) -> Any:
        path = self.path.joinpath(f"{target.name}.fits")
        if path.is_file():
            try:
                hdul = fits.open(path.as_posix())
                if hdul:
                    return hdul[0]
            except BaseException as err:  # pylint:disable=broad-exception-caught
                self.log.warning("While trying to load existing file '%s' and error was raised: %s", path.as_posix, str(err))
                return None
        else:
            return None
    
    def _save_to_cache(self, target: Target, hdu: Any) -> None:
        """Add first hdu from the hdu list and save the fits file to the cache directory."""
        path = self.path.joinpath(f"{target.name}.fits")
        hdu.writeto(path)

    def preload_images(self, targets: List[Target]) -> None:
        """Load a number of target images in parallel in background and return them as futures.
        
        This is ... iffy ... as it does not keep track of what is in the process of being loaded
        and what is done. We haven't done this (yet) as we will need some global state keeper,
        to keep a tally of what is being processed and what is not. This could be as "simple"
        as a global, always-alive, set but since we don't have global-always-alive things at the
        moment we will give it a miss atm. Danger is that we will have multiple threads loading
        the same objects and writing them over eachother. Luckily `fits.write` will not overwrite
        existing files so writing is as close to atomic as we can get. Fingers crossed.
        
        It also doesn't return immediately so we end up waiting for all the threads which may be
        annoying but we do get all the images in "parallel". Eventually.
        
        ..note:
        
            At the moment, this is only used by the `pre-populate-images.py` utility and should not
            be used anywhere else.
        """
        with concurrent.futures.ThreadPoolExecutor(thread_name_prefix="tofo_imagecache_") as executor:
            futures = []
            for target in targets:
                path = self.path.joinpath(f"{target.name}.fits")
                if target.name in self.in_processing or path.is_file():  # if we have the image or we are loading it
                    continue
                self.log.debug("Loading image for %s on a new thread", target.name)
                futures.append(executor.submit(self._get_remote_fits, 
                                               target=target, 
                                               dss_services=self.dss_services, 
                                               fov=self.observatories.observatory.fov,
                                               save_path=self.path))
