from tkinter import Label, Toplevel


class Tooltip:
    def __init__(self, parent):
        self.tw = None
        self.parent = parent

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
