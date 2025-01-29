#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# pylint: disable=invalid-name
import logging
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import matplotlib
import wx

from ui.main_frame import MainFrame
from ui.lib.splash import TofoSplashScreen
from tofo.observatory import Observatory
from tofo.sources.object_db import ObjectDB
from tofo.thread_with_return import ThreadWithReturnValue


class TOFOApp(wx.App):
    """Main Application"""
    scn_splash: TofoSplashScreen
    
    def __init__(self, observatory: Observatory, *args, **kwds):
        self.observatory = observatory
        super(TOFOApp, self).__init__(*args, **kwds)
    
    @staticmethod
    def load_object_db(obs: Observatory) -> ObjectDB:
        """This will take a LONG time to run!"""
        odb = ObjectDB(obs)
        return odb
    
    def OnInit(self):
        """Initialise the application"""
        self.frame = MainFrame(None, wx.ID_ANY, "", observatory=self.observatory)  # pylint:disable=attribute-defined-outside-init
        
        scn_splash = TofoSplashScreen()
        scn_splash.CenterOnScreen(wx.BOTH)
        scn_splash.Show(True)
        
        with wx.BusyCursor():
            # why threads? can we do this better? this whole thing is a mess!
            dbloader_t = ThreadWithReturnValue(target=TOFOApp.load_object_db, args=(self.observatory,))
            dbloader_t.start()
            self.frame.objectdb = dbloader_t.join()
            
        scn_splash.Hide()
        scn_splash.Destroy()
        
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

def load_observatory_data() -> Observatory:
    """Load the default observatory yaml file."""
    with open("observatory.yaml", "r", encoding="utf-8") as f:
        obsdata = load(f, Loader=Loader)
        return Observatory(obsdata)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    matplotlib.pyplot.set_loglevel (level='warning')    
    
    obsobj = load_observatory_data()
    TofO = TOFOApp(observatory=obsobj)
    
    TofO.MainLoop()
