# -*- coding: UTF-8 -*-

from typing import Any
import wx

from matplotlib.figure import Figure

_USE_AGG = True

if _USE_AGG :
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
else:
    from matplotlib.backends.backend_wx import FigureCanvasWx as FigureCanvas


class MatplotlibCanvas(FigureCanvas):
    """Simple wrapper around matplotlib to allow us to use it in our application."""
    def __init__(self, parent: Any, wxid: Any=wx.ID_ANY):
        """Create the canvas."""
        figure = self.figure = Figure()
        FigureCanvas.__init__(self, parent, wxid, figure)  # pylint:disable=too-many-function-args  # since it is ok, really

    def cleanup(self):
        """Tidy up at the end."""
        if not _USE_AGG:
            # avoid crash
            if self.renderer.gc.gfx_ctx:
                self.renderer.gc.gfx_ctx.Destroy()
                self.renderer.gc.gfx_ctx = None
