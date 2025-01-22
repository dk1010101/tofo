# -*- coding: UTF-8 -*-
# cSpell:ignore foo
import wx

class LoadingDialog(wx.Dialog):
    """ A popup dialog for temporary user messages """

    def __init__(self, parent, title, msg):
        # Create a dialog
        margin_size = 8
        wx.Dialog.__init__(self, parent, -1, title, size=(350, 150),style=wx.CAPTION | wx.STAY_ON_TOP)
        box = wx.BoxSizer(wx.VERTICAL)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        # Add an info icon
        bitmap = wx.Bitmap(32, 32)
        bitmap = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION,wx.ART_MESSAGE_BOX, (32, 32))
        graphic = wx.StaticBitmap(self, -1, bitmap)
        box2.Add(graphic, 0, wx.EXPAND|wx.ALL, margin_size)
        # Add the message
        self.message = wx.StaticText(self, -1, msg)
        box2.Add((10, 10), 0, wx.EXPAND|wx.ALL, margin_size)
        box2.Add(self.message, 0, wx.ALIGN_CENTRE_VERTICAL|wx.ALIGN_LEFT|wx.ALL, margin_size)
        box.Add(box2, 0, wx.EXPAND)
        # layout
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Fit()
        self.Layout()
        self.CentreOnScreen()
        # finally display the object
        self.Show()
        # Make sure the screen gets fully drawn before continuing.
        wx.Yield()
        
    def set_message(self, m: str) -> None:
        """Update the message on the dialog"""
        self.message.SetLabel(m)
        self.Refresh()
