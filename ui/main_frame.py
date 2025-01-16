# -*- coding: UTF-8 -*-
# cSpell:ignore ridx irow rahms decdms mday Exoclock sizer Hmmmmm
import csv
from datetime import datetime
from typing import List

import numpy as np

import astropy.units as u
from astropy.coordinates import Angle
from astropy.time import Time

from astroplan.plots import plot_sky

from palettable.tableau import Tableau_20
from palettable.tableau import ColorBlind_10

import wx
import wx.adv
import wx.grid

from ui.target_dialog import TargetDialog
from tofo.observatory import Observatory
from tofo.targets import Target
from tofo.ui_mpl_canvas import MatplotlibCanvas


class MainFrame(wx.Frame):
    """The main UI frame."""
    
    def __init__(self, *args, **kwds):
        """Create the UI."""
        self.observatory: Observatory = kwds['observatory']
        del kwds['observatory']
        
        self.targets: List[Target] = []
        self.ax = None
        
        self.start_time: Time
        self.end_time: Time
        
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.SetSize((750, 900))
        self.SetTitle("Target of opportunity tool")

        ft_section = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.frame_menubar = wx.MenuBar()
        wxglade_tmp_menu = wx.Menu()
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "&Load Targets", "")
        self.Bind(wx.EVT_MENU, self.on_menu_load_targets, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "Find &Exoclock Targets", "")
        self.Bind(wx.EVT_MENU, self.on_menu_load_exoclock, item)
        item = wxglade_tmp_menu.Append(wx.ID_ANY, "&Exit", "")
        self.Bind(wx.EVT_MENU, self.on_menu_exit_app, item)
        self.frame_menubar.Append(wxglade_tmp_menu, "&File")
        self.SetMenuBar(self.frame_menubar)
        
        self.panel_main = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)
        self.panel_main.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        
        label_obs_title = wx.StaticText(self.panel_main, wx.ID_ANY, "Observation Date/Time")
        label_obs_title.SetFont(ft_section)
        sizer_main.Add(label_obs_title, 1, 0, 0)

        sizer_observation_dt = wx.FlexGridSizer(1, 12, 3, 0)
        sizer_main.Add(sizer_observation_dt, 1, wx.EXPAND, 0)
        sizer_observation_dt.Add((50, 40), 0, 0, 0)
        label_gdt_1 = wx.StaticText(self.panel_main, wx.ID_ANY, "Start Time")
        sizer_observation_dt.Add(label_gdt_1, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.dp_start = wx.adv.DatePickerCtrl(self.panel_main, wx.ID_ANY)
        sizer_observation_dt.Add(self.dp_start, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.tp_start = wx.adv.TimePickerCtrl(self.panel_main, wx.ID_ANY)
        sizer_observation_dt.Add(self.tp_start, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_observation_dt.Add((50, 20), 0, 0, 0)
        label_gdt_2 = wx.StaticText(self.panel_main, wx.ID_ANY, "End Time")
        sizer_observation_dt.Add(label_gdt_2, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.dp_end = wx.adv.DatePickerCtrl(self.panel_main, wx.ID_ANY)
        sizer_observation_dt.Add(self.dp_end, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        self.tp_end = wx.adv.TimePickerCtrl(self.panel_main, wx.ID_ANY)
        sizer_observation_dt.Add(self.tp_end, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_observation_dt.Add((50, 20), 0, 0, 0)
        self.bt_dt_apply_all = wx.Button(self.panel_main, wx.ID_ANY, "Apply to All")
        sizer_observation_dt.Add(self.bt_dt_apply_all, 0, wx.ALIGN_CENTER_VERTICAL| wx.ALIGN_CENTER, 0)
        sizer_observation_dt.Add((50, 20), 0, 0, 0)
        # target grid label
        label_targets_title = wx.StaticText(self.panel_main, wx.ID_ANY, "Targets")
        label_targets_title.SetFont(ft_section)
        sizer_main.Add(label_targets_title, 1, 0, 0)
        
        # target grid
        self.grid_targets: wx.grid.Grid = wx.grid.Grid(self.panel_main, wx.ID_ANY)
        self.grid_targets.SetMinSize((500,250))
        self.grid_targets.CreateGrid(0, 6)
        self.grid_targets.SetColLabelValue(0, "Name")
        self.grid_targets.SetColLabelValue(1, "Start Time")
        self.grid_targets.SetColLabelValue(2, "End Time")
        self.grid_targets.SetColLabelValue(3, "RA")
        self.grid_targets.SetColLabelValue(4, "DEC")
        self.grid_targets.SetColLabelValue(5, "All Vis")
        self.grid_targets.SetColSize(0, 25*5)
        self.grid_targets.SetColSize(1, 25*5)
        self.grid_targets.SetColSize(2, 25*5)
        self.grid_targets.SetColSize(3, 15*5)
        self.grid_targets.SetColSize(4, 15*5)
        sizer_main.Add(self.grid_targets, 5, wx.EXPAND, 0)

        # target grid manipulation buttons
        sizer_grid_target_bt = wx.GridSizer(1, 4, 0, 0)
        sizer_main.Add(sizer_grid_target_bt, 1, wx.EXPAND, 0)
        self.bt_add_row = wx.Button(self.panel_main, wx.ID_ANY, "Add Row")
        sizer_grid_target_bt.Add(self.bt_add_row, 0, wx.ALIGN_CENTER, 0)
        self.bt_del_row = wx.Button(self.panel_main, wx.ID_ANY, "Del Row")
        sizer_grid_target_bt.Add(self.bt_del_row, 0, wx.ALIGN_CENTER, 0)
        # self.cb_visible_at_all_times = wx.CheckBox(self.panel_main, wx.ID_ANY, "Show only full visibility")
        # self.cb_visible_at_all_times.SetValue(1)
        # sizer_grid_target_bt.Add(self.cb_visible_at_all_times, 0, wx.ALIGN_CENTER, 0)
        self.bt_refresh_targets = wx.Button(self.panel_main, wx.ID_ANY, "Refresh")
        self.bt_refresh_targets.SetDefault()
        sizer_grid_target_bt.Add(self.bt_refresh_targets, 0, wx.ALIGN_CENTER, 0)
        
        
        # visibility plot label
        sizer_tv = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_tv, 1, 0, 0)
        label_tv_title = wx.StaticText(self.panel_main, wx.ID_ANY, "Target Visibility")
        label_tv_title.SetFont(ft_section)
        sizer_tv.Add(label_tv_title, 0, wx.ALIGN_BOTTOM, 0)
        sizer_tv.Add((250, 40), 0, 0, 0)
        label_tv_sel_label = wx.StaticText(self.panel_main, wx.ID_ANY, "Selected: ")
        sizer_tv.Add(label_tv_sel_label, 0, wx.ALIGN_BOTTOM, 0)
        self.label_tv_selected = wx.StaticText(self.panel_main, wx.ID_ANY, "")
        self.label_tv_selected.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer_tv.Add(self.label_tv_selected, 0, wx.ALIGN_BOTTOM, 0)
        
        # visibility plot
        self.canvas = MatplotlibCanvas(self.panel_main, wx.ID_ANY)
        self.canvas.SetMinSize((500, 400))
        self.figure = self.canvas.figure
        sizer_main.Add(self.canvas, 10, wx.EXPAND, 0)
        
        # and we are done
        self.panel_main.SetSizer(sizer_main)
        self.Layout()

        # event bindings
        self.grid_targets.Bind(wx.grid.EVT_GRID_CMD_CELL_CHANGED, self.on_grid_targets_cell_change)
        self.grid_targets.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_grid_targets_cell_dclick)
        self.bt_refresh_targets.Bind(wx.EVT_BUTTON, self.on_bt_refresh_targets)
        self.bt_add_row.Bind(wx.EVT_BUTTON, self.on_bt_add_row)
        self.bt_del_row.Bind(wx.EVT_BUTTON, self.on_bt_del_row)
        self.dp_start.Bind(wx.adv.EVT_DATE_CHANGED, self.on_tdp_start_change)
        self.tp_start.Bind(wx.adv.EVT_TIME_CHANGED, self.on_tdp_start_change)
        self.dp_end.Bind(wx.adv.EVT_DATE_CHANGED, self.on_tdp_end_change)
        self.tp_end.Bind(wx.adv.EVT_TIME_CHANGED, self.on_tdp_end_change)
        self.bt_dt_apply_all.Bind(wx.EVT_BUTTON, self.on_bt_dt_apply_all)
        # canvas events
        self.canvas.mpl_connect( 'pick_event', self.on_canvas_pick)
        self._last_pick_mouseevent = None  # store info, as we will act only once per pick event
        # self.canvas.mpl_connect( 'motion_notify_event', self.on_canvas_mouse_move)
        
        # self.cb_visible_at_all_times.Bind(wx.EVT_CHECKBOX, self.on_checkbox_change)
        
        self.set_datetimes()
        self.vis_refresh_targets()

    
    ########################################
    # HELPERS

    def set_datetimes(self) -> None:
        """Set the possible observation times to civil darkness for today."""
        now = datetime.now()
        obs_time = Time(now.isoformat()[:10]+"T23:00:00.0")
        self.start_time = self.observatory.observer.twilight_evening_civil(obs_time)
        self.end_time = self.observatory.observer.twilight_morning_civil(obs_time)
        self.vis_refresh_datetimes()
   
    def plot_horizon(self):
        """Draw the horizon from the horizon file."""
        if not self.ax:
            self.ax = self.figure.add_subplot(1, 1, 1, projection='polar')
            # self.ax.set_prop_cycle('color', ColorBlind_10.mpl_colors)
        h = [(x[0]*np.pi/180.0, 90-x[1]) for x in self.observatory.horizon]
        theta = [x[0] for x in h]
        r = [x[1] for x in h]
        self.ax.set_theta_zero_location('N')
        self.ax.set_yticks(range(90, 0, -10))   
        self.ax.set_rlim(0, 90)
        self.ax.plot(theta, r)
        self.ax.set_rmax(90)
        self.ax.grid(True)

    def vis_refresh_targets(self):
        """Refresh all targets."""
        self.vis_update_target_grid_size()
        if self.ax:
            self.ax.cla()
        self.plot_horizon()
        
        colours = ColorBlind_10.mpl_colors
        
        have_targets: bool = False
        for ridx, target in enumerate(self.targets):
            self.vis_update_target_grid_row(ridx)
            if self.ax and target.transits:
                tds = target.get_transit_details()
                if tds:
                    obs_start = tds[0][0]
                    duration = (tds[0][-1] - tds[0][0]).to(u.hour)
                    plot_col = colours[ridx % len(colours)]
                    plot_sky(target.target, 
                             self.observatory.observer, 
                             obs_start + np.linspace(0, duration.value, 20)*u.hour, 
                             ax=self.ax,
                             style_kwargs={
                                's': 8,
                                'color': plot_col,
                                'picker': True
                            })
                    have_targets = True
        # if self.ax and have_targets:
        #    self.ax.legend(loc='lower left', bbox_to_anchor=(-0.4, 0.2))
        self.canvas.draw()
        
    def vis_update_target_grid_row(self, row_idx: int) -> None:
        """Update a row on the target grid with the data in the target list."""
        self.grid_targets.SelectRow(row_idx, True)
        self.grid_targets.ClearSelection()
        
        obj: Target = self.targets[row_idx]
        end_time = obj.observation_time + obj.observation_duration
        
        if obj.transits:
            col = wx.WHITE
        else:
            col = wx.LIGHT_GREY
        for i in range(self.grid_targets.GetNumberCols()):
            self.grid_targets.SetCellBackgroundColour(row_idx, i, col)
            
        self.grid_targets.SetCellValue(row_idx, 0, obj.name)
        self.grid_targets.SetCellValue(row_idx, 1, obj.observation_time.iso[:-7])
        self.grid_targets.SetCellValue(row_idx, 2, end_time.iso[:-7])
        self.grid_targets.SetCellValue(row_idx, 3, obj.ra_j2000)
        self.grid_targets.SetCellValue(row_idx, 4, obj.dec_j2000)
        self.grid_targets.SetCellValue(row_idx, 5, 'T' if obj.transits else 'F')

    def vis_refresh_datetimes(self) -> None:
        """Update the datetime widgets."""
        st = self.start_time.jd
        et = self.end_time.jd
        
        if et < st:
            wx.MessageBox("End time cannot be before start time!", "Like, Doh! Dude!", wx.OK | wx.ICON_ERROR)
            self.end_time = self.start_time + 1 * u.hour
            et = self.end_time.jd
        
        self.dp_start.SetValue(wx.DateTime.FromJDN(st))
        self.tp_start.SetValue(wx.DateTime.FromJDN(st))
        self.dp_end.SetValue(wx.DateTime.FromJDN(et))
        self.tp_end.SetValue(wx.DateTime.FromJDN(et))

    def vis_update_target_grid_size(self):
        """Resize the grid to match the data that we have."""
        current, new = (self.grid_targets.GetNumberRows(), len(self.targets))
        if new < current:
            self.grid_targets.DeleteRows(0, current-new, True)
        if new > current:
            self.grid_targets.AppendRows(new-current)

    ########################################
    # EVENT HANDLERS

    def on_menu_load_targets(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Load targets from a file."""
        with wx.FileDialog(self, "Open target file", wildcard="*.csv",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:

            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            pathname = file_dialog.GetPath()
            try:
                with open(pathname, 'r', encoding="utf-8") as file:
                    csv_reader = csv.reader(file) # pass the file object to reader() to get the reader object
                    targets_data = list(csv_reader)

                    self.targets = []
                    for t in targets_data:
                        name = t[0]
                        if len(t) > 1:
                            start_time = Time(t[1])
                            end_time = Time(t[2])
                        else:
                            start_time = self.start_time
                            end_time = self.end_time
                        if len(t) > 3:
                            ra = t[3]
                            dec = t[4]
                        else:
                            ra = ""
                            dec = ""
                        self.targets.append(Target(observatory=self.observatory,
                                                   name=name, 
                                                   observation_time=start_time, 
                                                   observation_duration=(end_time-start_time).to(u.hour),
                                                   ra_j2000=ra,
                                                   dec_j2000=dec))
                        
                    self.vis_refresh_targets()
                    self.Layout()
                    self.Refresh()
                    self.Update()
            except IOError:
                wx.LogError(f"Cannot open target file '{pathname}'")
                

    def on_menu_load_exoclock(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Load targets from exoclock."""
        pass

    def on_menu_exit_app(self, event):  # pylint:disable=unused-argument
        """Exit the app cleanly."""
        wx.CallAfter(self.Destroy)

    def on_tdp_start_change(self, event: wx.adv.DateEvent):  # pylint:disable=unused-argument
        """Get the date and time from the two separate pickers and create the start datetime from that."""
        tm1 = self.dp_start.GetValue().GetTm()
        tm2 = self.tp_start.GetValue().GetTm()
        self.start_time = Time(f"{tm1.year}-{tm1.mon+1:02d}-{tm1.mday:02d}T{tm2.hour}:{tm2.min}:{tm2.sec}")  # TODO: there has to be a nicer way!
        self.vis_refresh_datetimes()
        
    def on_tdp_end_change(self, event: wx.adv.DateEvent):  # pylint:disable=unused-argument
        """Get the date and time from the two separate pickers and create the end datetime from that."""
        tm1 = self.dp_end.GetValue().GetTm()
        tm2 = self.tp_end.GetValue().GetTm()
        self.end_time = Time(f"{tm1.year}-{tm1.mon+1:02d}-{tm1.mday:02d}T{tm2.hour}:{tm2.min}:{tm2.sec}")  # TODO: there has to be a nicer way!
        self.vis_refresh_datetimes()

    def on_bt_dt_apply_all(self, event: wx.CommandEvent|None=None):  # pylint:disable=unused-argument
        """Apply the global start/end times to all targets in the grid."""
        duration = (self.end_time - self.start_time).to(u.hour)
        
        for target in self.targets:
            target.observation_time = self.start_time
            target.observation_duration = duration
        
        self.vis_refresh_targets()

    def on_grid_targets_cell_change(self, event: wx.grid.GridEvent):
        """When the cell in the grid changes, we need to update things..."""
        r = event.GetRow()
        c = event.GetCol()
        value = self.grid_targets.GetCellValue(r, c)
        if c == 0:
            # the name of the target has changed.
            try:
                if value == "":
                    self.grid_targets.SetCellValue(r, c, self.targets[r].name)
                    wx.MessageBox("It is not possible to have an empty target name!\nReverting to previous value.", "Doh!", wx.ICON_ERROR | wx.OK)
                    return
                
                start_time = self.targets[r].observation_time
                d = self.targets[r].observation_duration
                nt = Target(observatory=self.observatory, 
                            name=value, 
                            observation_time=start_time,
                            observation_duration=d)
                has_details: bool = nt.lookup_object_details()
                if not has_details:
                    wx.MessageBox("Failed to load object details for the object.\nCheck the name and try again.", "Hmmmmm....", wx.OK|wx.ICON_QUESTION)
                self.targets[r] = nt
            except ValueError as e:
                wx.MessageBox(f'Failed to get coordinates for object {value}!\nPlease change it and try again.\n\nError:\n{e}', 'Like, Doh!', wx.OK | wx.ICON_ERROR)
        elif c == 1:
            self.targets[r].observation_time = Time(value)
        elif c == 2:
            et = Time(value)
            self.targets[r].observation_duration = (et-self.targets[r].observation_time).to(u.day)
        elif c == 3:
            ra = Angle(value).to_string()
            self.targets[r].ra_j2000 = ra
        elif c == 4:
            dec = Angle(value).to_string()
            self.targets[r].dec_j2000 = dec
        # you can't change c==5
        self.vis_refresh_targets()

    def on_grid_targets_cell_dclick(self, event: wx.grid.GridEvent):
        """Pop up TofO dialog for the selected target."""
        if not self.targets:
            return
        ridx = event.GetRow()
        d = TargetDialog(self, f"Targets of opportunity for '{self.targets[ridx].name}'")
        d.Show()
        d.init(observatory=self.observatory, target=self.targets[ridx])

    def on_bt_add_row(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Add a new row to the bottom of the targets grid."""
        self.grid_targets.AppendRows()
        new_target = Target(self.observatory, "", observation_time=self.start_time)
        new_target.observation_end_time = self.end_time
        self.targets.append(new_target)  # blank object
        
        self.vis_refresh_targets()
        
    def on_bt_del_row(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Delete selected row in the targets grid. If more than one is selected, only the first one will be deleted."""
        selected_rows = self.grid_targets.GetSelectedRows()
        if len(selected_rows) == 0:
            return
        self.grid_targets.DeleteRows(selected_rows[0])
        del self.targets[selected_rows[0]]
        
        self.vis_refresh_targets()

    def on_bt_refresh_targets(self, event: wx.CommandEvent|None=None):  # pylint:disable=unused-argument
        """Refresh all targets."""
        self.vis_refresh_targets()

    def on_cb_visibility_change(self, event: wx.CommandEvent):  # pylint:disable=unused-argument
        """Update the targets when the view only always visible/view all state has changed."""
        self.vis_refresh_targets()

    def on_canvas_pick(self, event):
        """Show what target was selected on the canvas"""
        artist = event.artist
        label = artist.get_label()
        print(label)
        if self._last_pick_mouseevent == label:
            return
        self._last_pick_mouseevent = label
        self.label_tv_selected.SetLabelText(label)
        # i = 0
        # for t in self.targets:
        #     if t.name == label:
        #         break
        #     i += 1
        # self.grid_targets.SelectRow(i)
        

    #def on_canvas_mouse_move(self, event):
    #    # display mouse pointer coordinates; based on code from NavigationToolbar2
    #    s = ""
    #    if event.inaxes and event.inaxes.get_navigate():
    #        try:
    #            xs = event.inaxes.format_xdata(event.xdata).strip()
    #            ys = event.inaxes.format_ydata(event.ydata).strip()
    #            s = "%s / %s"%(xs,ys)
    #        except (ValueError, OverflowError):
    #            pass
    #        else:
    #            if hasattr(event.inaxes, "_mouseover_set"):
    #                artists = [a for a in event.inaxes._mouseover_set if a.contains(event) and a.get_visible()]
    #            else:
    #                # old matplotlib versions
    #                artists = [a for a in event.inaxes.mouseover_set if a.contains(event) and a.get_visible()]#
    #
    #            if artists:
    #                a = cbook._topmost_artist(artists)
    #                if a is not event.inaxes.patch:
    #                    data = a.get_cursor_data(event)
    #                    if data is not None:
    #                        s += ' [%s]' % a.format_cursor_data(data)
    #                        
    #        print('on_move: ', s, str(event))