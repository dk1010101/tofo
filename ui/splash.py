import wx
from wx.adv import SplashScreen as SplashScreen


class TofoSplashScreen(SplashScreen):
    """
    Create a splash screen widget.
    """
    def __init__(self, parent=None):  # pylint:disable=unused-argument
        bitmap = wx.Bitmap(name="images/tofo_800.png", type=wx.BITMAP_TYPE_PNG)
        splash = wx.adv.SPLASH_CENTRE_ON_SCREEN | wx.adv.SPLASH_NO_TIMEOUT
        super(TofoSplashScreen, self).__init__(bitmap=bitmap,
                                               splashStyle=splash,
                                               milliseconds=0,
                                               parent=None,
                                               id=-1,
                                               pos=wx.DefaultPosition,
                                               size=wx.DefaultSize,
                                               style=wx.STAY_ON_TOP | wx.BORDER_NONE)
        self.Bind(wx.EVT_CLOSE, self.OnExit)
    #-----------------------------------------------------------------------
    def OnExit(self, event):
        event.Skip()  # Make sure the default handler runs too...
        self.Hide()
