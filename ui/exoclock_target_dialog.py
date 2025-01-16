import pandas as pd

import wx
import wx.adv



class ExoclockTargetDialog(wx.Dialog):
    def __init__(self, parent):
                
        super(ExoclockTargetDialog, self).__init__(parent, title="title", size=(400, 500))
        self.SetTitle("dialog")
        self.SetSize((400, 500))
        sizer_1 = wx.BoxSizer(wx.VERTICAL)

        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(sizer_3, 1, wx.EXPAND, 0)

        grid_sizer_1 = wx.FlexGridSizer(3, 3, 0, 0)
        sizer_3.Add(grid_sizer_1, 1, wx.EXPAND, 0)

        grid_sizer_1.Add((150, 0), 0, 0, 0)

        label_1 = wx.StaticText(self, wx.ID_ANY, "Telescope Diameter (inches) ")
        grid_sizer_1.Add(label_1, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)

        self.txt_telescope_diameter = wx.TextCtrl(self, wx.ID_ANY, "9.0")
        grid_sizer_1.Add(self.txt_telescope_diameter, 0, wx.EXPAND, 0)

        grid_sizer_1.Add((150, 0), 0, 0, 0)

        label_2 = wx.StaticText(self, wx.ID_ANY, "Observation Date ")
        grid_sizer_1.Add(label_2, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)

        self.datepicker_obsdate = wx.adv.DatePickerCtrl(self, wx.ID_ANY)
        grid_sizer_1.Add(self.datepicker_obsdate, 0, wx.EXPAND, 0)

        grid_sizer_1.Add((150, 0), 0, 0, 0)

        grid_sizer_1.Add((150, 0), 0, 0, 0)

        self.bt_find_targets = wx.Button(self, wx.ID_ANY, "Find Targets\n")
        grid_sizer_1.Add(self.bt_find_targets, 0, wx.EXPAND, 0)

        self.lst_targets = wx.ListCtrl(self, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
        self.lst_targets.AppendColumn("A", format=wx.LIST_FORMAT_LEFT, width=150)
        self.lst_targets.AppendColumn("B", format=wx.LIST_FORMAT_LEFT, width=150)
        self.lst_targets.AppendColumn("C", format=wx.LIST_FORMAT_LEFT, width=150)
        sizer_3.Add(self.lst_targets, 2, wx.EXPAND | wx.TOP, 0)

        static_line_1 = wx.StaticLine(self, wx.ID_ANY)
        sizer_1.Add(static_line_1, 1, wx.EXPAND, 0)

        sizer_2 = wx.StdDialogButtonSizer()
        sizer_1.Add(sizer_2, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

        self.button_CANCEL = wx.Button(self, wx.ID_CANCEL, "")
        sizer_2.AddButton(self.button_CANCEL)

        self.button_APPLY = wx.Button(self, wx.ID_APPLY, "")
        sizer_2.AddButton(self.button_APPLY)

        sizer_2.Realize()

        self.SetSizer(sizer_1)
        sizer_1.Fit(self)

        self.SetEscapeId(self.button_CANCEL.GetId())

        self.bt_find_targets.Bind(wx.EVT_BUTTON, self.on_find)

        self.Layout()
        
    def on_find(self, event):
        