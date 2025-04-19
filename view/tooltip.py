from tkinter import Label, Toplevel, StringVar
import sys
import platform


class Tooltip:
    def __init__(self, parent, widget=None, text=None):
        self.tw = None
        self.parent = parent
        self._after_id = None
        self.text_var = None  # Will use StringVar for better text handling
        
        # Detect platform for platform-specific fixes
        self.is_macos = platform.system() == "Darwin"
        
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
        if self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None
            
        # Schedule showing the tooltip
        self._after_id = self.parent.after(delay, lambda: self.show(text, x, y))
            
    def show(self, text, x, y):
        """Show tooltip with text at given position"""
        # For debugging
        print(f"Showing tooltip with text: '{text}', platform: {platform.system()}")
        
        if self.tw:
            self.hide()
            
        # Ensure we have text to display
        if not text or text.strip() == "":
            print("No text to display in tooltip")
            return
            
        # Create tooltip window
        self.tw = Toplevel(self.parent)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x + 15}+{y + 15}")
        
        # MacOS specific handling
        if self.is_macos:
            self.tw.configure(background="#ffffe0", highlightbackground="#ffffe0")
            self.tw.wm_attributes("-alpha", 0.95)  # Slight transparency for better rendering
        
        # Make sure it appears on top
        self.tw.attributes("-topmost", True)
        
        # Use StringVar for better text tracking
        self.text_var = StringVar(self.tw)
        self.text_var.set(text)
        
        # Create and pack the label with the text
        label = Label(self.tw, textvariable=self.text_var, justify="left",
                      background="#ffffe0", foreground="black", relief="solid",
                      borderwidth=1, padx=5, pady=3)
                      
        # Use system font on macOS for better compatibility
        if self.is_macos:
            label.configure(font=("SF Pro", 12), wraplength=200)
        else:
            label.configure(font=("Arial", 9))
            
        label.pack(ipadx=6, ipady=4, fill="both", expand=True)
        
        # Force update to ensure tooltip appears correctly
        self.tw.update_idletasks()
        
        # Double-check text was set correctly
        if self.is_macos:
            self.parent.after(50, self._verify_tooltip_text)

    def _verify_tooltip_text(self):
        """Verify that tooltip text is visible (for macOS debugging)"""
        if self.tw and self.text_var:
            current_text = self.text_var.get()
            print(f"Tooltip text verification: '{current_text}'")
            # Force a text update to ensure visibility
            self.text_var.set(current_text)
            self.tw.update_idletasks()

    def hide(self):
        """Hide the tooltip"""
        # Cancel any pending show operations
        if self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None
            
        # Destroy tooltip window if it exists
        if self.tw:
            self.tw.destroy()
            self.tw = None
            self.text_var = None
