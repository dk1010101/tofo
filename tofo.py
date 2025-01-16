#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# pylint: disable=invalid-name

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import wx

from ui.main_frame import MainFrame
from lib.observatory import Observatory


class TOFOApp(wx.App):
    """Main Application"""    
    def __init__(self, observatory: Observatory, *args, **kwds):
        self.observatory = observatory
        super(TOFOApp, self).__init__(*args, **kwds)
        
    def OnInit(self):
        """Initialise the application"""
        self.frame = MainFrame(None, wx.ID_ANY, "", observatory=self.observatory)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

def load_observatory_data() -> Observatory:
    """Load the default observatory yaml file."""
    with open("observatory.yaml", "r", encoding="utf-8") as f:
        obsdata = load(f, Loader=Loader)
        return Observatory(obsdata)

if __name__ == "__main__":
    
    obsobj = load_observatory_data()
    TofO = TOFOApp(observatory=obsobj)
    TofO.MainLoop()
