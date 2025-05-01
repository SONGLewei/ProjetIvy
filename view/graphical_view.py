import os
import tkinter as tk
import tkinter.simpledialog as simpledialog
import tkinter.font
from tkinter import ttk, PhotoImage
from tkinter import messagebox
from ivy.ivy_bus import ivy_bus
from view.tooltip import Tooltip 
from tkinter import filedialog
from tkinter import Toplevel, Label, StringVar

class GraphicalView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application VMC")

        # Check if the icon file exists before setting it
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "photos", "icon.ico"
        )
        png_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "photos", "icon.png"
        )
        
        # Try to apply both icon methods for better cross-platform support
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        else:
            print(f"Warning: Icon file not found at {icon_path}")
            
        if os.path.exists(png_path):
            try:
                icon_img = PhotoImage(file=png_path)
                self.iconphoto(False, icon_img)
            except tk.TclError:
                print(f"Warning: Could not load icon as PhotoImage from {png_path}")
        else:
            print(f"Warning: PNG icon file not found at {png_path}")

        # Set initial window size
        window_width = 1280
        window_height = 720
        self.geometry(f"{window_width}x{window_height}")

        # Center the window on the screen
        self._center_window(window_width, window_height)

        self.currentFloorLabel = None
        self.floor_count = 0
        self.current_floor = None
        self.floor_buttons = []
        self.current_tool = 'select'  
        self.vent_role = None
        self.vent_color = None
        self.canvas_item_meta = {}
        self.tooltip = Tooltip(self)
        self.tooltips = []  # For storing button tooltips
        self.vent_tooltips = {}  # For storing vent tooltips by canvas item ID
        self.tool_buttons = {}  # Store tool buttons for styling
        self.disabled_tools = set()  # Track which tools are disabled

        # Onion skin related variables
        self.onion_skin_items = []  # To track items drawn as part of onion skin
        self.onion_skin_opacity = 0.3  # 30% opacity for onion skin items

        self.hover_after_id = None
        self.current_hover_item = None 
        self.height_text_id = None
        self.current_floor_height = None
        
        # Placement tooltip for showing element info during placement
        self.placement_tooltip = None
        self.placement_tooltip_text = StringVar(self)
        self.placement_element_type = None

        self.text_id = None

        self.colors = {
            "topbar_bg": "white",  # White top bar
            "main_bg": "#f5f7fa",  # Light gray for main background
            "canvas_bg": "white",  # White canvas background
            "toolbar_bg": "#f0f0f0",  # Light gray for toolbar
            "button_bg": "#ffffff",  # White for buttons
            "selected_tool": "#dde1f7",  # Modern UI blue color
            "selected_floor": "#f0f3ff",  # Light blue for selected floor
            "unselected_floor": "white",  # White for unselected floor
            "floor_text": "#2f3039",  # Dark gray for floor text
            "disabled_tool": "#e0e0e0",  # Light gray for disabled tools
        }

        self.icons = {}
        self._load_icons()
        self._setup_style()
        self._create_layout()

        self.bind("<Configure>", self._on_window_configure)
        
        # Add Esc key binding to cancel drawing operations
        self.bind("<Escape>", self.on_escape_key)

        # Subscribe to events from controller
        ivy_bus.subscribe("draw_wall_update",         self.on_draw_wall_update)
        ivy_bus.subscribe("floor_selected_update",    self.on_floor_selected_update)
        ivy_bus.subscribe("new_floor_update",         self.on_new_floor_update)
        ivy_bus.subscribe("tool_selected_update",     self.on_tool_selected_update)
        ivy_bus.subscribe("show_alert_request",       self.on_show_alert_request)
        ivy_bus.subscribe("draw_window_update",       self.on_draw_window_update)
        ivy_bus.subscribe("draw_door_update",         self.on_draw_door_update)
        ivy_bus.subscribe("vent_need_info_request",   self.on_vent_need_info_request)
        ivy_bus.subscribe("draw_vent_update",         self.on_draw_vent_update)
        ivy_bus.subscribe("floor_height_update",      self.on_floor_height_update)
        ivy_bus.subscribe("onion_skin_preview_update", self.on_onion_skin_preview_update)
        ivy_bus.subscribe("clear_canvas_update",      self.on_clear_canvas_update)
        ivy_bus.subscribe("ventilation_summary_update", self.populate_ventilation_summary)
        ivy_bus.subscribe("ensure_onion_skin_refresh", self.on_ensure_onion_skin_refresh)
        ivy_bus.subscribe("draw_plenum_update",         self.on_draw_plenum_update)
        ivy_bus.subscribe("disable_tool_button",        self.on_disable_tool_button)
        ivy_bus.subscribe("enable_tool_button",         self.on_enable_tool_button)


        # Set initial cursor
        self.current_tool = 'select'  # Default tool

        # Request the initial floor information from the controller
        self.after(100, self._request_initial_floor)
        self.after(100, self._update_cursor)

        # Highlight the select tool button initially and notify controller
        self.after(200, lambda: self._highlight_tool_button('select'))
        self.after(200, lambda: ivy_bus.publish("tool_selected_request", {"tool": 'select'}))
        
        # Make window appear in front of other applications - macOS specific approach
        self.focus_force()  # Force focus on this window
        self.after(100, self._bring_to_front)  # Delay to ensure window is fully created

    def _bring_to_front(self):
        """Ensures the window appears in front of other applications on macOS"""
        self.lift()  # Raise window in stacking order
        self.attributes('-topmost', True)  # Make window stay on top
        self.focus_force()  # Force focus again after topmost
        # After a short delay, turn off topmost to allow other windows to go in front when needed
        self.after(100, lambda: self.attributes('-topmost', False))

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 10), padding=6, foreground="black")
        style.configure("FloorLabel.TLabel", font=("Arial", 13, "bold"), foreground="#333333", background="white")
        style.configure("Floor.TButton", font=("Helvetica", 11), padding=8)
        style.configure("SelectedFloor.TButton", font=("Helvetica", 11, "bold"), padding=8, background="#e8eeff")
        style.map("SelectedFloor.TButton", background=[("active", "#d8e0ff")])

    def _load_icons(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_paths = {
            'select': os.path.join(base_path, 'photos', 'select.png'),
            'eraser': os.path.join(base_path, 'photos', 'eraser.png'),
            'wall':   os.path.join(base_path, 'photos', 'wall.png'),
            'window': os.path.join(base_path, 'photos', 'window.png'),
            'door':   os.path.join(base_path, 'photos', 'door.png'),
            'vent':   os.path.join(base_path, 'photos', 'fan.png'),
            'plenum': os.path.join(base_path, 'photos', 'plenum.png'),
            'save':   os.path.join(base_path, 'photos', 'diskette.png'),
            'import': os.path.join(base_path, 'photos', 'import.png'),
            'document': os.path.join(base_path, 'photos', 'document.png'),
            'reset': os.path.join(base_path, 'photos', 'broom.png'),
        }
        for name, path in icon_paths.items():
            try:
                # Load original image without subsampling
                icon = PhotoImage(file=path)
                # Resize to fit within toolbar buttons
                icon = self._resize_image(icon, 32, 32)  # Slightly smaller than button to have some padding
                self.icons[name] = icon
            except Exception as e:
                print(f"fail to load {name} : {e}")

    def _resize_image(self, img, width, height):
        """Resize an image to the specified dimensions"""
        # Get original dimensions
        original_width = img.width()
        original_height = img.height()

        # Calculate subsample rates
        width_subsample = max(1, int(original_width / width))
        height_subsample = max(1, int(original_height / height))

        # Use the larger subsample rate to ensure the image fits
        subsample = max(width_subsample, height_subsample)

        return img.subsample(subsample, subsample)

    def _create_layout(self):
        # 3 parts of the UI
        self._create_top_bar()
        self._create_main_area()
        self._create_bottom_toolbar()

    def _create_top_bar(self):
        # Create top bar with white background
        topBarFrame = tk.Frame(self, bg=self.colors["topbar_bg"])
        topBarFrame.pack(side=tk.TOP, fill=tk.X)

        # Add a left frame for the Save and Import buttons
        leftFrame = tk.Frame(topBarFrame, bg=self.colors["topbar_bg"])
        leftFrame.pack(side=tk.LEFT, padx=(20, 0), pady=10)

        # Create Save button
        save_btn_frame = tk.Frame(leftFrame, bg=self.colors["topbar_bg"])
        save_btn_frame.pack(side=tk.LEFT, padx=(0, 10))

        save_canvas = tk.Canvas(
            save_btn_frame,
            width=45,
            height=45,
            bg="white",
            highlightthickness=0,
            cursor="hand2"
        )
        save_canvas.pack()

        # Add Save icon
        if 'save' in self.icons:
            save_canvas.create_image(45//2, 45//2, image=self.icons['save'])

        # Bind click event
        save_canvas.bind("<Button-1>", lambda e: self.on_save_button_click())

        # Create tooltip for Save button
        save_tooltip = Tooltip(self)
        save_tooltip._attach_to_widget(save_canvas, "Sauvegarder")
        self.tooltips.append(save_tooltip)

        # Create Import button
        import_btn_frame = tk.Frame(leftFrame, bg=self.colors["topbar_bg"])
        import_btn_frame.pack(side=tk.LEFT, padx=(0, 10))

        import_canvas = tk.Canvas(
            import_btn_frame,
            width=45,
            height=45,
            bg="white",
            highlightthickness=0,
            cursor="hand2"
        )
        import_canvas.pack()

        # Add Import icon
        if 'import' in self.icons:
            import_canvas.create_image(45//2, 45//2, image=self.icons['import'])

        # Bind click event
        import_canvas.bind("<Button-1>", lambda e: self.on_import_button_click())

        # Create tooltip for Import button
        import_tooltip = Tooltip(self)
        import_tooltip._attach_to_widget(import_canvas, "Importer")
        self.tooltips.append(import_tooltip)

        # Create Document button
        document_btn_frame = tk.Frame(leftFrame, bg=self.colors["topbar_bg"])
        document_btn_frame.pack(side=tk.LEFT)

        document_canvas = tk.Canvas(
            document_btn_frame,
            width=45,
            height=45,
            bg="white",
            highlightthickness=0,
            cursor="hand2"
        )
        document_canvas.pack()

        # Add Document icon
        if 'document' in self.icons:
            document_canvas.create_image(45//2, 45//2, image=self.icons['document'])

        # Bind click event
        document_canvas.bind("<Button-1>", lambda e: self.on_document_button_click())

        # Create tooltip for Document button
        document_tooltip = Tooltip(self)
        document_tooltip._attach_to_widget(document_canvas, "Vue textuelle")
        self.tooltips.append(document_tooltip)

        # Create Reset button
        reset_btn_frame = tk.Frame(leftFrame, bg=self.colors["topbar_bg"])
        reset_btn_frame.pack(side=tk.LEFT, padx=(5, 0))

        reset_canvas = tk.Canvas(
            reset_btn_frame,
            width=45,
            height=45,
            bg="white",
            highlightthickness=0,
            cursor="hand2"
        )
        reset_canvas.pack()

        # Add Reset icon
        if 'reset' in self.icons:
            reset_canvas.create_image(45//2, 45//2, image=self.icons['reset'])

        # Bind click event
        reset_canvas.bind("<Button-1>", lambda e: self.on_reset_button_click())

        # Create tooltip for Reset button
        reset_tooltip = Tooltip(self)
        reset_tooltip._attach_to_widget(reset_canvas, "Réinitialiser")
        self.tooltips.append(reset_tooltip)

        # Continue with the center frame and other elements
        centerFrame = tk.Frame(topBarFrame, bg=self.colors["topbar_bg"])
        centerFrame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Create label with white background
        label_frame = tk.Frame(centerFrame, bg="white", padx=15, pady=8)
        label_frame.pack(anchor="center", pady=5)

        self.currentFloorLabel = ttk.Label(label_frame,
                                           text="Aucun etage selectionne",
                                           style="FloorLabel.TLabel")
        self.currentFloorLabel.pack(anchor="center")

        # New floor button with plus icon and rounded corners
        new_floor_canvas = tk.Canvas(
            topBarFrame,
            width=130,
            height=40,
            bg=self.colors["topbar_bg"],
            highlightthickness=0,
            cursor="hand2"  # Add pointer cursor
        )
        new_floor_canvas.pack(side=tk.RIGHT, padx=(10, 20), pady=10)

        # Draw rounded rectangle with 5px radius
        radius = 5
        button_color = "#6bbb6d"

        # Create rounded corners using ovals
        new_floor_canvas.create_oval(0, 0, 2*radius, 2*radius, fill=button_color, outline="")
        new_floor_canvas.create_oval(130-2*radius, 0, 130, 2*radius, fill=button_color, outline="")
        new_floor_canvas.create_oval(0, 40-2*radius, 2*radius, 40, fill=button_color, outline="")
        new_floor_canvas.create_oval(130-2*radius, 40-2*radius, 130, 40, fill=button_color, outline="")

        # Create rectangles to complete the rounded shape
        new_floor_canvas.create_rectangle(radius, 0, 130-radius, 40, fill=button_color, outline="")
        new_floor_canvas.create_rectangle(0, radius, 130, 40-radius, fill=button_color, outline="")

        # Add text
        new_floor_canvas.create_text(
            65, 20,
            text="+ Nouvel etage",
            fill="white",
            font=("Helvetica", 12, "bold")
        )

        # Bind click event
        new_floor_canvas.bind("<Button-1>", lambda e: self.on_new_floor_button_click())

    def _create_main_area(self):
        mainFrame = tk.Frame(self, bg="white")  # Main frame background
        mainFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # left part with white background
        drawWrap = tk.Frame(mainFrame, bg="white")
        drawWrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0), pady=(0, 0))

        # Create scrollbars but don't pack them - they'll be functional but invisible
        vbar = ttk.Scrollbar(drawWrap, orient="vertical")
        hbar = ttk.Scrollbar(drawWrap, orient="horizontal")

        # Load grid background image
        grid_img_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "photos", "grid.png"
        )
        if os.path.exists(grid_img_path):
            try:
                self.grid_image = PhotoImage(file=grid_img_path)
                # Set the grid image resolution
                self.grid_image = self.grid_image.subsample(2, 2)  # Reduce resolution by half
                self.use_grid_background = True
            except tk.TclError:
                print(f"Warning: Could not load grid image from {grid_img_path}")
                self.use_grid_background = False
        else:
            print(f"Warning: Grid image file not found at {grid_img_path}")
            self.use_grid_background = False

        # Create canvas with border on right and bottom
        self.canvas = tk.Canvas(
            drawWrap, bg="white", highlightthickness=1,
            highlightbackground="#cccccc",
            xscrollcommand=hbar.set, yscrollcommand=vbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Connect scrollbars to canvas (without displaying them)
        vbar.config(command=self._on_canvas_y_scroll)
        hbar.config(command=self._on_canvas_x_scroll)

        # Initialize background tile image IDs to track and update them
        self.bg_tile_ids = []
        
        def _on_canvas_configure(evt):
            self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 0, 0))
            self._redraw_height_text()
            # Redraw the background grid when canvas size changes
            self._update_grid_background()

        self.canvas.bind("<Configure>", _on_canvas_configure)

        # Bind mousewheel events for scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_y)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)
        # For Linux/macOS
        self.canvas.bind("<Button-4>", self._on_button4)
        self.canvas.bind("<Button-5>", self._on_button5)
        self.canvas.bind("<Shift-Button-4>", self._on_shift_button4)
        self.canvas.bind("<Shift-Button-5>", self._on_shift_button5)

        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>",   self.on_canvas_move)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # Create compass layer
        self._create_compass_layer(drawWrap)

        # Vertical separator line instead of ttk.Separator
        sep_frame = tk.Frame(mainFrame, width=1, bg="#cccccc")
        sep_frame.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 0))  # Removed top padding

        # Right panel container with borders on top and bottom
        rightContainer = tk.Frame(mainFrame, bg="white", width=200)  # Increased from 150 to 160
        rightContainer.pack(side=tk.RIGHT, fill=tk.Y, padx=0, pady=(0, 0))  # Removed top padding
        rightContainer.pack_propagate(False)  # Prevent the container from shrinking

        # Top border for right panel - we're keeping this one
        tk.Frame(rightContainer, height=1, bg="#cccccc").pack(side=tk.TOP, fill=tk.X)

        # Main scrollable area for floors
        scrollWrap = tk.Frame(rightContainer, bg="white")
        scrollWrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)  # Add padding inside the container

        # Add a "etage" label at the top of the floor list
        floor_title = tk.Label(scrollWrap, text="Etage(s) :", font=("Helvetica", 14), fg="#2f3039", bg="white")
        floor_title.pack(side=tk.TOP, anchor="w", pady=(10, 10))

        self.floorCanvas = tk.Canvas(
            scrollWrap, bg="white", highlightthickness=0, width=130
        )

        # Create scrollbar but don't pack it yet
        self.floor_vsb = ttk.Scrollbar(scrollWrap, orient="vertical", command=self.floorCanvas.yview)
        self.floorCanvas.configure(yscrollcommand=self._on_floor_scroll)

        # Pack the canvas first
        self.floorCanvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create the floor frame
        self.floorFrame = tk.Frame(self.floorCanvas, bg="white")
        self.floorCanvas.create_window((0, 0), window=self.floorFrame, anchor="nw")

        # Restore the mousewheel bindings for scrolling
        def _on_mousewheel(event):
            self.floorCanvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Windows / Linux
        self.floorCanvas.bind_all("<MouseWheel>", _on_mousewheel)
        # macOS
        self.floorCanvas.bind_all("<Button-4>", _on_mousewheel)
        self.floorCanvas.bind_all("<Button-5>", _on_mousewheel)

        # Bottom border for right panel
        tk.Frame(rightContainer, height=1, bg="#cccccc").pack(side=tk.BOTTOM, fill=tk.X)
        
    # Custom scroll handlers that update grid when scrolling
    def _on_canvas_x_scroll(self, *args):
        self.canvas.xview(*args)
        # After scrolling, update the grid background
        self.after(10, self._update_grid_background)
        
    def _on_canvas_y_scroll(self, *args):
        self.canvas.yview(*args)
        # After scrolling, update the grid background
        self.after(10, self._update_grid_background)
        
    def _on_mousewheel_y(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.after(10, self._update_grid_background)
        
    def _on_mousewheel_x(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        self.after(10, self._update_grid_background)
        
    def _on_button4(self, event):
        self.canvas.yview_scroll(-1, "units")
        self.after(10, self._update_grid_background)
        
    def _on_button5(self, event):
        self.canvas.yview_scroll(1, "units")
        self.after(10, self._update_grid_background)
        
    def _on_shift_button4(self, event):
        self.canvas.xview_scroll(-1, "units")
        self.after(10, self._update_grid_background)
        
    def _on_shift_button5(self, event):
        self.canvas.xview_scroll(1, "units")
        self.after(10, self._update_grid_background)

    def _create_compass_layer(self, parent_frame):
        self.compass_canvas = tk.Canvas(parent_frame, width=80, height=120,
                                        bg="white", highlightthickness=0, 
                                        cursor="arrow")  # Use arrow cursor to indicate it's not clickable

        self.compass_canvas.place(x=1, y=1)  # Added 1px margin from the border

        center_x = 40
        center_y = 40
        radius = 20

        self.compass_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline='black', width=2
        )
        self.compass_canvas.create_line(
            center_x, center_y - radius, center_x, center_y + radius, width=2, fill='black'
        )
        self.compass_canvas.create_line(
            center_x - radius, center_y, center_x + radius, center_y, width=2, fill='black'
        )
        self.compass_canvas.create_text(
            center_x, center_y - radius - 10,
            text='N', font=('Helvetica', 8, 'bold'), fill='black'
        )
        self.compass_canvas.create_text(
            center_x + radius + 10, center_y,
            text='E', font=('Helvetica', 8, 'bold'), fill='black'
        )
        self.compass_canvas.create_text(
            center_x, center_y + radius + 10,
            text='S', font=('Helvetica', 8, 'bold'), fill='black'
        )
        self.compass_canvas.create_text(
            center_x - radius - 10, center_y,
            text='O', font=('Helvetica', 8, 'bold'), fill='black'
        )

        line_y = center_y + radius + 25
        line_length_px = 40
        start_x = center_x - (line_length_px // 2)
        end_x   = center_x + (line_length_px // 2)

        self.compass_canvas.create_text(
            center_x, line_y,
            text="2m", font=("Helvetica", 9, "bold"),
            fill='black'
        )

        self.compass_canvas.create_line(
            start_x, line_y + 10, end_x, line_y + 10, width=2, fill="black"
        )

    def _create_bottom_toolbar(self):
        toolbarFrame = tk.Frame(self, bg=self.colors["toolbar_bg"])
        toolbarFrame.pack(side=tk.BOTTOM, fill=tk.X)  # Increased bottom margin to 20px

        leftSpace = tk.Label(toolbarFrame, bg=self.colors["toolbar_bg"])
        leftSpace.pack(side=tk.LEFT, fill=tk.X, expand=True)

        iconFrame = tk.Frame(toolbarFrame, bg=self.colors["toolbar_bg"])
        iconFrame.pack(side=tk.LEFT, pady=10)  # Add vertical padding to the icon frame

        # Tool names in French (direct constant strings for better reliability)
        tool_buttons = [
            ('select', 'Selection'),
            ('eraser', 'Gomme'),
            ('wall', 'Mur'),
            ('window', 'Fenêtre'),
            ('door', 'Porte'),
            ('vent', 'Ventilation'),
            ('plenum','Plenum')
        ]

        # Create buttons with tooltips
        for tool_id, tooltip_text in tool_buttons:
            # Create button container with fixed size of 45x45
            btn_container = tk.Frame(iconFrame, bg=self.colors["toolbar_bg"], width=50, height=50)
            btn_container.pack(side=tk.LEFT, padx=4, pady=(15, 30)) 
            btn_container.pack_propagate(False)  # Prevent resizing based on content

            # Create rounded button using Canvas
            canvas = tk.Canvas(
                btn_container,
                width=50,
                height=50,
                bg=self.colors["toolbar_bg"],
                highlightthickness=0,
                bd=0,
                cursor="hand2"  # Add pointer cursor
            )
            canvas.pack(fill=tk.BOTH, expand=True)

            # Draw rounded rectangle (simulating rounded corners)
            radius = 10  # 15px radius as requested
            canvas.create_oval(0, 0, 2*radius, 2*radius, fill=self.colors["button_bg"], outline="")
            canvas.create_oval(45-2*radius, 0, 45, 2*radius, fill=self.colors["button_bg"], outline="")
            canvas.create_oval(0, 45-2*radius, 2*radius, 45, fill=self.colors["button_bg"], outline="")
            canvas.create_oval(45-2*radius, 45-2*radius, 45, 45, fill=self.colors["button_bg"], outline="")

            # Draw rectangles to complete the rounded shape
            canvas.create_rectangle(radius, 0, 45-radius, 45, fill=self.colors["button_bg"], outline="")
            canvas.create_rectangle(0, radius, 45, 45-radius, fill=self.colors["button_bg"], outline="")

            # Create icon on the canvas
            icon = self.icons.get(tool_id)
            if icon:
                icon_id = canvas.create_image(45//2, 45//2, image=icon)

            # Bind click events
            canvas.bind("<Button-1>", lambda event, tool=tool_id: self.on_tool_button_click(tool))

            # Store button reference - we now store the canvas instead of a label
            self.tool_buttons[tool_id] = canvas

            # Create tooltip - explicit instance creation
            tooltip = Tooltip(self)
            tooltip._attach_to_widget(canvas, tooltip_text)

            # Store tooltip reference to prevent garbage collection
            self.tooltips.append(tooltip)

        rightSpace = tk.Label(toolbarFrame, bg=self.colors["toolbar_bg"])
        rightSpace.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --------------------------------- Handle events ------------------------------------------------
    def on_canvas_left_click(self, event):
        # Convert window coordinates to canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_click": True
            })

        if self.current_tool == "window":
            ivy_bus.publish("draw_window_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_click": True
            })

        if self.current_tool == "door":
            ivy_bus.publish("draw_door_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_click": True
            })

        if self.current_tool == "vent":
            if not self.vent_role:
                self.on_show_alert_request({
                    "title": "Type de ventilation non selectionne",
                    "message": "Veuillez d'abord choisir un type de ventilation."
                })
                return
            ivy_bus.publish("draw_vent_request", {
                "x": canvas_x, 
                "y": canvas_y,
                "is_click": True,
                "role": self.vent_role,
                "color": self.vent_color
            })
        if self.current_tool == "eraser":
            items = self.canvas.find_overlapping(
                canvas_x, canvas_y, canvas_x, canvas_y
            )
            if not items:
                return

            # Find items that are not part of the onion skin or background
            valid_items = []
            for item in items:
                tags = self.canvas.gettags(item)
                if "onion_skin" not in tags and "background" not in tags:
                    valid_items.append(item)

            if not valid_items:
                return

            # Get the topmost non-onion, non-background item
            item = valid_items[-1]
            tags = self.canvas.gettags(item)
            if not tags:
                return

            obj_type = tags[0]
            coords = self.canvas.coords(item)
            
            # For vents, we need to clean up any associated metadata
            if obj_type == "vent" and item in self.canvas_item_meta:
                # Remove from metadata dictionary
                if item in self.canvas_item_meta:
                    del self.canvas_item_meta[item]
                # Remove from vent tooltips if present
                if item in self.vent_tooltips:
                    del self.vent_tooltips[item]
            
            # Delete the item
            self.canvas.delete(item)

            # Notify controller about the deletion
            ivy_bus.publish("delete_item_request", {
                "type": obj_type,
                "coords": coords
            })
            
        if self.current_tool == "plenum":
            self.plenum_start_x = self.canvas.canvasx(event.x)
            self.plenum_start_y = self.canvas.canvasy(event.y)
            self.temp_plenum = None

        

    def on_canvas_move(self, event):
        # Convert window coordinates to canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_preview": True
            })
            # Update placement tooltip position
            if self.placement_tooltip:
                self.placement_tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        if self.current_tool == "window":
            ivy_bus.publish("draw_window_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_preview": True
            })
            # Update placement tooltip position
            if self.placement_tooltip:
                self.placement_tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        if self.current_tool == "door":
            ivy_bus.publish("draw_door_request", {
                "x": canvas_x,
                "y": canvas_y,
                "is_preview": True
            })
            # Update placement tooltip position
            if self.placement_tooltip:
                self.placement_tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        if self.current_tool == "vent" and self.vent_role:
            ivy_bus.publish("draw_vent_request", {
                "x": canvas_x, 
                "y": canvas_y,
                "is_preview": True,
                "role": self.vent_role,
                "color": self.vent_color
            })
            # Update placement tooltip position
            if self.placement_tooltip:
                self.placement_tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")
        
        if self.current_tool == "plenum" and hasattr(self, "plenum_start_x") and self.plenum_start_x is not None:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            if self.temp_plenum:
                self.canvas.delete(self.temp_plenum)

            self.temp_plenum = self.canvas.create_rectangle(
                self.plenum_start_x, self.plenum_start_y,
                end_x, end_y,
                outline="blue", dash=(4, 2), width=2, tags=("plenum_preview",)
            )
            
            # Calculate the plenum area for placement tooltip
            width_px = abs(end_x - self.plenum_start_x)
            height_px = abs(end_y - self.plenum_start_y)
            
            # Convert to square meters based on scale (40px = 2m)
            width_m = width_px * (2.0/40.0)
            height_m = height_px * (2.0/40.0)
            area_m2 = width_m * height_m
            
            # Format area to display exactly 2 decimal places
            formatted_area = f"{area_m2:.2f}"
            
            # Show area in placement tooltip
            self._show_placement_tooltip("Plenum", formatted_area, is_dimension=True)
            
            # Update placement tooltip position
            if self.placement_tooltip:
                self.placement_tooltip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 15}")

        self._handle_hover(event)

    # the case to cancel the wall when draw
    def on_canvas_right_click(self,event):
        if self.current_tool == "wall":
            ivy_bus.publish("cancal_to_draw_wall_request",{})
            self._hide_placement_tooltip()

        if self.current_tool == "window":
            ivy_bus.publish("cancal_to_draw_window_request",{})
            self._hide_placement_tooltip()

        if self.current_tool == "door":
            ivy_bus.publish("cancal_to_draw_door_request",{})
            self._hide_placement_tooltip()

        if self.current_tool == "vent":
            ivy_bus.publish("cancal_to_draw_vent_request", {})
            self._hide_placement_tooltip()
            
        if self.current_tool == "plenum" and hasattr(self, "plenum_start_x") and self.plenum_start_x is not None:
            # Cancel the plenum drawing
            if hasattr(self, "temp_plenum") and self.temp_plenum:
                self.canvas.delete(self.temp_plenum)
                self.temp_plenum = None
            self.plenum_start_x = None
            self.plenum_start_y = None
            self._hide_placement_tooltip()
            # Notify controller to cancel plenum creation
            ivy_bus.publish("cancel_plenum_request", {})
            print("[View] Plenum drawing cancelled by right-click")

    def on_canvas_release(self, event):
        if self.current_tool == "plenum" and hasattr(self, "plenum_start_x") and self.plenum_start_x is not None:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            if self.temp_plenum:
                self.canvas.delete(self.temp_plenum)
                self.temp_plenum = None
                
            # Hide placement tooltip
            self._hide_placement_tooltip()

            ivy_bus.publish("create_plenum_request", {
                "start_x": self.plenum_start_x,
                "start_y": self.plenum_start_y,
                "end_x": end_x,
                "end_y": end_y
            })

            self.plenum_start_x = None
            self.plenum_start_y = None

    def on_new_floor_button_click(self):
        ivy_bus.publish("new_floor_request", {})

    def on_tool_button_click(self, tool, event=None):
        # Check if tool is disabled
        if tool in self.disabled_tools:
            # Show alert that this tool is disabled
            self.on_show_alert_request({
                "title": "Outil indisponible",
                "message": "Plenum déjà présent"
            })
            return

        # Reset previous tool button appearance
        if self.current_tool and self.current_tool in self.tool_buttons:
            canvas = self.tool_buttons[self.current_tool]
            # Update all shapes on the canvas to use the default background color
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["button_bg"])

        # Update local tool state
        self.current_tool = tool

        # Highlight selected tool button
        if tool in self.tool_buttons:
            canvas = self.tool_buttons[tool]
            # Update all shapes on the canvas to use the selected color
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["selected_tool"])

        # Update cursor
        self._update_cursor()

        # Handle vent tool specially
        if tool == "vent":
            ivy_bus.publish("tool_selected_request", {"tool": tool})
            self.show_vent_type_menu()
        else:
            ivy_bus.publish("tool_selected_request", {"tool": tool})

    def on_floor_button_click(self, floor_index):
        ivy_bus.publish("floor_selected_request", {
            "floor_index": floor_index
        })

    def on_floor_button_right_click(self, event, floor_index):
        menu = tk.Menu(self, tearoff=0)

        menu.add_command(
            label="Renommer",
            command=lambda: self.on_rename_floor(floor_index)
        )

        menu.add_command(
            label="Definir la hauteur",
            command=lambda: self.on_set_height(floor_index)
        )

        menu.add_separator()

        menu.add_command(
            label="Supprimer",
            command=lambda: self.on_delete_floor(floor_index)
        )

        menu.tk_popup(event.x_root, event.y_root)

    def on_rename_floor(self, floor_index):
        new_name = simpledialog.askstring(
            title="Renommer l'etage",
            prompt="Entrez le nouveau nom de l'etage : "
        )

        if new_name:
            ivy_bus.publish("rename_floor_request", {
                "floor_index": floor_index,
                "new_name": new_name
            })

    def show_vent_type_menu(self):
        menu = tk.Menu(self, tearoff=0)

        vent_options = [
            ("En rouge, extraction de l'air vicie", "#ff0000", "extraction_interne"),
            (
                "En orange, insufflation de l'air neuf",
                "#ff9900",
                "insufflation_interne",
            ),
            (
                "En bleu fonce, extraction a l'exterieur",
                "#4c7093",
                "extraction_externe",
            ),
            (
                "En bleu clair, admission d'air neuf exterieur",
                "#66ccff",
                "admission_externe",
            ),
        ]

        for label, color, role in vent_options:
            menu.add_command(
                label=label,
                background=color,
                foreground="white",
                command=lambda r=role, c=color: self.on_vent_type_selected(r, c)
            )

        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def on_vent_type_selected(self, role, color):
        self.vent_role = role
        self.vent_color = color

    # ----------------------------- GET FROM CONTROLLER --------------------------------------------------------
    def on_draw_wall_update(self, data):
        """
        Called when the Controller publishes 'draw_wall_update' to actually operate the Canvas to draw the wall
        """
        start = data.get("start")
        end   = data.get("end")
        fill  = data.get("fill")

        if fill == "gray":
            if hasattr(self,"temp_line"):
                self.canvas.delete(self.temp_line)
            self.temp_line = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="gray", dash=(4, 2) ,width=5               
            )
            
            # Calculate length for placement tooltip
            if start != (0, 0) or end != (0, 0):  # Only update if not resetting
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length_px = (dx**2 + dy**2)**0.5
                length_m = length_px * (2.0/40.0)  # Convert to meters based on scale
                self._show_placement_tooltip("Mur", length_m)

        else:
            # Clear any existing temporary lines
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line
                self._hide_placement_tooltip()  # Hide tooltip when placement is done

            # If starting points are (0,0) and ending points are (0,0), this is likely 
            # a reset or deletion operation, so we don't need to draw anything
            if start == (0, 0) and end == (0, 0):
                # This might be a deletion operation, make sure onion skin is refreshed
                self._ensure_onion_skin_below()
                # Also request a fresh onion skin to ensure it's displayed correctly
                self.after(100, self._request_onion_skin_preview)
                return

            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=fill ,width=6,tags=("wall",)
            )

            # Calculate wall length in meters (using scale where 40px = 2m from _create_compass_layer)
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_px = (dx**2 + dy**2)**0.5
            length_m = length_px * (2.0/40.0)  # Convert to meters based on scale

            # Store length data for tooltip
            self.canvas_item_meta[item] = {
                'text': f"{length_m:.2f}m",
                'type': 'wall'
            }

            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # Ensure all onion skin items remain below
            self._ensure_onion_skin_below()

    def on_draw_window_update(self,data):
        start = data.get("start")
        end   = data.get("end")
        fill  = data.get("fill")
        thickness = data.get("thickness")

        if fill == "gray":
            if hasattr(self,"temp_line"):
                self.canvas.delete(self.temp_line)
            self.temp_line = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="gray", dash=(4, 2), width=thickness               
            )
            
            # Calculate length for placement tooltip
            if start != (0, 0) or end != (0, 0):  # Only update if not resetting
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length_px = (dx**2 + dy**2)**0.5
                length_m = length_px * (2.0/40.0)  # Convert to meters based on scale
                self._show_placement_tooltip("Fenêtre", length_m)

        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line
                self._hide_placement_tooltip()  # Hide tooltip when placement is done

            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=fill ,width=thickness, tags=("window",)
            )

            # Calculate window length in meters (using scale where 40px = 2m from _create_compass_layer)
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_px = (dx**2 + dy**2)**0.5
            length_m = length_px * (2.0/40.0)  # Convert to meters based on scale

            # Store length data for tooltip
            self.canvas_item_meta[item] = {
                'text': f"{length_m:.2f}m",
                'type': 'window'
            }

            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # Ensure all onion skin items remain below
            self._ensure_onion_skin_below()

    def on_draw_door_update(self,data):
        start = data.get("start")
        end   = data.get("end")
        fill  = data.get("fill")
        thickness = data.get("thickness")

        if fill == "gray":
            if hasattr(self,"temp_line"):
                self.canvas.delete(self.temp_line)
            self.temp_line = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="gray", dash=(4, 2), width=thickness
            )
            
            # Calculate length for placement tooltip
            if start != (0, 0) or end != (0, 0):  # Only update if not resetting
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length_px = (dx**2 + dy**2)**0.5
                length_m = length_px * (2.0/40.0)  # Convert to meters based on scale
                self._show_placement_tooltip("Porte", length_m)

        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line
                self._hide_placement_tooltip()  # Hide tooltip when placement is done

            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=fill,width=thickness,tags=("door",)
            )

            # Calculate door length in meters (using scale where 40px = 2m from _create_compass_layer)
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_px = (dx**2 + dy**2)**0.5
            length_m = length_px * (2.0/40.0)  # Convert to meters based on scale

            # Store length data for tooltip
            self.canvas_item_meta[item] = {
                'text': f"{length_m:.2f}m",
                'type': 'door'
            }

            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # Ensure all onion skin items remain below
            self._ensure_onion_skin_below()

    def on_draw_vent_update(self, data):
        start, end = data["start"], data["end"]
        color      = data.get("color", "gray")

        if color == "gray":
            if hasattr(self, "temp_vent"):
                self.canvas.delete(self.temp_vent)
            
            # Calculate the radius based on the distance between start and end points
            import math
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            radius = math.sqrt(dx*dx + dy*dy)
            
            # Draw a circle with dashed outline
            self.temp_vent = self.canvas.create_oval(
                start[0] - radius, start[1] - radius,
                start[0] + radius, start[1] + radius,
                outline="gray", dash=(4, 2), width=2, fill=""
            )
            
            # Calculate dimensions for placement tooltip
            if start != (0, 0) or end != (0, 0):  # Only update if not resetting
                # Convert dimensions to meters based on scale (40px = 2m)
                diameter_m = radius * 2 * (2.0/40.0)  # Convert to meters based on scale
                
                # Get the correct vent type name
                vent_type = "Ventilation"
                if hasattr(self, "vent_role"):
                    role_map = {
                        "insufflation_interne": "Insuff. Interne",
                        "insufflation_externe": "Insuff. Externe",
                        "extraction_interne": "Extract. Interne",
                        "extraction_externe": "Extract. Externe"
                    }
                    if self.vent_role in role_map:
                        vent_type = role_map[self.vent_role]
                
                # Show dimensions instead of length
                dimension = f"{diameter_m:.2f}x{diameter_m:.2f}"
                self._show_placement_tooltip(vent_type, dimension, is_dimension=True)

        else:
            if hasattr(self, "temp_vent"):
                self.canvas.delete(self.temp_vent)
                del self.temp_vent
                self._hide_placement_tooltip()  # Hide tooltip when placement is done

            # Calculate the radius based on the distance between start and end points
            import math
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            radius = math.sqrt(dx*dx + dy*dy)
            
            # Create a hollow circle with the specified color
            item = self.canvas.create_oval(
                start[0] - radius, start[1] - radius,
                start[0] + radius, start[1] + radius,
                outline=color, width=2, fill="", tags=("vent",)
            )

            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # Create well-formatted tooltip content with explicit strings
            name = data.get('name', '')
            diameter = data.get('diameter', '')
            flow = data.get('flow', '')
            role = data.get('role', '')

            meta = f"{name}\nO {diameter} mm\n{flow} m3/h\n{role}"

            # Ensure meta data is not empty
            if meta and meta.strip():
                # Store both formatted text and individual components
                self.canvas_item_meta[item] = {
                    'text': meta,
                    'name': name,
                    'diameter': diameter,
                    'flow': flow,
                    'role': role,
                    'type': 'vent'  # Add type field for consistency
                }

            # Ensure all onion skin items remain below
            self._ensure_onion_skin_below()

    def on_vent_need_info_request(self, data):
        start, end = data["start"], data["end"]
        role, color = data["role"], data["color"]

        # Get vent name - name can be any text but must not be empty
        name = simpledialog.askstring("Nom de la ventilation", "Entrez le nom de la ventilation :")
        if not name or name.strip() == "":
            self.on_show_alert_request({
                "title": "Entree invalide",
                "message": "Le nom de la ventilation ne peut pas être vide."
            })
            ivy_bus.publish("cancal_to_draw_vent_request", {})
            return

        # Validate diameter is an integer
        while True:
            diameter = simpledialog.askstring("Diamètre (mm)", "Entrez le diamètre de la ventilation (mm) :")
            if diameter is None:  # User cancelled
                ivy_bus.publish("cancal_to_draw_vent_request", {})
                return

            # Check if input is a valid integer
            if not diameter.strip():
                self.on_show_alert_request({
                    "title": "Entree invalide",
                    "message": "Le diamètre ne peut pas être vide."
                })
                continue

            if not diameter.isdigit():
                self.on_show_alert_request({
                    "title": "Entree invalide",
                    "message": "Le diamètre doit être un nombre entier positif."
                })
                continue

            # Valid integer, break out of the loop
            break

        # Validate flow rate is an integer
        while True:
            flow = simpledialog.askstring("Debit d'air (m³/h)", "Entrez le debit d'air (m³/h) :")
            if flow is None:  # User cancelled
                ivy_bus.publish("cancal_to_draw_vent_request", {})
                return

            # Check if input is a valid integer
            if not flow.strip():
                self.on_show_alert_request({
                    "title": "Entree invalide",
                    "message": "Le debit d'air ne peut pas être vide."
                })
                continue

            if not flow.isdigit():
                self.on_show_alert_request({
                    "title": "Entree invalide",
                    "message": "Le debit d'air doit être un nombre entier positif."
                })
                continue

            # Valid integer, break out of the loop
            break

        ivy_bus.publish("create_vent_request", {
            "start": start, "end": end,
            "name": name, "diameter": diameter, "flow": flow,
            "role": role, "color": color
        })

    def on_floor_selected_update(self, data):
        """
        data = {
        "selected_floor_index": <int>,
        "floor_name": "Floor 2"
        }
        """
        floor_name = data.get("floor_name")
        selected_index = data.get("selected_floor_index")
        
        # Update the current floor index
        self.current_floor = selected_index

        # Update the label text
        self.currentFloorLabel.config(text=f"Etage selectionne : {floor_name}")

        # Update the styling of floor buttons
        for i, btn_frame in enumerate(self.floor_buttons):
            # Find the canvas in the button frame
            canvas = None
            for widget in btn_frame.winfo_children():
                if isinstance(widget, tk.Canvas):
                    canvas = widget
                    break

            if canvas and hasattr(canvas, 'shape_id') and hasattr(canvas, 'text_id'):
                # Update button appearance based on selection state
                is_selected = (i == selected_index)
                bg_color = self.colors["selected_floor"] if is_selected else "white"

                # Update the shape color for all canvas items that are shapes
                for item in canvas.find_all():
                    if canvas.type(item) in ["rectangle", "oval", "polygon"] and item != canvas.text_id:
                        canvas.itemconfig(item, fill=bg_color, outline=bg_color)

                # Update text weight and possibly truncate text again with new font weight
                font_spec = ("Helvetica", 11, "bold" if is_selected else "normal")

                # Get the available width for text
                available_width = 200 - 20  # Container width minus padding
                text_padding = 20
                max_text_width = available_width - (text_padding * 2)

                # Get the full text and truncate if needed
                if hasattr(canvas, 'full_text'):
                    full_text = canvas.full_text
                else:
                    full_text = canvas.itemcget(canvas.text_id, 'text')
                    if full_text.endswith('...'):  # Best effort to recover original text
                        full_text = floor_name

                display_text = self._truncate_text_with_ellipsis(full_text, max_text_width, font_spec)

                # Update text and font
                canvas.itemconfig(canvas.text_id, 
                                  text=display_text,
                                  font=font_spec)

        # After updating floor, request onion skin if available
        self.after(10, self._request_onion_skin_preview)

    def on_new_floor_update(self, data):
        """
        data = {
        "floors": ["Floor 1", "Floor 2", ...],
        "selected_floor_index": <int>
        }
        """
        floors = data.get("floors", [])
        selected_index = data.get("selected_floor_index", None)

        # Clear existing buttons
        for btn in self.floor_buttons:
            for widget in btn.winfo_children():
                widget.destroy()
            btn.destroy()

        self.floor_buttons = []

        # Create new buttons with the custom style
        for i, floor_name in enumerate(floors):
            # Create a frame for each button with white background
            btn_frame = tk.Frame(self.floorFrame, bg="white")
            btn_frame.pack(side=tk.TOP, fill=tk.X, pady=3, padx=0)

            # Create button with rounded corners using a canvas
            button_height = 40

            # Calculate available width - use full width
            available_width = 200 - 20  # Container width minus padding (10px on each side)

            canvas = tk.Canvas(
                btn_frame, 
                height=button_height,
                width=available_width,
                bg="white",
                highlightthickness=0,
                cursor="hand2"
            )
            canvas.pack(fill=tk.X)

            # Determine if this is the selected button
            is_selected = (i == selected_index)
            button_bg = self.colors["selected_floor"] if is_selected else "white"

            # Update to match the "+ Nouvel etage" button radius (5px)
            radius = 5  # Changed from 20 to 5 to match the "+ Nouvel etage" button

            # Define the box with some padding
            x1 = 5
            y1 = 5
            x2 = available_width - 5
            y2 = button_height - 5

            # Create rounded corners using ovals (similar to "+ Nouvel etage" button)
            canvas.create_oval(x1, y1, x1 + 2*radius, y1 + 2*radius, fill=button_bg, outline="")
            canvas.create_oval(x2 - 2*radius, y1, x2, y1 + 2*radius, fill=button_bg, outline="")
            canvas.create_oval(x1, y2 - 2*radius, x1 + 2*radius, y2, fill=button_bg, outline="")
            canvas.create_oval(x2 - 2*radius, y2 - 2*radius, x2, y2, fill=button_bg, outline="")

            # Create rectangles to complete the rounded shape
            canvas.create_rectangle(x1 + radius, y1, x2 - radius, y1 + 2*radius, fill=button_bg, outline="")  # Top
            canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=button_bg, outline="")  # Middle
            canvas.create_rectangle(x1 + radius, y2 - 2*radius, x2 - radius, y2, fill=button_bg, outline="")  # Bottom

            # Store the background shape ID (use the first rectangle as reference)
            shape_id = canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=button_bg, outline="")
            canvas.tag_lower(shape_id)  # Move it to the back

            # Add text, left-aligned with padding
            text_padding = 20
            max_text_width = available_width - (text_padding * 2)  # Available width for text
            font_spec = ("Helvetica", 12, "bold" if is_selected else "normal")

            # Truncate text if needed
            display_text = self._truncate_text_with_ellipsis(floor_name, max_text_width, font_spec)

            text_id = canvas.create_text(
                text_padding,
                button_height / 2,
                text=display_text, 
                anchor="w",  # Left-aligned
                fill=self.colors["floor_text"],
                font=font_spec
            )

            # Store IDs for later updates
            canvas.tag_raise(text_id)   # Ensure text is on top

            # Save references to the shape and text for easy updates
            canvas.shape_id = shape_id
            canvas.text_id = text_id
            canvas.full_text = floor_name  # Store the original full text

            # Bind click events
            canvas.bind("<Button-1>", lambda e, idx=i: self.on_floor_button_click(idx))
            canvas.bind("<Button-2>", lambda e, idx=i: self.on_floor_button_right_click(e, idx))  # For macOS
            canvas.bind("<Button-3>", lambda e, idx=i: self.on_floor_button_right_click(e, idx))  # For Windows/Linux
            
            # For Control+click on macOS (another way to right-click)
            canvas.bind("<Control-Button-1>", lambda e, idx=i: self.on_floor_button_right_click(e, idx))

            # Add tooltip with full text if truncated
            if display_text != floor_name:
                floor_tooltip = Tooltip(self)
                floor_tooltip._attach_to_widget(canvas, floor_name)
                self.tooltips.append(floor_tooltip)

            self.floor_buttons.append(btn_frame)

        if selected_index is not None and 0 <= selected_index < len(floors):
            self.currentFloorLabel.config(text=f"Etage selectionne : {floors[selected_index]}")
        else:
            self.currentFloorLabel.config(text="Aucun etage selectionne")

        # Check if scrollbar is needed after updating floor buttons
        self.after(10, self._update_floor_scroll)

    def on_tool_selected_update(self, data):
        """
        Tool selected update from controller
        """
        tool = data.get("tool")
        
        # Skip if trying to select a disabled tool
        if tool in self.disabled_tools:
            print(f"[View] Ignoring attempt to select disabled tool: {tool}")
            return
            
        if tool != self.current_tool:
            # Set the current tool
            self.current_tool = tool
            
            # Update cursor
            self._update_cursor()
            
            # Update tool button visuals while preserving disabled state
            self._highlight_tool_button(tool)

    def _update_cursor(self):
        """
        Update the cursor appearance based on the current tool
        """
        if self.current_tool in ['wall', 'window', 'door', 'vent']:
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="arrow")

    def on_show_alert_request(self, data):
        title = data.get("title", "Alert")
        message = data.get("message", "Something went wrong.")

        messagebox.showwarning(title, message)

    def _schedule_hover(self, item, x_root, y_root):
        """Schedule showing a tooltip for an item after a delay"""
        if item == self.current_hover_item:
            return

        self._cancel_hover()
        self.current_hover_item = item

        if item in self.canvas_item_meta:
            meta_data = self.canvas_item_meta[item]
            item_type = meta_data.get('type', '') if isinstance(meta_data, dict) else ''

            if item_type == 'wall':
                # For walls, use the main tooltip
                tooltip_text = meta_data['text']
                self.hover_after_id = self.after(
                    500,  # Use a shorter delay for wall tooltips (500ms instead of 1000ms)
                    lambda: self.tooltip.show(tooltip_text, x_root, y_root)
                )
            elif item_type =='plenum':
                tooltip_text_to_show = meta_data.get('tooltip_text') 
                if tooltip_text_to_show:
                    self.hover_after_id = self.after(
                        500,
                        lambda text=tooltip_text_to_show: self.tooltip.show(text, x_root + 10, y_root + 10) 
                    )

            else:
                # Create a dedicated tooltip for vents if it doesn't exist
                if item not in self.vent_tooltips:
                    self.vent_tooltips[item] = Tooltip(self)

                # Get tooltip data for vents
                tooltip_text = meta_data['text'] if isinstance(meta_data, dict) else meta_data

                # Schedule showing this vent's tooltip
                if tooltip_text and tooltip_text.strip():
                    self.hover_after_id = self.after(
                        1000,
                        lambda: self.vent_tooltips[item].show(tooltip_text, x_root, y_root)
                    )

    def _cancel_hover(self):
        """Cancel any pending hover tooltip"""
        if self.hover_after_id is not None:
            self.after_cancel(self.hover_after_id)
            self.hover_after_id = None

        # Hide all tooltips
        for tooltip in self.vent_tooltips.values():
            tooltip.hide()

        self.tooltip.hide()
        self.current_hover_item = None

    def _handle_hover(self, event):
        """Handle mouse hover events on the canvas"""
        # Only process hover events if we have canvas items
        if not hasattr(self, "canvas") or not self.canvas:
            return

        # Convert window coordinates to canvas coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Find items under the cursor
        try:
            items = self.canvas.find_overlapping(canvas_x, canvas_y, canvas_x, canvas_y)
            # Find the first item that has metadata (for tooltip)
            hover_item = next((i for i in items if i in self.canvas_item_meta), None)

            if hover_item:
                self._schedule_hover(hover_item, event.x_root + 10, event.y_root + 10)
            else:
                plenum_hover_found = False
                plenum_items = self.canvas.find_withtag("plenum") 
                for item_id in plenum_items:
                     try:
                         coords = self.canvas.coords(item_id)
                         if len(coords) == 4:
                             x1 = min(coords[0], coords[2])
                             y1 = min(coords[1], coords[3])
                             x2 = max(coords[0], coords[2])
                             y2 = max(coords[1], coords[3])

                             if x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2:
                                 self._schedule_hover(item_id, event.x_root + 10, event.y_root + 10)
                                 plenum_hover_found = True 
                                 break
                     except Exception as e_coords:
                          print(f"Error getting coords for plenum item {item_id}: {e_coords}")
                          continue 
                if not plenum_hover_found:
                    self._cancel_hover()
        except Exception as e:
            # Handle any errors that might occur during hover detection
            print(f"Error handling hover: {e}")
            self._cancel_hover()

    def on_canvas_leave(self, event):
        self._cancel_hover()

    def on_set_height(self, floor_index):
        value = simpledialog.askstring(
            "Hauteur de cet etage",
            "Entrez la hauteur de cet etage (m) :",
            parent=self
        )
        if value:
            try:
                h = float(value.replace(",", "."))
                ivy_bus.publish("set_floor_height_request", {
                    "floor_index": floor_index,
                    "height": h
                })
            except ValueError:
                self.on_show_alert_request({
                    "title": "Valeur incorrecte",
                    "message": "Veuillez entrer un nombre valide"
                })

    def on_floor_height_update(self, data):
        """Handle floor height update from controller"""
        self.current_floor_height = data["height"]
        self._redraw_height_text()

    def _on_window_configure(self, event):
        """Handle window resizing events"""
        if event.widget is self:
            # Only redraw if we have a floor height to display
            if self.current_floor_height is not None:
                self._redraw_height_text()

            # Update the canvas scrollregion to match the new size
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            # Reset canvas view if needed
            if not self.canvas.bbox("all"):
                self.canvas.xview_moveto(0)
                self.canvas.yview_moveto(0)

    def _redraw_height_text(self):
        """Redraw the height text display at the bottom of the canvas"""
        if self.current_floor_height is None:
            return
            
        # Delete existing text if present
        if self.height_text_id:
            self.canvas.delete(self.height_text_id)
            self.height_text_id = None

        # Calculate position for the text (bottom right corner)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # If canvas not yet properly sized, wait and try again
        if canvas_width <= 1 or canvas_height <= 1:
            self.after(100, self._redraw_height_text)
            return
            
        # Position at bottom right
        x_visible = self.canvas.canvasx(canvas_width) - 10
        y_visible = self.canvas.canvasy(canvas_height) - 10
        
        # Format the text
        txt = f"Hauteur de cet etage : {self.current_floor_height} m"
        
        # Create the height text with no background
        self.height_text_id = self.canvas.create_text(
            x_visible, y_visible,
            anchor="se", 
            text=txt,
            fill="#444",
            font=("Helvetica", 10, "italic")
        )

    def _request_initial_floor(self):
        ivy_bus.publish("floor_selected_request", {"floor_index": 0})

    def on_delete_floor(self, floor_index):
        result = messagebox.askyesno(
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer cet etage ?\nTous les elements de cet etage seront perdus.",
            icon='warning'
        )
        if result:
            ivy_bus.publish("delete_floor_request", {
                "floor_index": floor_index
            })

    def _update_floor_scroll(self):
        """Update floor canvas scrollregion and determine if scrollbar is needed"""
        self.floorCanvas.configure(scrollregion=self.floorCanvas.bbox("all"))

        # Check if content exceeds the visible area
        content_height = self.floorFrame.winfo_reqheight()
        canvas_height = self.floorCanvas.winfo_height()

        if content_height > canvas_height:
            # Content is larger than canvas, show scrollbar
            self.floor_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            # Content fits, hide scrollbar
            self.floor_vsb.pack_forget()

    def _on_floor_scroll(self, *args):
        """Custom scrollcommand for floor canvas that updates scrollbar and checks visibility"""
        self.floor_vsb.set(*args)

        # After updating scrollbar position, check if it should be visible
        content_height = self.floorFrame.winfo_reqheight()
        canvas_height = self.floorCanvas.winfo_height()

        if content_height > canvas_height:
            # Content is larger than canvas, ensure scrollbar is shown
            if not self.floor_vsb.winfo_ismapped():
                self.floor_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            # Content fits, ensure scrollbar is hidden
            if self.floor_vsb.winfo_ismapped():
                self.floor_vsb.pack_forget()

    def _highlight_tool_button(self, tool):
        # Reset all buttons to normal state first, except disabled ones
        for t, canvas in self.tool_buttons.items():
            if t not in self.disabled_tools:  # Skip disabled buttons
                for item in canvas.find_all():
                    if canvas.type(item) in ("rectangle", "oval"):
                        canvas.itemconfig(item, fill=self.colors["button_bg"])

        # Highlight selected tool button
        if tool in self.tool_buttons and tool not in self.disabled_tools:
            canvas = self.tool_buttons[tool]
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["selected_tool"])
                    
        # Ensure disabled tools stay visually disabled
        for disabled_tool in self.disabled_tools:
            if disabled_tool in self.tool_buttons:
                canvas = self.tool_buttons[disabled_tool]
                for item in canvas.find_all():
                    if canvas.type(item) in ("rectangle", "oval"):
                        canvas.itemconfig(item, fill=self.colors["disabled_tool"])

    def on_save_button_click(self):
        json_file_path = filedialog.asksaveasfilename(
            title="Enregistrer le projet",
            defaultextension=".json",
            filetypes=[("Fichier JSON", "*.json")],
            initialdir=os.getcwd(),
            initialfile="floors.json"
        )

        if not json_file_path:
            return  # User cancelled the dialog

        ivy_bus.publish("save_project_request", {
            "json_file_path": json_file_path
        })

    def on_import_button_click(self):

        file_path = filedialog.askopenfilename(
        title="选择 floors.json",
        filetypes=[("JSON 文件", "*.json")],
        defaultextension=".json"
        )
        if not file_path:
            return

        ivy_bus.publish("import_project_request", {
            "json_path": file_path
        })

    def on_document_button_click(self):
        """Open a window displaying the ventilation summary view"""
        # Check if there's already a window open - if so, focus on it instead of creating a new one
        if hasattr(self, 'ventilation_summary_window') and self.ventilation_summary_window is not None:
            try:
                if self.ventilation_summary_window.winfo_exists():
                    self.ventilation_summary_window.focus_force()
                    return
            except Exception:
                # In case of error, continue to create a new window
                pass
        
        # Create the Toplevel window
        summary_window = tk.Toplevel(self)
        summary_window.title("Vue Textuelle - Bilan Aéraulique")
        
        # Store reference to the window for future access
        self.ventilation_summary_window = summary_window
        
        # Set window size and position
        window_width = 915
        window_height = 600
        summary_window.geometry(f"{window_width}x{window_height}")
        
        # Center the window relative to the main window
        x = self.winfo_x() + (self.winfo_width() - window_width) // 2
        y = self.winfo_y() + (self.winfo_height() - window_height) // 2
        summary_window.geometry(f"+{x}+{y}")
        
        # Make window modal
        summary_window.transient(self)
        summary_window.grab_set()
        
        # Create main frame with padding
        main_frame = ttk.Frame(summary_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Bilan Aéraulique des Bouches de Ventilation", 
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create notebook with tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # All vents tab
        all_vents_frame = ttk.Frame(notebook, padding=10)
        notebook.add(all_vents_frame, text="Toutes les bouches")
        
        # Create TreeView for all vents
        all_columns = ("floor", "name", "type", "diameter", "flow")
        all_vents_tree = ttk.Treeview(all_vents_frame, columns=all_columns, show="headings", height=15)
        
        # Define headings
        all_vents_tree.heading("floor", text="Étage")
        all_vents_tree.heading("name", text="Nom")
        all_vents_tree.heading("type", text="Type")
        all_vents_tree.heading("diameter", text="Diamètre (mm)")
        all_vents_tree.heading("flow", text="Débit (m³/h)")
        
        # Define column widths
        all_vents_tree.column("floor", width=120)
        all_vents_tree.column("name", width=120)
        all_vents_tree.column("type", width=200)
        all_vents_tree.column("diameter", width=120)
        all_vents_tree.column("flow", width=120)
        
        # Add scrollbar
        all_vents_scrollbar = ttk.Scrollbar(all_vents_frame, orient=tk.VERTICAL, command=all_vents_tree.yview)
        all_vents_tree.configure(yscrollcommand=all_vents_scrollbar.set)
        
        all_vents_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        all_vents_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Category tabs - one for each type of vent
        categories = {
            "extraction_interne": {"name": "Extraction d'air vicié", "color": "#ff0000"},
            "insufflation_interne": {"name": "Insufflation d'air neuf", "color": "#ff9900"},
            "extraction_externe": {"name": "Extraction à l'extérieur", "color": "#4c7093"},
            "admission_externe": {"name": "Admission d'air neuf extérieur", "color": "#66ccff"}
        }
        
        category_frames = {}
        category_trees = {}
        
        for category_id, category_info in categories.items():
            # Create frame for this category
            category_frame = ttk.Frame(notebook, padding=10)
            notebook.add(category_frame, text=category_info["name"])
            category_frames[category_id] = category_frame
            
            # Create TreeView for this category
            cat_columns = ("floor", "name", "diameter", "flow")
            cat_tree = ttk.Treeview(category_frame, columns=cat_columns, show="headings", height=15)
            
            # Define headings
            cat_tree.heading("floor", text="Étage")
            cat_tree.heading("name", text="Nom")
            cat_tree.heading("diameter", text="Diamètre (mm)")
            cat_tree.heading("flow", text="Débit (m³/h)")
            
            # Define column widths
            cat_tree.column("floor", width=120)
            cat_tree.column("name", width=120)
            cat_tree.column("diameter", width=120)
            cat_tree.column("flow", width=120)
            
            # Add scrollbar
            cat_scrollbar = ttk.Scrollbar(category_frame, orient=tk.VERTICAL, command=cat_tree.yview)
            cat_tree.configure(yscrollcommand=cat_scrollbar.set)
            
            cat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Store tree reference
            category_trees[category_id] = cat_tree
        
        # Summary tab
        summary_frame = ttk.Frame(notebook, padding=10)
        notebook.add(summary_frame, text="Récapitulatif")
        
        # Create a frame for summary statistics
        stats_frame = ttk.Frame(summary_frame, padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # Summary labels
        ttk.Label(stats_frame, text="Nombre total de bouches:", 
                font=("Helvetica", 12)).grid(row=0, column=0, sticky="w", pady=5)
        
        total_vents_value = ttk.Label(stats_frame, text="0", font=("Helvetica", 12, "bold"))
        total_vents_value.grid(row=0, column=1, sticky="w", pady=5)
        
        # Category counts
        row = 1
        category_labels = {}
        for category_id, category_info in categories.items():
            ttk.Label(stats_frame, text=f"Nombre de {category_info['name']}:", 
                    font=("Helvetica", 12)).grid(row=row, column=0, sticky="w", pady=5)
            
            count_label = ttk.Label(stats_frame, text="0", font=("Helvetica", 12, "bold"))
            count_label.grid(row=row, column=1, sticky="w", pady=5)
            category_labels[category_id] = count_label
            row += 1
        
        # Flow rates
        ttk.Label(stats_frame, text="Débit total insufflé:", 
                font=("Helvetica", 12)).grid(row=row, column=0, sticky="w", pady=5)
        total_inflow_value = ttk.Label(stats_frame, text="0 m³/h", font=("Helvetica", 12, "bold"))
        total_inflow_value.grid(row=row, column=1, sticky="w", pady=5)
        row += 1
        
        ttk.Label(stats_frame, text="Débit total extrait:", 
                font=("Helvetica", 12)).grid(row=row, column=0, sticky="w", pady=5)
        total_outflow_value = ttk.Label(stats_frame, text="0 m³/h", font=("Helvetica", 12, "bold"))
        total_outflow_value.grid(row=row, column=1, sticky="w", pady=5)
        row += 1
        
        ttk.Label(stats_frame, text="Équilibre aéraulique:", 
                font=("Helvetica", 12)).grid(row=row, column=0, sticky="w", pady=5)
        balance_value = ttk.Label(stats_frame, text="0 m³/h", font=("Helvetica", 12, "bold"))
        balance_value.grid(row=row, column=1, sticky="w", pady=5)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        close_button = ttk.Button(button_frame, text="Fermer", command=summary_window.destroy)
        close_button.pack(side=tk.RIGHT)
        
        # Store references to widgets for updating
        summary_window.vent_data = {
            "all_vents_tree": all_vents_tree,
            "category_trees": category_trees,
            "total_vents_value": total_vents_value,
            "category_labels": category_labels,
            "total_inflow_value": total_inflow_value,
            "total_outflow_value": total_outflow_value,
            "balance_value": balance_value
        }
        
        # Create a callback handler for ventilation updates 
        def handle_ventilation_update(data):
            print("[View] Received ventilation summary update")
            self.populate_ventilation_summary(data=data, summary_window=summary_window)
        
        # Store the update handler reference so we can access it later to remove
        summary_window.ventilation_update_handler = handle_ventilation_update
        
        # Subscribe to ventilation summary updates
        ivy_bus.subscribe("ventilation_summary_update", handle_ventilation_update)
        
        # When the window is closed, manage cleanup
        summary_window.protocol("WM_DELETE_WINDOW", 
                               lambda: self._handle_summary_window_close(summary_window))
        
        # Request ventilation data from the controller AFTER setting up the handler
        print("[View] Requesting ventilation summary data")
        ivy_bus.publish("get_ventilation_summary_request", {})

    def on_draw_plenum_update(self, data):
        """
        data = {
            "start": (x1, y1),
            "end": (x2, y2),
            "max_flow": 1000,
            "type": "Simple" or "Double",
            "area": calculated area in m²
        }
        """
        start = data.get("start")
        end = data.get("end")
        max_flow = data.get("max_flow")
        plenum_type = data.get("type")
        
        # Calculate area if not provided
        area = data.get("area")
        if area is None:
            # Calculate width and height in pixels
            width_px = abs(end[0] - start[0])
            height_px = abs(end[1] - start[1])
            
            # Convert to meters based on scale (40px = 2m)
            width_m = width_px * (2.0/40.0)
            height_m = height_px * (2.0/40.0)
            
            # Calculate area in square meters with 2 decimal places
            area = round(width_m * height_m, 2)
        
        # Choose color based on plenum type
        plenum_color = "blue"  # Default color
        if plenum_type:
            if plenum_type == "Simple":
                plenum_color = "#4CAF50"  # Material Green
            elif plenum_type == "Double":
                plenum_color = "#9C27B0"  # Material Purple
        
        drawn_rect_id = self.canvas.create_rectangle(
            start[0], start[1], end[0], end[1],
            outline=plenum_color, fill="", width=3, tags=("plenum",)
        )

        tooltip_text = f"Plenum\nType: {plenum_type if plenum_type else 'N/A'}\nDébit Max: {max_flow} m3/h\nSuperficie: {area} m²"
        self.canvas_item_meta[drawn_rect_id] = {
            "type": "plenum",
            "max_flow": max_flow,
            "plenum_type": plenum_type, 
            "plenum_color": plenum_color,
            "area": area,
            "tooltip_text": tooltip_text
        }

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._ensure_onion_skin_below()

    def _handle_summary_window_close(self, summary_window):
        """Handle cleanup when summary window is closed"""
        try:
            # Now that we have an unsubscribe method, use it to clean up properly
            if hasattr(summary_window, 'ventilation_update_handler'):
                ivy_bus.unsubscribe("ventilation_summary_update", summary_window.ventilation_update_handler)
                # Remove the reference to prevent future calls to a non-existent window
                if hasattr(self, 'ventilation_summary_window'):
                    self.ventilation_summary_window = None
            
            # Destroy the window
            summary_window.destroy()
        except Exception as e:
            print(f"[View] Error during summary window cleanup: {e}")
            # Still try to reset the reference even if there was an error
            if hasattr(self, 'ventilation_summary_window'):
                self.ventilation_summary_window = None

    def populate_ventilation_summary(self, data=None, summary_window=None):
        """
        Populate the ventilation summary window with data from all floors
        
        Can be called in two ways:
        1. From ivy_bus subscriber: populate_ventilation_summary(self, data)
        2. From window handler: populate_ventilation_summary(summary_window, data)
        """
        # Handle the case where it's called from ivy_bus subscriber
        if summary_window is None and isinstance(data, dict):
            # If we have an open ventilation summary window, use its handler instead
            if hasattr(self, 'ventilation_summary_window') and self.ventilation_summary_window is not None:
                try:
                    if self.ventilation_summary_window.winfo_exists():
                        if hasattr(self.ventilation_summary_window, 'ventilation_update_handler'):
                            # Forward to the window's handler
                            self.ventilation_summary_window.ventilation_update_handler(data)
                            return
                except Exception:
                    # Window no longer exists, clear reference
                    self.ventilation_summary_window = None
            # If no window or error, just return silently
            return
            
        # Handle the case where it's called from summary window's handler with (summary_window, data) params
        if summary_window is None or not isinstance(summary_window, tk.Toplevel):
            print("[View] Error: Invalid summary_window parameter")
            return
            
        if not hasattr(summary_window, "vent_data"):
            print("[View] Error: summary_window doesn't have vent_data attribute")
            return
            
        widgets = summary_window.vent_data
        all_vents_tree = widgets["all_vents_tree"]
        category_trees = widgets["category_trees"]
        
        # Check if the window still exists by trying to access its state
        try:
            winfo_exists = summary_window.winfo_exists()
            if not winfo_exists:
                print("[View] Warning: Summary window no longer exists")
                return
        except Exception:
            print("[View] Warning: Error checking if summary window exists")
            return
            
        # Check if the treeview widgets still exist
        try:
            # Clear existing data
            all_vents_tree.delete(*all_vents_tree.get_children())
            for tree in category_trees.values():
                tree.delete(*tree.get_children())
        except Exception as e:
            print(f"[View] Warning: Error accessing treeview widgets: {e}")
            return
            
        # Variables to track statistics
        total_vents = 0
        category_counts = {
            "extraction_interne": 0,
            "insufflation_interne": 0,
            "extraction_externe": 0,
            "admission_externe": 0
        }
        
        total_inflow = 0  # insufflation_interne + admission_externe
        total_outflow = 0  # extraction_interne + extraction_externe
        
        vent_types = {
            "extraction_interne": "Extraction d'air vicié",
            "insufflation_interne": "Insufflation d'air neuf",
            "extraction_externe": "Extraction à l'extérieur",
            "admission_externe": "Admission d'air neuf extérieur"
        }
        
        # If we received ventilation data, use it
        vents_data = []
        if data and "vents" in data:
            vents_data = data["vents"]
            print(f"[View] Processing {len(vents_data)} vents for summary display")
        else:
            print("[View] Warning: No ventilation data received")
        
        # Process all vents
        for vent_data in vents_data:
            vent_function = vent_data.get("function", "")
            if not vent_function:
                print(f"[View] Warning: Vent missing function: {vent_data}")
                continue
                
            total_vents += 1
            
            # Increment category count
            if vent_function in category_counts:
                category_counts[vent_function] += 1
            
            # Calculate flow rates
            try:
                flow_rate = int(vent_data.get("flow_rate", 0)) if vent_data.get("flow_rate") else 0
            except ValueError:
                flow_rate = 0
                
            if vent_function in ["insufflation_interne", "admission_externe"]:
                total_inflow += flow_rate
            elif vent_function in ["extraction_interne", "extraction_externe"]:
                total_outflow += flow_rate
            
            # Add to all vents tree
            try:
                vent_type = vent_types.get(vent_function, "")
                all_vents_tree.insert("", tk.END, values=(
                    vent_data.get("floor_name", ""),
                    vent_data.get("name", ""),
                    vent_type,
                    vent_data.get("diameter", ""),
                    vent_data.get("flow_rate", "")
                ))
                
                # Add to category tree
                if vent_function in category_trees:
                    category_trees[vent_function].insert("", tk.END, values=(
                        vent_data.get("floor_name", ""),
                        vent_data.get("name", ""),
                        vent_data.get("diameter", ""),
                        vent_data.get("flow_rate", "")
                    ))
            except Exception as e:
                print(f"[View] Error adding vent to treeview: {e}")
                continue
        
        # Update statistics display - with error handling
        try:
            widgets["total_vents_value"].config(text=str(total_vents))
            
            for category, count in category_counts.items():
                if category in widgets["category_labels"]:
                    widgets["category_labels"][category].config(text=str(count))
            
            widgets["total_inflow_value"].config(text=f"{total_inflow} m³/h")
            widgets["total_outflow_value"].config(text=f"{total_outflow} m³/h")
            
            # Calculate balance
            balance = total_inflow - total_outflow
            balance_text = f"{abs(balance)} m³/h"
            
            if balance > 0:
                balance_text = f"+{balance_text} (Surpression)"
                widgets["balance_value"].config(text=balance_text, foreground="blue")
            elif balance < 0:
                balance_text = f"-{balance_text} (Dépression)" 
                widgets["balance_value"].config(text=balance_text, foreground="red")
            else:
                balance_text = f"{balance_text} (Équilibré)"
                widgets["balance_value"].config(text=balance_text, foreground="green")
                
            print(f"[View] Summary populated with {total_vents} vents. Inflow: {total_inflow}, Outflow: {total_outflow}")
        except Exception as e:
            print(f"[View] Error updating statistics widgets: {e}")
            return

    def _truncate_text_with_ellipsis(self, text, max_width, font):
        """Truncates text with ellipsis if it exceeds max_width pixels"""
        # Get Tkinter font object to measure text width
        font_obj = tk.font.Font(family=font[0], size=font[1], weight=font[2] if len(font) > 2 else "normal")

        # If text fits, return it as is
        if font_obj.measure(text) <= max_width:
            return text

        # Truncate with ellipsis
        ellipsis = "..."
        ellipsis_width = font_obj.measure(ellipsis)

        # Start with empty result and add characters one by one
        result = ""
        for char in text:
            # Check if adding this character + ellipsis would exceed max width
            if font_obj.measure(result + char) + ellipsis_width > max_width:
                return result + ellipsis
            result += char

        return result  # Shouldn't reach here, but just in case

    def _center_window(self, width, height):
        """Center the window on the screen"""
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate position coordinates
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Set window position
        self.geometry(f"+{x}+{y}")

    def _request_onion_skin_preview(self):
        """Request the onion skin preview of the floor below"""
        if hasattr(self, 'currentFloorLabel') and self.currentFloorLabel:
            ivy_bus.publish("onion_skin_preview_request", {})

    def draw_onion_skin_item(self, item_type, coords, fill_color=None, thickness=None, additional_data=None):
        """Draw an item as part of the onion skin with reduced opacity"""
        # Remove any existing onion skin items
        item_id = None
        opacity_color = self._apply_opacity_to_color(fill_color, self.onion_skin_opacity)

        if item_type == "wall":
            start, end = coords
            item_id = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=opacity_color, width=3, tags=("onion_skin",)
            )
        elif item_type == "window":
            start, end = coords
            thickness = thickness or 5
            item_id = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=opacity_color, width=thickness, tags=("onion_skin",)
            )
        elif item_type == "door":
            start, end = coords
            thickness = thickness or 5
            item_id = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=opacity_color, width=thickness, tags=("onion_skin",)
            )
        elif item_type == "vent":
            start, end = coords
            # Calculate the radius based on the distance between start and end points
            import math
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            radius = math.sqrt(dx*dx + dy*dy)
            
            # Create a hollow circle with reduced opacity
            item_id = self.canvas.create_oval(
                start[0] - radius, start[1] - radius,
                start[0] + radius, start[1] + radius,
                outline=opacity_color, width=2, fill="", tags=("onion_skin",)
            )
            
            # Store this onion skin item
            self.onion_skin_items.append(item_id)
        elif item_type == "plenum":
            start, end = coords
            # Get plenum type from additional data if available
            plenum_type = None
            if additional_data:
                plenum_type = additional_data.get("type")
            
            # Choose color based on plenum type (same as in on_draw_plenum_update)
            plenum_color = "blue"  # Default color
            if plenum_type:
                if plenum_type == "Simple":
                    plenum_color = "#4CAF50"  # Material Green
                elif plenum_type == "Double":
                    plenum_color = "#9C27B0"  # Material Purple
            
            # Apply opacity to the color
            plenum_color = self._apply_opacity_to_color(plenum_color, self.onion_skin_opacity)
            
            # Create the rectangle for plenum with reduced opacity
            item_id = self.canvas.create_rectangle(
                start[0], start[1], end[0], end[1],
                outline=plenum_color, width=3, fill="", tags=("onion_skin",)
            )

        if item_id:
            self.onion_skin_items.append(item_id)

    def _apply_opacity_to_color(self, color, opacity):
        """Convert color to rgba with opacity"""
        if not color or color == "":
            color = "#000000"  # Default to black

        # Handle named colors
        if color == "black":
            color = "#000000"
        elif color == "blue":
            color = "#0000FF"  # Standard blue for plenum
        elif color == "#ffafcc":  # Window color
            color = "#ffafcc"
        elif color == "#dda15e":  # Door color
            color = "#dda15e"

        # For hex colors, mix with white background to create opacity effect
        if color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16) if len(color) >= 5 else r
            b = int(color[5:7], 16) if len(color) >= 7 else g

            # Mix with white (255,255,255) based on opacity
            r = int(r * opacity + 255 * (1 - opacity))
            g = int(g * opacity + 255 * (1 - opacity))
            b = int(b * opacity + 255 * (1 - opacity))

            return f"#{r:02x}{g:02x}{b:02x}"

        return color  # Return original if we can't process it

    def clear_onion_skin(self):
        """Clear all onion skin preview items"""
        # Delete items by ID list
        for item_id in self.onion_skin_items:
            self.canvas.delete(item_id)
        
        # Also find and delete any items that might have the onion_skin tag but weren't tracked
        onion_items = self.canvas.find_withtag("onion_skin")
        for item in onion_items:
            self.canvas.delete(item)
            
        # Reset the tracking list
        self.onion_skin_items = []

    def on_onion_skin_preview_update(self, data):
        """Handle onion skin preview update from controller"""
        # Clear any existing onion skin items
        self.clear_onion_skin()

        # Check if we have data to draw
        if not data or "items" not in data:
            return

        # Draw each item in the onion skin preview
        for item in data["items"]:
            item_type = item.get("type")
            coords = item.get("coords")
            fill = item.get("fill", "")
            thickness = item.get("thickness")
            additional_data = item.get("additional_data")

            self.draw_onion_skin_item(item_type, coords, fill, thickness, additional_data)

        # Ensure all onion skin items are at the bottom of the z-order
        self._ensure_onion_skin_below()

    def _ensure_onion_skin_below(self):
        """Ensure all onion skin items are below all other canvas items"""
        # First, lower all onion skin items
        for item_id in self.onion_skin_items:
            self.canvas.tag_lower(item_id)

        # Then raise all regular items (walls, windows, doors, vents) above onion skin
        all_items = self.canvas.find_all()
        for item in all_items:
            tags = self.canvas.gettags(item)
            if tags and "onion_skin" not in tags:
                self.canvas.tag_raise(item)

    def on_escape_key(self, event):
        """Handle Esc key press to cancel the current drawing operation"""
        if self.current_tool == 'wall':
            ivy_bus.publish("cancal_to_draw_wall_request", {})
            self._hide_placement_tooltip()
        elif self.current_tool == 'window':
            ivy_bus.publish("cancal_to_draw_window_request", {})
            self._hide_placement_tooltip()
        elif self.current_tool == 'door':
            ivy_bus.publish("cancal_to_draw_door_request", {})
            self._hide_placement_tooltip()
        elif self.current_tool == 'vent':
            ivy_bus.publish("cancal_to_draw_vent_request", {})
            self._hide_placement_tooltip()
            
            # If we have an open ventilation summary window, ensure it's properly tracked
            if hasattr(self, 'ventilation_summary_window') and self.ventilation_summary_window is not None:
                try:
                    # Check if the window still exists
                    if not self.ventilation_summary_window.winfo_exists():
                        # Window no longer exists, clear the reference
                        self.ventilation_summary_window = None
                except Exception:
                    # In case of error, clear the reference to be safe
                    self.ventilation_summary_window = None
        elif self.current_tool == 'plenum' and hasattr(self, "plenum_start_x") and self.plenum_start_x is not None:
            # Cancel the plenum drawing
            if hasattr(self, "temp_plenum") and self.temp_plenum:
                self.canvas.delete(self.temp_plenum)
                self.temp_plenum = None
            self.plenum_start_x = None
            self.plenum_start_y = None
            self._hide_placement_tooltip()
            # Notify controller to cancel plenum creation
            ivy_bus.publish("cancel_plenum_request", {})
            print("[View] Plenum drawing cancelled by Escape key")

    def on_reset_button_click(self):
        """Handle reset button click with confirmation dialog"""
        # Show confirmation dialog
        confirm = messagebox.askokcancel(
            title="Confirmation de réinitialisation",
            message="Êtes-vous sûr de vouloir réinitialiser l'application ?\n\nToutes les modifications non sauvegardées seront perdues.",
            icon=messagebox.WARNING
        )
        
        # If user confirmed, send reset request to controller
        if confirm:
            ivy_bus.publish("reset_app_request", {})
            
    # Placement tooltip methods
    def _show_placement_tooltip(self, element_type, length_m, is_dimension=False):
        """Show or update the placement tooltip with element type and length or dimensions"""
        if not self.placement_tooltip:
            # Create the tooltip window
            self.placement_tooltip = Toplevel(self)
            self.placement_tooltip.wm_overrideredirect(True)
            self.placement_tooltip.attributes("-topmost", True)
            
            # Configure tooltip appearance
            self.placement_tooltip.configure(background="#f0f8ff", highlightbackground="#d0e0ff", highlightthickness=1)
            
            # Create and configure label
            label = Label(self.placement_tooltip, 
                          textvariable=self.placement_tooltip_text,
                          justify="left",
                          background="#f0f8ff", 
                          foreground="#333333", 
                          relief="flat",
                          font=("Arial", 11, "bold"),
                          padx=8, 
                          pady=5)
            label.pack(ipadx=6, ipady=4, fill="both", expand=True)
        
        # Update text and element type
        self.placement_element_type = element_type
        
        # Display dimensions or length based on the flag
        if is_dimension:
            tooltip_text = f"{element_type}: {length_m} m²"
        else:
            tooltip_text = f"{element_type}: {length_m:.2f} m"
            
        self.placement_tooltip_text.set(tooltip_text)
        
        # Force update to ensure tooltip appears correctly
        self.placement_tooltip.update_idletasks()
    
    def _hide_placement_tooltip(self):
        """Hide the placement tooltip"""
        if self.placement_tooltip:
            self.placement_tooltip.destroy()
            self.placement_tooltip = None
            self.placement_element_type = None

    def _update_grid_background(self):
        """Create a tiled background using the grid image"""
        if not hasattr(self, 'use_grid_background') or not self.use_grid_background:
            return

        # Clear existing background tiles
        for tile_id in self.bg_tile_ids:
            self.canvas.delete(tile_id)
        self.bg_tile_ids = []

        # Get canvas size and image dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:  # Canvas not fully initialized yet
            return

        img_width = self.grid_image.width()
        img_height = self.grid_image.height()

        # Ensure grid extends beyond the visible area for scrolling
        visible_left = int(self.canvas.canvasx(0))
        visible_top = int(self.canvas.canvasy(0))
        visible_right = visible_left + canvas_width
        visible_bottom = visible_top + canvas_height

        # Calculate the range to cover with tiles (with a bit of extra padding)
        padding = max(img_width, img_height) * 2
        min_x = max(0, visible_left - padding)
        min_y = max(0, visible_top - padding)
        max_x = visible_right + padding
        max_y = visible_bottom + padding

        # Calculate the starting grid points aligned to image size
        start_x = min_x - (min_x % img_width)
        start_y = min_y - (min_y % img_height)

        # Create tiles
        for x in range(start_x, max_x, img_width):
            for y in range(start_y, max_y, img_height):
                # Create tile and add to background layer (behind all items)
                tile_id = self.canvas.create_image(x, y, image=self.grid_image, anchor='nw', tags='background')
                self.bg_tile_ids.append(tile_id)
                # Ensure background tiles stay in background
                self.canvas.lower(tile_id)
        
        # Ensure onion skin preview items are above the background
        self._ensure_onion_skin_below()

    def on_clear_canvas_update(self, data):
        # Store whether this is a redraw operation (not a true clear)
        is_redraw = data.get("redraw_operation", False)
        
        # Check if there were any plenums on the canvas before clearing
        plenum_items = self.canvas.find_withtag("plenum")
        has_plenums = len(plenum_items) > 0
        
        # Store the current floor height before clearing
        previous_height = self.current_floor_height
        
        # Store the background tile IDs before clearing
        bg_tile_ids = self.bg_tile_ids.copy() if hasattr(self, 'bg_tile_ids') else []
        
        # Clear the main canvas
        self.canvas.delete("all")
        
        # Reset tracking variables
        self.bg_tile_ids = []
        self.canvas_item_meta = {}  # Clear meta data
        self.vent_tooltips = {}  # Clear vent tooltips
        self.onion_skin_items = []  # Clear onion skin items
        
        if self.height_text_id:
            self.height_text_id = None
        
        # Restore the floor height for redraw operations
        if is_redraw:
            self.current_floor_height = previous_height
        else:
            self.current_floor_height = None
        
        # Reset the canvas view position
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        
        # Redraw the background grid
        self._update_grid_background()
        
        # Update the tool buttons (in case plenum was removed)
        self._update_disabled_tools()
        
        # Only notify about plenums if this is a genuine clear, not a redraw operation
        if has_plenums and not is_redraw:
            ivy_bus.publish("plenum_cleared_notification", {})
            
        # Redraw the height text if this is a redraw operation and we have a floor height
        if is_redraw and self.current_floor_height is not None:
            self.after(50, self._redraw_height_text)

    def on_ensure_onion_skin_refresh(self, data):
        """Handles the ensure_onion_skin_refresh event by requesting a fresh onion skin preview"""
        self._request_onion_skin_preview()
        # Ensure the onion skin appears in the correct z-order
        self.after(50, self._ensure_onion_skin_below)

    def on_disable_tool_button(self, data):
        tool = data.get("tool")
        if tool:
            self.disabled_tools.add(tool)
            self._update_disabled_tools()
            print(f"[View] Disabled tool: {tool}")

    def on_enable_tool_button(self, data):
        tool = data.get("tool")
        if tool and tool in self.disabled_tools:
            self.disabled_tools.remove(tool)
            self._update_disabled_tools()
            print(f"[View] Enabled tool: {tool}")
            
    def _update_disabled_tools(self):
        """Update the visual appearance of disabled tools"""
        for tool in self.tool_buttons:
            canvas = self.tool_buttons[tool]
            
            # Update canvas appearance based on disabled state
            if tool in self.disabled_tools:
                # Apply disabled appearance
                for item in canvas.find_all():
                    if canvas.type(item) in ("rectangle", "oval"):
                        canvas.itemconfig(item, fill=self.colors["disabled_tool"])
                # Update tooltip to indicate disabled state
                for tooltip in self.tooltips:
                    if hasattr(tooltip, "_widget") and tooltip._widget == canvas:
                        tooltip._text = "Plenum déjà présent"
                # Unbind click event
                canvas.unbind("<Button-1>")
                
                # If the disabled tool is the current tool, switch to select tool
                if tool == self.current_tool:
                    self.on_tool_button_click('select')
            else:
                # Only reset background if it's not the current tool
                if tool != self.current_tool:
                    for item in canvas.find_all():
                        if canvas.type(item) in ("rectangle", "oval"):
                            canvas.itemconfig(item, fill=self.colors["button_bg"])
                else:
                    # This is the current selected tool
                    for item in canvas.find_all():
                        if canvas.type(item) in ("rectangle", "oval"):
                            canvas.itemconfig(item, fill=self.colors["selected_tool"])
                            
                # Rebind click event if it was previously disabled
                canvas.bind("<Button-1>", lambda event, t=tool: self.on_tool_button_click(t))
                # Reset tooltip text
                for tooltip in self.tooltips:
                    if hasattr(tooltip, "_widget") and tooltip._widget == canvas:
                        # Reset to original tooltip based on tool type
                        if tool == 'select':
                            tooltip._text = 'Selection'
                        elif tool == 'eraser':
                            tooltip._text = 'Gomme'
                        elif tool == 'wall':
                            tooltip._text = 'Mur'
                        elif tool == 'window':
                            tooltip._text = 'Fenêtre'
                        elif tool == 'door':
                            tooltip._text = 'Porte'
                        elif tool == 'vent':
                            tooltip._text = 'Ventilation'
                        elif tool == 'plenum':
                            tooltip._text = 'Plenum'
        
        # Call highlight tool button to ensure current tool is properly highlighted
        # while maintaining disabled states
        self._highlight_tool_button(self.current_tool)
