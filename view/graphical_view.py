import os
import tkinter as tk
import tkinter.simpledialog as simpledialog
import tkinter.font
from tkinter import ttk, PhotoImage
from tkinter import messagebox
from ivy.ivy_bus import ivy_bus
from view.tooltip import Tooltip 

class GraphicalView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application VMC")

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
        
        # Onion skin related variables
        self.onion_skin_items = []  # To track items drawn as part of onion skin
        self.onion_skin_opacity = 0.3  # 30% opacity for onion skin items

        self.hover_after_id = None
        self.current_hover_item = None 
        self.height_text_id = None
        self.current_floor_height = None

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
        }

        self.icons = {}
        self._load_icons()
        self._setup_style()
        self._create_layout()

        self.bind("<Configure>", self._on_window_configure)

        # Subscribe to events from controller
        ivy_bus.subscribe("draw_wall_update",         self.on_draw_wall_update)
        ivy_bus.subscribe("floor_selected_update",    self.on_floor_selected_update)
        ivy_bus.subscribe("new_floor_update",         self.on_new_floor_update)
        ivy_bus.subscribe("tool_selected_update",     self.on_tool_selected_update)
        ivy_bus.subscribe("show_alert_request",       self.on_show_alert_request)
        ivy_bus.subscribe("clear_canvas_update",      self.on_clear_canvas_update)
        ivy_bus.subscribe("draw_window_update",       self.on_draw_window_update)
        ivy_bus.subscribe("draw_door_update",         self.on_draw_door_update)
        ivy_bus.subscribe("vent_need_info_request",   self.on_vent_need_info_request)
        ivy_bus.subscribe("draw_vent_update",         self.on_draw_vent_update)
        ivy_bus.subscribe("floor_height_update",      self.on_floor_height_update)
        ivy_bus.subscribe("onion_skin_preview_update", self.on_onion_skin_preview_update)

        # Set initial cursor
        self.current_tool = 'select'  # Default tool

        # Request the initial floor information from the controller
        self.after(100, self._request_initial_floor)
        self.after(100, self._update_cursor)

        # Highlight the select tool button initially and notify controller
        self.after(200, lambda: self._highlight_tool_button('select'))
        self.after(200, lambda: ivy_bus.publish("tool_selected_request", {"tool": 'select'}))

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
            'save':   os.path.join(base_path, 'photos', 'diskette.png'),
            'import': os.path.join(base_path, 'photos', 'import.png'),
            'document': os.path.join(base_path, 'photos', 'document.png'),
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

        # Continue with the center frame and other elements
        centerFrame = tk.Frame(topBarFrame, bg=self.colors["topbar_bg"])
        centerFrame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Create label with white background
        label_frame = tk.Frame(centerFrame, bg="white", padx=15, pady=8)
        label_frame.pack(anchor="center", pady=5)

        self.currentFloorLabel = ttk.Label(label_frame,
                                           text="Aucun étage sélectionné",
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
            text="+ Nouvel étage",
            fill="white",
            font=("Helvetica", 11, "bold")
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

        # Create canvas with border on right and bottom
        self.canvas = tk.Canvas(
            drawWrap, bg="white", highlightthickness=1,
            highlightbackground="#cccccc",
            xscrollcommand=hbar.set, yscrollcommand=vbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Connect scrollbars to canvas (without displaying them)
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)

        def _on_canvas_configure(evt):
            self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 0, 0))
            self._redraw_height_text()

        self.canvas.bind("<Configure>", _on_canvas_configure)

        # Bind mousewheel events for scrolling
        self.canvas.bind("<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda event: self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS
        self.canvas.bind("<Button-4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Shift-Button-4>", lambda event: self.canvas.xview_scroll(-1, "units"))
        self.canvas.bind("<Shift-Button-5>", lambda event: self.canvas.xview_scroll(1, "units"))

        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>",   self.on_canvas_move)
        self.canvas.bind("<Leave>", self.on_canvas_leave)

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

        # Add a "Étage" label at the top of the floor list
        floor_title = tk.Label(scrollWrap, text="Étage", font=("Helvetica", 12), fg="#2f3039", bg="white")
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
            ('select', 'Sélection'),
            ('eraser', 'Gomme'),
            ('wall', 'Mur'),
            ('window', 'Fenêtre'),
            ('door', 'Porte'),
            ('vent', 'Ventilation')
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
        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request", {
                "x": event.x,
                "y": event.y,
                "is_click":True
            })

        if self.current_tool == "window":
            ivy_bus.publish("draw_window_request",{
                "x": event.x,
                "y": event.y,
                "is_click":True
            })

        if self.current_tool == "door":
            ivy_bus.publish("draw_door_request",{
                "x": event.x,
                "y": event.y,
                "is_click":True
            })

        if self.current_tool == "vent":
            if not self.vent_role:
                self.on_show_alert_request({
                    "title": "Type de ventilation non sélectionné",
                    "message": "Veuillez d'abord choisir un type de ventilation."
                })
                return
            ivy_bus.publish("draw_vent_request", {
                "x": event.x, "y": event.y,
                "is_click": True,
                "role":  self.vent_role,
                "color": self.vent_color
            })
        if self.current_tool == "eraser":
            items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
            if not items:
                return
                
            # Find items that are not part of the onion skin
            non_onion_items = []
            for item in items:
                tags = self.canvas.gettags(item)
                if "onion_skin" not in tags:
                    non_onion_items.append(item)
                    
            if not non_onion_items:
                return
                
            # Get the topmost non-onion item
            item = non_onion_items[-1]
            tags = self.canvas.gettags(item)
            if not tags:
                return

            obj_type = tags[0]
            coords = self.canvas.coords(item)
            self.canvas.delete(item)

            ivy_bus.publish("delete_item_request", {
                "type": obj_type,
                "coords": coords
            })

    def on_canvas_move(self,event):
        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request",{
                "x": event.x,
                "y": event.y,
                "is_preview": True
            })

        if self.current_tool == "window":
            ivy_bus.publish("draw_window_request",{
                "x": event.x,
                "y": event.y,
                "is_preview": True
            })
        if self.current_tool == "door":
            ivy_bus.publish("draw_door_request",{
                "x": event.x,
                "y": event.y,
                "is_preview": True
            })

        if self.current_tool == "vent" and self.vent_role:
            ivy_bus.publish("draw_vent_request", {
                "x": event.x, "y": event.y,
                "is_preview": True,
                "role":  self.vent_role,
                "color": self.vent_color
            })

        self._handle_hover(event)

    # the case to cancel the wall when draw
    def on_canvas_right_click(self,event):
        if self.current_tool == "wall":
            ivy_bus.publish("cancal_to_draw_wall_request",{})

        if self.current_tool == "window":
            ivy_bus.publish("cancal_to_draw_window_request",{})

        if self.current_tool == "door":
            ivy_bus.publish("cancal_to_draw_door_request",{})

        if self.current_tool == "vent":
            ivy_bus.publish("cancal_to_draw_vent_request", {})

    def on_new_floor_button_click(self):
        ivy_bus.publish("new_floor_request", {})

    def on_tool_button_click(self, tool, event=None):
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

    def on_floor_button_right_click(self,event,floor_index):
        menu = tk.Menu(self,tearoff=0)

        menu.add_command(
            label="Renommer",
            command=lambda:self.on_rename_floor(floor_index)
        )

        menu.add_command(
            label="Définir la hauteur",
            command=lambda: self.on_set_height(floor_index)
        )

        menu.add_separator()

        menu.add_command(
            label="Supprimer",
            command=lambda: self.on_delete_floor(floor_index)
        )

        menu.tk_popup(event.x_root,event.y_root)

    def on_rename_floor(self,floor_index):
        new_name=simpledialog.askstring(
            title="Renommer l'étage",
            prompt="Entrez le nouveau nom de l'étage : "
        )

        if new_name:
            ivy_bus.publish("rename_floor_request",{
                "floor_index":floor_index,
                "new_name": new_name 
            })

    def show_vent_type_menu(self):
        menu = tk.Menu(self, tearoff=0)

        vent_options = [
            ("En rouge, extraction de l'air vicié", "#ff0000", "extraction_interne"),
            (
                "En orange, insufflation de l'air neuf",
                "#ff9900",
                "insufflation_interne",
            ),
            (
                "En bleu foncé, extraction à l'extérieur",
                "#4c7093",
                "extraction_externe",
            ),
            (
                "En bleu clair, admission d'air neuf extérieur",
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

    def on_vent_type_selected(self,role,color):
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

        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line

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

        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line

            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=fill ,width=thickness, tags=("window",)
            )
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

        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line

            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=fill,width=thickness,tags=("door",)
            )
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Ensure all onion skin items remain below
            self._ensure_onion_skin_below()

    def on_draw_vent_update(self, data):
        start, end = data["start"], data["end"]
        color      = data.get("color", "gray")

        if color == "gray":
            if hasattr(self, "temp_vent"):
                self.canvas.delete(self.temp_vent)
            self.temp_vent = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="gray", dash=(4, 2), width=4
            )
        else:
            if hasattr(self, "temp_vent"):
                self.canvas.delete(self.temp_vent)
                del self.temp_vent
                
            # Calculate line angle for the arrow
            import math
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0:
                dx, dy = dx/length, dy/length
                
                # Create the base line (using width=2 to match the onion skin)
                item = self.canvas.create_line(
                    start[0], start[1], end[0], end[1],
                    fill=color, width=2, tags=("vent",)
                )
                
                # Add arrowhead
                arrow_size = 8
                arrow_angle = 0.5  # in radians, determines arrow width
                
                # Calculate the arrowhead points
                arrow_x1 = end[0] - arrow_size * (dx * math.cos(arrow_angle) - dy * math.sin(arrow_angle))
                arrow_y1 = end[1] - arrow_size * (dy * math.cos(arrow_angle) + dx * math.sin(arrow_angle))
                arrow_x2 = end[0] - arrow_size * (dx * math.cos(arrow_angle) + dy * math.sin(arrow_angle))
                arrow_y2 = end[1] - arrow_size * (dy * math.cos(arrow_angle) - dx * math.sin(arrow_angle))
                
                # Create arrowhead with the same tag as the line
                arrowhead = self.canvas.create_polygon(
                    end[0], end[1], arrow_x1, arrow_y1, arrow_x2, arrow_y2,
                    fill=color, outline=color, tags=("vent",)
                )
                
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))

                # Create well-formatted tooltip content with explicit strings
                name = data.get('name', '')
                diameter = data.get('diameter', '')
                flow = data.get('flow', '')
                role = data.get('role', '')

                meta = f"{name}\nØ {diameter} mm\n{flow} m³/h\n{role}"

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
                "title": "Entrée invalide",
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
                    "title": "Entrée invalide",
                    "message": "Le diamètre ne peut pas être vide."
                })
                continue

            if not diameter.isdigit():
                self.on_show_alert_request({
                    "title": "Entrée invalide",
                    "message": "Le diamètre doit être un nombre entier positif."
                })
                continue

            # Valid integer, break out of the loop
            break

        # Validate flow rate is an integer
        while True:
            flow = simpledialog.askstring("Débit d'air (m³/h)", "Entrez le débit d'air (m³/h) :")
            if flow is None:  # User cancelled
                ivy_bus.publish("cancal_to_draw_vent_request", {})
                return

            # Check if input is a valid integer
            if not flow.strip():
                self.on_show_alert_request({
                    "title": "Entrée invalide",
                    "message": "Le débit d'air ne peut pas être vide."
                })
                continue

            if not flow.isdigit():
                self.on_show_alert_request({
                    "title": "Entrée invalide",
                    "message": "Le débit d'air doit être un nombre entier positif."
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

        # Update the label text
        self.currentFloorLabel.config(text=f"Étage sélectionné : {floor_name}")

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

            # Update to match the "+ Nouvel étage" button radius (5px)
            radius = 5  # Changed from 20 to 5 to match the "+ Nouvel étage" button

            # Define the box with some padding
            x1 = 5
            y1 = 5
            x2 = available_width - 5
            y2 = button_height - 5

            # Create rounded corners using ovals (similar to "+ Nouvel étage" button)
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
            font_spec = ("Helvetica", 11, "bold" if is_selected else "normal")

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
            canvas.bind("<Button-3>", lambda e, idx=i: self.on_floor_button_right_click(e, idx))

            # Add tooltip with full text if truncated
            if display_text != floor_name:
                floor_tooltip = Tooltip(self)
                floor_tooltip._attach_to_widget(canvas, floor_name)
                self.tooltips.append(floor_tooltip)

            self.floor_buttons.append(btn_frame)

        if selected_index is not None and 0 <= selected_index < len(floors):
            self.currentFloorLabel.config(text=f"Étage sélectionné : {floors[selected_index]}")
        else:
            self.currentFloorLabel.config(text="Aucun étage sélectionné")

        # Check if scrollbar is needed after updating floor buttons
        self.after(10, self._update_floor_scroll)

    def on_tool_selected_update(self, data):
        """
        When the Controller publishes 'tool_selected_update', it can update the interface status
        (such as highlighting the current tool button, or displaying "Current Tool" in the status bar)
        """
        # Reset previous tool button appearance
        if self.current_tool and self.current_tool in self.tool_buttons:
            canvas = self.tool_buttons[self.current_tool]
            # Update all shapes on the canvas to use the default background color
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["button_bg"])

        # Update current tool
        self.current_tool = data.get("tool")

        # Highlight selected tool button
        if self.current_tool in self.tool_buttons:
            canvas = self.tool_buttons[self.current_tool]
            # Update all shapes on the canvas to use the selected color
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["selected_tool"])

        # Update cursor
        self._update_cursor()

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

    def on_clear_canvas_update(self, data):
        # Clear the main canvas
        self.canvas.delete("all")
        self.canvas_item_meta = {}  # Clear meta data
        self.vent_tooltips = {}  # Clear vent tooltips
        self.onion_skin_items = []  # Clear onion skin items
        if self.height_text_id:
            self.canvas.delete(self.height_text_id)
            self.height_text_id = None
        self.current_floor_height = None
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

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

        # Find items under the cursor
        try:
            items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
            # Find the first item that has metadata (for tooltip)
            hover_item = next((i for i in items if i in self.canvas_item_meta), None)

            if hover_item:
                self._schedule_hover(hover_item, event.x_root + 10, event.y_root + 10)
            else:
                self._cancel_hover()
        except Exception as e:
            # Handle any errors that might occur during hover detection
            print(f"Error handling hover: {e}")
            self._cancel_hover()

    def on_canvas_leave(self, event):
        self._cancel_hover()

    def on_set_height(self, floor_index):
        value = simpledialog.askstring(
            "Hauteur de cet étage",
            "Entrez la hauteur de cet étage (m) :",
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
        self.current_floor_height = data["height"]
        self._redraw_height_text()

    def _on_window_configure(self, event):
        if event.widget is self:
            self._redraw_height_text()

    def _redraw_height_text(self):
        if self.current_floor_height is None:
            return
        if self.height_text_id:
            self.canvas.delete(self.height_text_id)

        x_visible = self.canvas.canvasx(self.canvas.winfo_width()) - 10
        y_visible = self.canvas.canvasy(self.canvas.winfo_height()) - 10
        txt = f"Hauteur de cet étage : {self.current_floor_height} m"
        self.height_text_id = self.canvas.create_text(
             x_visible, y_visible,
            anchor="se", text=txt,
            font=("Helvetica", 10, "italic"), fill="#444"
        )

    def _request_initial_floor(self):
        ivy_bus.publish("floor_selected_request", {"floor_index": 0})

    def on_delete_floor(self, floor_index):
        result = messagebox.askyesno(
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer cet étage ?\nTous les éléments de cet étage seront perdus.",
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
        if tool in self.tool_buttons:
            canvas = self.tool_buttons[tool]
            for item in canvas.find_all():
                if canvas.type(item) in ("rectangle", "oval"):
                    canvas.itemconfig(item, fill=self.colors["selected_tool"])

    def on_save_button_click(self):
        # For now, just inform the user that the feature is not implemented
        ivy_bus.publish("show_alert_request", {
            "title": "Sauvegarde",
            "message": "Fonctionnalité de sauvegarde à implémenter."
        })
        # In a real implementation, you would publish an event for the controller to handle saving

    def on_import_button_click(self):
        # For now, just inform the user that the feature is not implemented
        ivy_bus.publish("show_alert_request", {
            "title": "Importation",
            "message": "Fonctionnalité d'importation à implémenter."
        })
        # In a real implementation, you would publish an event for the controller to handle importing

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
            # Calculate the line angle for the arrow
            import math
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0:
                dx, dy = dx/length, dy/length
                
                # Create the base line (using width=2 to match main view)
                item_id = self.canvas.create_line(
                    start[0], start[1], end[0], end[1],
                    fill=opacity_color, width=2, tags=("onion_skin",)
                )
            
                # Store this onion skin item
                self.onion_skin_items.append(item_id)
                
                # Add arrowhead
                arrow_size = 8
                arrow_angle = 0.5  # in radians, determines arrow width
                
                # Calculate the arrowhead points
                arrow_x1 = end[0] - arrow_size * (dx * math.cos(arrow_angle) - dy * math.sin(arrow_angle))
                arrow_y1 = end[1] - arrow_size * (dy * math.cos(arrow_angle) + dx * math.sin(arrow_angle))
                arrow_x2 = end[0] - arrow_size * (dx * math.cos(arrow_angle) + dy * math.sin(arrow_angle))
                arrow_y2 = end[1] - arrow_size * (dy * math.cos(arrow_angle) - dx * math.sin(arrow_angle))
                
                # Create arrowhead
                arrowhead_id = self.canvas.create_polygon(
                    end[0], end[1], arrow_x1, arrow_y1, arrow_x2, arrow_y2,
                    fill=opacity_color, outline=opacity_color, tags=("onion_skin",)
                )
                
                self.onion_skin_items.append(arrowhead_id)
        
        if item_id:
            self.onion_skin_items.append(item_id)

    def _apply_opacity_to_color(self, color, opacity):
        """Convert color to rgba with opacity"""
        if not color or color == "":
            color = "#000000"  # Default to black
            
        # Handle named colors
        if color == "black":
            color = "#000000"
        elif color == "#EE82EE":  # Window color
            color = "#EE82EE"
        elif color == "#8B4513":  # Door color
            color = "#8B4513"
            
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
        for item_id in self.onion_skin_items:
            self.canvas.delete(item_id)
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
