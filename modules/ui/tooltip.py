import tkinter as tk
from tkinter import Toplevel
#import logging

#logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class ToolTip:
    """
    A tooltip that displays after a delay if the pointer remains over the widget.
    Includes debug logging and a check for descendant widgets.
    """
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay  # delay in milliseconds
        self.tipwindow = None
        self.after_id = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.cancel, add="+")
        widget.bind("<ButtonPress>", self.cancel, add="+")

    def is_descendant(self, widget):
        current = widget
        while current:
            if current == self.widget:
                return True
            current = current.master
        return False

    def schedule(self, event=None):
       #logging.debug("ToolTip.schedule called")
        self.after_id = self.widget.after(self.delay, self.showtip)
       #logging.debug("Tooltip scheduled to show after %d ms; after_id=%s", self.delay, self.after_id)

    def cancel(self, event=None):
       #logging.debug("ToolTip.cancel called")
        if event:
            x, y = event.x_root, event.y_root
            widget_under = self.widget.winfo_containing(x, y)
            if widget_under and self.is_descendant(widget_under):
               #logging.debug("Pointer is still in widget or descendant; not canceling tooltip.")
                return
        if self.after_id:
            self.widget.after_cancel(self.after_id)
           #logging.debug("Canceled scheduled tooltip with after_id=%s", self.after_id)
            self.after_id = None
        self.hidetip()

    def showtip(self):
       #logging.debug("ToolTip.showtip called")
        if self.tipwindow or not self.text:
           #logging.debug("Aborting showtip: tipwindow exists or text is empty")
            return
        x = self.widget.winfo_rootx() + 30
        y = self.widget.winfo_rooty() + 20
       #logging.debug("Creating tooltip window at position (%d, %d) with text: '%s'", x, y, self.text)
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify="left",
                        background="#ffffe0", relief="solid", borderwidth=1,
                        font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
       #logging.debug("Tooltip window created")

    def hidetip(self):
       #logging.debug("ToolTip.hidetip called")
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
           #logging.debug("Tooltip window destroyed")