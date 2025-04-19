from tkinter import Label, Toplevel


class Tooltip:
    def __init__(self, parent, widget=None, text=None):
        self.tw = None
        self.parent = parent
        
        # If widget and text are provided, set up the tooltip for this widget
        if widget and text:
            self._attach_to_widget(widget, text)

    def _attach_to_widget(self, widget, text):
        """Attach this tooltip to a widget"""
        widget.bind("<Enter>", lambda e: self.show_delayed(text, e.x_root, e.y_root))
        widget.bind("<Leave>", lambda e: self.hide())
        widget.bind("<Motion>", lambda e: self.update_position(e.x_root, e.y_root))
    
    def update_position(self, x, y):
        """Update the position of the tooltip"""
        if self.tw:
            self.tw.wm_geometry(f"+{x + 15}+{y + 15}")
            
    def show_delayed(self, text, x, y, delay=500):
        """Show the tooltip after a delay"""
        # Cancel any existing after calls
        if hasattr(self, '_after_id') and self._after_id:
            self.parent.after_cancel(self._after_id)
            
        # Schedule showing the tooltip
        self._after_id = self.parent.after(delay, lambda: self.show(text, x, y))
            
    def show(self, text, x, y):
        if self.tw:
            self.hide()
        self.tw = Toplevel(self.parent)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")
        label = Label(self.tw, text=text, justify="left",
                      background="#ffffe0", relief="solid",
                      borderwidth=1, font=("Arial", 9))
        label.pack(ipadx=4)

    def hide(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None
        
        # Cancel any pending show operations
        if hasattr(self, '_after_id') and self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None
