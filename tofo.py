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
from tofo.observatory import Observatories
from tofo.sources.object_db import ObjectDB
from tofo.thread_with_return import ThreadWithReturnValue


class TOFOApp(wx.App):
    """Main Application"""
    scn_splash: TofoSplashScreen
    
    def __init__(self, observatories: Observatories, *args, **kwds):
        self.observatories = observatories
        super(TOFOApp, self).__init__(*args, **kwds)
    
    @staticmethod
    def load_object_db(obs: Observatories) -> ObjectDB:
        """This will take a LONG time to run!"""
        odb = ObjectDB(obs)
        return odb
    
    def OnInit(self):
        """Initialise the application"""
        self.frame = MainFrame(None, wx.ID_ANY, "", observatories=self.observatories)  # pylint:disable=attribute-defined-outside-init
        
        scn_splash = TofoSplashScreen()
        scn_splash.CenterOnScreen(wx.BOTH)
        scn_splash.Show(True)
        
        with wx.BusyCursor():
            # why threads? this does not work with the wx threads at all and is bunk.
            # TODO: make this work properly.
            dbloader_t = ThreadWithReturnValue(target=TOFOApp.load_object_db, args=(self.observatories,))
            dbloader_t.start()
            self.frame.objectdb = dbloader_t.join()
            
        scn_splash.Hide()
        scn_splash.Destroy()
        
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

def load_observatory_data() -> Observatories:
    """Load the default observatory yaml file."""
    with open("observatories.yaml", "r", encoding="utf-8") as f:
        obsdata = load(f, Loader=Loader)
        return Observatories(obsdata)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    matplotlib.pyplot.set_loglevel (level='warning')    
    
    obsobj = load_observatory_data()
    tofo = TOFOApp(observatories=obsobj)
    
    tofo.MainLoop()
