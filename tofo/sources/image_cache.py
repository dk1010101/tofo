# -*- coding: UTF-8 -*-
# cSpell:ignore 
import logging
from pathlib import Path
from typing import Any

from astropy.io import fits
from pyvo import registry

from tofo.targets import Target
from tofo.observatory import Observatory


class ImageCache():
    """Simple file-based cache for fist images."""
    def __init__(self, observatory: Observatory):
        self.log = logging.getLogger()
        self.observatory = observatory
        
        # get the cache directory for this observatory and sensor
        path = observatory.sources_cache_image_dir.joinpath(self.observatory.observer.name)
        path = path.joinpath(self.observatory.sensor_name)
        path.mkdir(parents=True, exist_ok=True)
        self.path: Path = path
        
    def get_fits(self, target: Target) -> Any:
        """Given a target name, get the image in the fov for the current observatory/telescope"""
        res = self._load_from_cache(target)
        if res is None:
            res = self._get_remote_fits(target)
        return res
        
    def _get_remote_fits(self, target: Target) -> Any:
        """"""
        dss_services = registry.search(registry.Servicetype('image'), registry.Waveband('optical'), registry.Freetext("DSS"))
        im_table = dss_services[0].search(pos=target.c, 
                                          size=[self.observatory.fov[0]*1.2, self.observatory.fov[1]*1.2],
                                          format='image/fits', intersect='COVERS')
        url = im_table[0].getdataurl()
        url = url.replace("pixels=300%2C300", "pixels=2000%2C2000")  # since we don't know a better way
        hdul = fits.open(url)
        self._save_to_cache(target, hdul)
        return hdul[0]
    
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
