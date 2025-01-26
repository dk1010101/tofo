# -*- coding: UTF-8 -*-
# cSpell:ignore AAVSO NAXIS CUNIT1 CUNIT2 CDELT1 CDELT2 CRPIX1 CRPIX2 CRVAL1 CRVAL2 CROTA1 CROTA2 auid radec tomag hmsdms

import math
import copy 

import logging
import numpy as np
import pandas as pd

from regions import RectangleSkyRegion

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.wcs import WCS

from matplotlib.patches import Rectangle, Circle

import wx
# begin wxGlade: dependencies
import wx.grid
# end wxGlade

from ui.loading_dialog import LoadingDialog
from tofo.ui_mpl_canvas import MatplotlibCanvas
from tofo.observatory import Observatory
from tofo.targets import Target
from tofo.sources.object_db import ObjectDB


class TargetDialog(wx.Dialog):
    """Dialog for showing all targets of opportunity based on some central object of interest."""
    
    grid_col_spec = [('Name', 35*5), 
                     ('AUID', 16*5), 
                     ('RA deg', 10*5), 
                     ('DEC deg', 10*5), 
                     ('RA DEC', 31*5), 
                     ('Var Type', 13*5), 
                     ('Min Mag', 12*5), 
                     ('Max Mag', 12*5), 
                     ('Period', 12*5), 
                     ('Epoch', 16*5), 
                     ('Duration', 12*5), 
                     ('Event ISO', 24*5), 
                     ('Event JD', 19*5)]
    
    def __init__(self, parent, title="", win_size=(800,600)):
        self.log = logging.getLogger()
        self.loading_dalog: LoadingDialog
        self.observatory: Observatory
        self.objectdb: ObjectDB
        self.ax = None
        self.target: Target
        self.wcs: WCS = None
        self.df: pd.DataFrame
        
        # UI
        super(TargetDialog, self).__init__(parent, title=title, size=win_size)
        panel_main = wx.Panel(self)
        
        bold_font: wx.Font = panel_main.GetFont()
        bold_font.SetWeight(wx.FONTWEIGHT_BOLD)
        
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sizer_main_non_dialog = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.sizer_main_non_dialog, 20, wx.EXPAND, 0)
        
        # TOP - starfield plot and target details grid
        self.sz_top_grid: wx.GridSizer = wx.GridSizer(1, 2, 10, 0)
        self.sizer_main_non_dialog.Add(self.sz_top_grid, 2, wx.EXPAND, 0)
        # starfield plot
        self.canvas = MatplotlibCanvas(panel_main, wx.ID_ANY)
        self.canvas.SetMinSize((500, 500))
        self.figure = self.canvas.figure
        self.sz_top_grid.Add(self.canvas, 0, wx.ALL | wx.EXPAND, 0)
        # target details grid
        self.target_grid: wx.grid.Grid = wx.grid.Grid(panel_main, wx.ID_ANY)
        self.target_grid.CreateGrid(12, 2)
        self.target_grid.SetRowLabelSize(0)
        self.target_grid.SetColLabelValue(0, "Parameter")
        self.target_grid.SetColLabelValue(1, "Value")
        self.target_grid.SetColSize(0, 30*5)
        self.target_grid.SetColSize(1, 25*5)
        self.target_grid.SetCellValue(0, 0, "Name")
        self.target_grid.SetCellValue(1, 0, "Start time before Ingress")
        self.target_grid.SetCellValue(2, 0, "Transit Start")
        self.target_grid.SetCellValue(3, 0, "Mid-Transit")
        self.target_grid.SetCellValue(4, 0, "Transit End")
        self.target_grid.SetCellValue(5, 0, "End time after Egress")
        self.target_grid.SetCellValue(6, 0, "Mag V")
        self.target_grid.SetCellValue(7, 0, "Mag R")
        self.target_grid.SetCellValue(8, 0, "Mag Gaia G")
        self.target_grid.SetCellValue(9, 0, "Epoch")
        self.target_grid.SetCellValue(10, 0, "Period")
        self.target_grid.SetCellValue(11, 0, "Duration")

        for i in range(12):
            self.target_grid.SetCellFont(i, 0, bold_font)
        self.sz_top_grid.Add(self.target_grid, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL|wx.ALIGN_CENTRE_VERTICAL, 0)
        
        # targets grid
        self.grid_tofo: wx.grid.Grid = wx.grid.Grid(panel_main, wx.ID_ANY)
        self.grid_tofo.CreateGrid(5, len(TargetDialog.grid_col_spec))
        for idx, col in enumerate(TargetDialog.grid_col_spec):
            self.grid_tofo.SetColLabelValue(idx, col[0])
            self.grid_tofo.SetColSize(idx, col[1])
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

    def init(self, 
             observatory: Observatory, 
             objectdb: ObjectDB,
             target: Target, 
             loading_dlg: LoadingDialog):
        """Initialise the object. """
        with wx.BusyCursor():
            self.loading_dalog = loading_dlg
            self.target = target
            self.observatory: Observatory = observatory
            self.objectdb: ObjectDB = objectdb
            
            self.set_target()
            self.get_tofos()
    
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
        self.wcs = WCS(wcs_input_dict)
        rows = []
        target_list = self.objectdb.vsx.query_radius(target_ra, target_dec, radius, limiting_mag)
        for t in target_list:
            if sky_region:
                c = SkyCoord(ra=t.ra_deg * u.degree, dec=t.dec_deg * u.degree)
                if not sky_region.contains(c, self.wcs):
                    self.log.info("skipping %s since it is not in the sky region", t.name)
                    continue
            base_row = [t.name, 
                        t.auid,
                        t.ra_deg, t.dec_deg, t.c.to_string("hmsdms"),
                        t.var_type,
                        t.minmag, t.maxmag,
                        t.period, t.epoch, t.duration]
            if t.epoch is not None and t.period is not None:
                eph = self._get_eph(t.epoch, t.period, self.target.observation_time, self.target.observation_end_time)
                if eph:
                    for e in eph:
                        row = copy.deepcopy(base_row)
                        row.append(e.datetime.isoformat())
                        row.append(e.jd)
                        rows.append(row)
                else:
                    self.log.info("skipping %s since there are no events for this object. epoch=%s period=%s", base_row[0], t.epoch.iso, t.period.to_string())
            else:
                row = copy.deepcopy(base_row)
                row.append('')
                row.append(0.0)
        df = pd.DataFrame(rows, columns=['name', 'auid', 'ra_deg', 'dec_deg', 
                                         'radec', 'var_type', 'min_mag', 'max_mag', 
                                         'period', 'epoch', 'eclipse_duration',
                                         'event_iso', 'event_jd'])
        return df, self.wcs

    def _show_tofo(self, wcs: WCS):
        """Get a sky image for the field of view (120% of it) and then plot targets of opportunity on it."""    
        hdu = self.objectdb.get_fits(self.target)
        
        wcs_i = WCS(hdu.header)  # pylint:disable=no-member
        if wcs_i is not None:
            self.ax = self.figure.add_subplot(1, 1, 1, projection=wcs_i)
            self.ax.set(xlabel="RA", ylabel="Dec")
        else:
            self.ax = self.figure.add_subplot(1, 1, 1)
            self.ax.set(xlabel="x pixel", ylabel="y pixel")
        
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

    def set_target(self) -> None:
        """Add target values to the top-right grid."""
        if self.target is None:
            return
        td = self.target.get_transit_details()
        if not td:
            for i in range(11):
                self.target_grid.SetCellValue(i, 1, "")
            return
        transit = td[1]  # light-time adjusted
        self.target_grid.SetCellValue(0, 1, self.target.name)
        for i in range(1, 6):
            self.target_grid.SetCellValue(i, 1, transit[i-1].iso.split('.')[0])

        if self.target.epoch is not None:
            self.target_grid.SetCellValue(9, 1, f"{self.target.epoch.jd:.4f}")
        else:
            self.target_grid.SetCellValue(9, 1, "")
        if self.target.period is not None:
            self.target_grid.SetCellValue(10, 1, self.target.period.to_string())
        else:
            self.target_grid.SetCellValue(10, 1, "")
        if self.target.duration is not None:
            self.target_grid.SetCellValue(11, 1, self.target.duration.to_string())
        else:
            self.target_grid.SetCellValue(11, 1, "")
            
        self.target_grid.SetCellValue(6, 1, f"{self.target.mag_v:.3f}")
        self.target_grid.SetCellValue(7, 1, f"{self.target.mag_r:.3f}")
        self.target_grid.SetCellValue(8, 1, f"{self.target.mag_g:.3f}")
        
    
    def get_tofos(self):
        """Get all targets of opportunity, add them to the grid and plot them on the sky image."""
        self.loading_dalog.set_message("Loading targets...")
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
            self.grid_tofo.SetCellValue(ridx, 0, str(row[0]))  # name
            self.grid_tofo.SetCellValue(ridx, 1, str(row[1]))  # AUID is any
            self.grid_tofo.SetCellValue(ridx, 2, f"{float(row[2]):.2f}")  # RA in degrees
            self.grid_tofo.SetCellValue(ridx, 3, f"{float(row[3]):.2f}")  # DEC is degrees
            self.grid_tofo.SetCellValue(ridx, 4, str(row[4]))  # RA DEC as string
            self.grid_tofo.SetCellValue(ridx, 5, str(row[5]))  # Var Type as string
            self.grid_tofo.SetCellValue(ridx, 6, str(row[6]))  # MinMag as string
            self.grid_tofo.SetCellValue(ridx, 7, str(row[7]))  # MaxMag as string
            self.grid_tofo.SetCellValue(ridx, 8, row[8].round(2).to_string())  # Period as string
            self.grid_tofo.SetCellValue(ridx, 9, f"{float(row[9].jd):.4f}")  # Epoch as string
            self.grid_tofo.SetCellValue(ridx, 10, row[10].round(2).to_string())  # Duration as string
            self.grid_tofo.SetCellValue(ridx, 11, str(row[11][:-7]))  # Event ISO minus millisecond part as string
            self.grid_tofo.SetCellValue(ridx, 12, f"{float(row[12]):.4f}")  # Event JD as string
        
        self.loading_dalog.set_message("Loading sky image...")
        self._show_tofo(wcs)
        self.loading_dalog = None

    def _get_eph(self, epoch: Time, period: u.Quantity, start: Time, end: Time) -> list:
        """Get all events that fall between start and end times."""
        if np.isnan(period.value):
            return []
        p = period.to(u.day).value
        minn = int(np.ceil((start.jd - epoch.jd) / p))
        maxn = int(np.ceil((end.jd - epoch.jd) / p))
        r = [Time((epoch.jd + (n * p)), format='jd') for n in range(minn, maxn)]
        return r

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
