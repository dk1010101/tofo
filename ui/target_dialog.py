# -*- coding: UTF-8 -*-
# cSpell:ignore AAVSO NAXIS CUNIT1 CUNIT2 CDELT1 CDELT2 CRPIX1 CRPIX2 CRVAL1 CRVAL2 CROTA1 CROTA2 auid radec tomag hmsdms

# TODO: add loading progress something

import math
import copy 

import requests
import numpy as np
import pandas as pd

from regions import RectangleSkyRegion

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import WCS
from astropy.io import fits

from pyvo import registry

from matplotlib.patches import Rectangle, Circle

import wx
# begin wxGlade: dependencies
import wx.grid
# end wxGlade

from tofo.ui_mpl_canvas import MatplotlibCanvas
from tofo.observatory import Observatory
from tofo.targets import Target


class TargetDialog(wx.Dialog):
    """Dialog for showing all targets of opportunity based on some central object of interest."""
    
    grid_col_names = ['Name', 'AUID', 'OID', 'Const', 'RA deg', 'DEC deg', 'RA DEC', 'Var Type', 'Min Mag', 'Max Mag', 'Period', 'Epoch', 'Duration', 'Spec Type', 'Event ISO', 'Event JD']
    
    def __init__(self, parent, title="", win_size=(800,800)):
        """Create the UI"""
        self.observatory: Observatory
        self.ax = None
        self.target: Target
        self.df: pd.DataFrame
        
        # UI
        super(TargetDialog, self).__init__(parent, title=title, size=win_size)
        panel_main = wx.Panel(self)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sizer_main_non_dialog = wx.BoxSizer(wx.VERTICAL)
        
        # starfield plot
        self.canvas = MatplotlibCanvas(panel_main, wx.ID_ANY)
        self.canvas.SetMinSize((500, 500))
        self.figure = self.canvas.figure
        self.sizer_main_non_dialog.Add(self.canvas, 0, wx.ALL | wx.EXPAND, 0)
        sizer_main.Add(self.sizer_main_non_dialog, 1, wx.EXPAND, 0)
        
        # targets grid
        self.grid_tofo: wx.grid.Grid = wx.grid.Grid(panel_main, wx.ID_ANY)
        self.grid_tofo.CreateGrid(5, len(TargetDialog.grid_col_names))
        for idx, name in enumerate(TargetDialog.grid_col_names):
            self.grid_tofo.SetColLabelValue(idx, name)
        self.sizer_main_non_dialog.Add(self.grid_tofo, 1, wx.EXPAND, 0) 
        
        # dialog buttons
        sizer_dlg_buttons = wx.StdDialogButtonSizer()
        sizer_main.Add(sizer_dlg_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.bt_save = wx.Button(panel_main, wx.ID_SAVE, "")
        self.bt_save.SetDefault()
        sizer_dlg_buttons.AddButton(self.bt_save)
        
        self.bt_close = wx.Button(panel_main, wx.ID_CLOSE, "")
        sizer_dlg_buttons.AddButton(self.bt_close)
        sizer_dlg_buttons.Realize()

        # main panel done
        panel_main.SetSizer(sizer_main)
        sizer_main.Fit(self)

        # event handlers
        self.SetAffirmativeId(self.bt_save.GetId())
        self.SetEscapeId(self.bt_close.GetId())
        self.bt_save.Bind(wx.EVT_BUTTON, self.on_bt_save)
        
        self.Layout()

    def init(self, observatory: Observatory, target: Target):
        """Initialise the object. """
        with wx.BusyCursor():
            self.target = target
            self.observatory: Observatory = observatory
            
            self.get_tofos()
    
    def on_bt_save(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Save the image and the data (if any)."""
        fname = f"{self.target.name}_{self.target.observation_time.datetime.isoformat()}".replace(":", "-")
        try:
            self.figure.savefig(fname+".png", dpi=300)
            with open(fname+'.txt', "w", encoding="utf-8") as f:
                f.writelines(self.df.to_string(float_format=lambda x: f"{x:.6f}"))
            wx.MessageBox(f'Saved data to {fname}.png and {fname}.txt', 'Save OK', wx.OK | wx.ICON_INFORMATION)
        except BaseException:  # pylint:disable=broad-exception-caught  # since we really do not care
            wx.MessageBox(f'Saved to {fname}.png and {fname}.txt failed!', 'Save Failed', wx.OK | wx.ICON_ERROR)
        
    def _get_eph(self, epoch: float, period: float, start: Time, end: Time) -> list:
        """Get all events that fall between start and end times."""
        minn = int(np.ceil((start.jd - epoch) / period))
        maxn = int(np.ceil((end.jd - epoch) / period))
        r = [Time((epoch + n * period), format='jd') for n in range(minn, maxn)]
        return r

    def _get_all_fov(self) -> pd.DataFrame:
        """Get all targets of opportunity that are held in the field of view."""
        target_ra = self.target.c.ra.deg
        target_dec = self.target.c.dec.deg
        
        radius = math.sqrt(self.observatory.sensor_size_px[0]**2 + self.observatory.sensor_size_px[1]**2) * abs(self.observatory.cdelt1/2.) # radius in degrees. Some solvers produce files with negative cdelt2
        if radius > 3.0: 
            limiting_mag = 12.0 # Required by AAVSO
        else:
            limiting_mag = self.observatory.limiting_mag

        sky_region = RectangleSkyRegion(center = self.target.c,
                                        width = self.observatory.fov[0] * 1.2,
                                        height = self.observatory.fov[1] * 1.2)
        wcs = None
        wcs_input_dict = {
            'NAXIS' : 2,
            'CTYPE1': 'RA---TAN', 
            'CUNIT1': 'deg', 
            'CDELT1': self.observatory.cdelt1, 
            'CRPIX1': self.observatory.sensor_size_px[0] / 2., 
            'CRVAL1': target_ra, 
            'CROTA1': self.observatory.crota1,
            'NAXIS1': self.observatory.sensor_size_px[0],
            'CTYPE2': 'DEC--TAN', 
            'CUNIT2': 'deg', 
            'CDELT2': self.observatory.cdelt2, 
            'CRPIX2': self.observatory.sensor_size_px[1] / 2., 
            'CRVAL2': target_dec, 
            'CROTA2': self.observatory.crota2,
            'NAXIS2': self.observatory.sensor_size_px[1]
        }
        wcs = WCS(wcs_input_dict)
        
        url= 'https://www.aavso.org/vsx/index.php'
        query = {
            'view': 'api.list',
            'ra': target_ra,
            'dec': target_dec,
            'radius': radius,
            'tomag': limiting_mag,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=query, timeout=30)
        except requests.exceptions.ReadTimeout:
            wx.MessageBox("Timeout while trying to get data from AAVSO.", "Oops!", wx.OK | wx.ICON_STOP)
            df = pd.DataFrame([], columns=['name', 'auid', 'oid', 'constellation', 'ra_deg', 'dec_deg', 
                                           'radec', 'var_type', 'min_mag', 'max_mag', 
                                           'period', 'epoch', 'eclipse_duration', 'spectral_type', 
                                           'event_iso', 'event_jd'])
            return df, wcs
        
        js = response.json()
        if 'VSXObjects' not in js:
            return []
        stars = js['VSXObjects']['VSXObject']
        
        rows = []
        for s in stars:
            n = s['Name']
            
            c = SkyCoord(ra=float(s['RA2000'])*u.degree, dec=float(s['Declination2000'])*u.degree)
            if sky_region:
                if not sky_region.contains(c, wcs):
                    print(f"skipping {n} since it is not in the sky region")
                    continue
            # grid_col_names = ['Name', 'AUID', 'OID', 'Const', 'RA deg', 'DEC deg', 
            #                   'RA DEC', 'Var Type', 'Min Mag', 'Max Mag', 
            #                   'Period', 'Epoch', 'Eclipse Duration', 'Spec Type', 
            #                   'Event ISO', 'Event JD']
    
            base_row = [
                s['Name'],
                s.get("AUID", ""),
                s.get("OID", ""),
                s.get('Constellation', ''),
                s['RA2000'], 
                s['Declination2000'], 
                c.to_string('hmsdms'),
                s.get('VariabilityType', 'NA'), 
                s.get('MinMag', ''), 
                s.get('MaxMag', ''),
                s.get("Period", np.nan),
                s.get("Epoch", np.nan),
                s.get("EclipseDuration", np.nan),
                s.get("SpectralType", ""),
            ]   
            if s.get("Epoch", False) and s.get("Period", False):
                eph = self._get_eph(float(s['Epoch']), float(s['Period']), self.target.observation_time, self.target.observation_end_time)
                if eph:
                    for e in eph:
                        row = copy.deepcopy(base_row)
                        row.append(e.datetime.isoformat())
                        row.append(e.jd)
                        rows.append(row)
                else:
                    print(f"skipping {n} since there are no events for this object. epoch={s['Epoch']} period={s['Period']}")
            else:
                row = copy.deepcopy(base_row)
                row.append('')
                row.append(0.0)
        df = pd.DataFrame(rows, columns=['name', 'auid', 'oid', 'constellation', 'ra_deg', 'dec_deg', 
                                         'radec', 'var_type', 'min_mag', 'max_mag', 
                                         'period', 'epoch', 'eclipse_duration', 'spectral_type', 
                                         'event_iso', 'event_jd'])
        return df, wcs

    def _show_tofo(self, wcs: WCS):
        """Get a sky image for the field of view (120% of it) and then plot targets of opportunity on it."""
        dss_services = registry.search(registry.Servicetype('image'), registry.Waveband('optical'), registry.Freetext("DSS"))
        im_table = dss_services[0].search(pos=self.target.c, 
                                          size=[self.observatory.fov[0]*1.2, self.observatory.fov[1]*1.2],
                                          format='image/fits', intersect='COVERS')
        url = im_table[0].getdataurl()
        url = url.replace("pixels=300%2C300", "pixels=2000%2C2000")  # since we don't know a better way
        
        hdu = fits.open(url)[0]

        wcs_i = WCS(hdu.header)  # pylint:disable=no-member
                
        # self.ax = self.figure.add_subplot(1, 1, 1, projection=wcs_i)
        self.ax = self.figure.add_subplot(1, 1, 1)
        
        # Plot the image
        self.ax.imshow(hdu.data)  # pylint:disable=no-member
        self.ax.set(xlabel="RA", ylabel="Dec")
        
        if len(self.df) == 0:
            return
        names = self.df['name'].to_list()
        times = self.df['event_iso'].to_list()
        maxmag = self.df['max_mag'].to_list()
        jd = list(map(lambda x: x - 2460000.0, self.df['event_jd'].to_list()))
        
        i = 0
        arr = wcs_i.world_to_pixel(SkyCoord(self.df['radec'].to_list()))
        for x, y in zip(arr[0], arr[1]):
            p = Circle((x, y), 10, color='y', fill=False, lw=1)
            self.ax.add_patch(p)
            t = times[i]
            tp = times[i].find('T')
            txt = f"{names[i]}\n{maxmag[i]}\n{t[tp+4:tp+4+7]} {jd[i]:.5f}"
            self.ax.text(x+15, y+22, txt, color='yellow', fontsize=6)
            i += 1  # yes, enumerate blah blah
        
        fp2 = wcs.calc_footprint()
        blc = SkyCoord(ra=fp2[0][0]*u.deg, dec=fp2[0][1]*u.deg)
        blcc = wcs_i.world_to_pixel(blc)
        p = Rectangle((blcc[0][()], blcc[1][()]), 
                      self.observatory.fov[0].value/wcs_i.wcs.cdelt[0], 
                      self.observatory.fov[1].value/wcs_i.wcs.cdelt[1], 
                      color='orange', fill=False, lw=1)
        self.ax.add_patch(p)
        self.ax.set_title(f"{self.target.name} - {self.target.observation_time.iso[:10]} - {2460000 + int(jd[0])}")

    def get_tofos(self):
        """Get all targets of opportunity, add them to the grid and plot them on the sky image."""
        self.df, wcs = self._get_all_fov()
        
        arr = self.df.to_numpy()
        current, new = (self.grid_tofo.GetNumberRows(), len(arr))
        if new < current:
            self.grid_tofo.DeleteRows(0, current-new, True)
        if new > current:
            self.grid_tofo.AppendRows(new-current)
        
        for ridx, row in enumerate(arr):
            self.grid_tofo.SelectRow(ridx, True)
            self.grid_tofo.ClearSelection()
            for cidx, val in enumerate(row):
                self.grid_tofo.SetCellValue(ridx, cidx, str(val))
        
        self._show_tofo(wcs)
        
        if len(self.df) == 0:
            wx.MessageBox(f'There are no targets of opportunity for {self.target.name}\nfor observations between {self.target.observation_time.iso[:16]} and {self.target.observation_end_time.iso[:16]}', 'Shame...', wx.OK | wx.ICON_WARNING)
