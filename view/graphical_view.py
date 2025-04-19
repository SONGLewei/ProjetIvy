import os
import tkinter as tk
import tkinter.simpledialog as simpledialog
from tkinter import ttk, PhotoImage
from tkinter import messagebox
from ivy.ivy_bus import ivy_bus
from view.tooltip import Tooltip 

class GraphicalView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application VMC")
        self.geometry("1000x600")

        self.currentFloorLabel = None
        self.floor_count = 0
        self.current_floor = None
        self.floor_buttons = []
        self.current_tool = None
        self.vent_role = None
        self.vent_color = None
        self.canvas_item_meta = {}
        self.tooltip = Tooltip(self)

        self.hover_after_id = None
        self.current_hover_item = None 
        self.height_text_id = None
        self.current_floor_height = None

        
        
        self.colors = {
            "topbar_bg":    "#f4f4f4",
            "main_bg":      "#e8e8e8",
            "canvas_bg":    "#fafafa",
            "toolbar_bg":   "#dadada",
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
        
        # Set initial cursor
        self.current_tool = 'select'  # Default tool
        
        # Request the initial floor information from the controller
        self.after(100, self._request_initial_floor)
        self.after(100, self._update_cursor)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton",font=("Helvetica", 10),padding=6,foreground="black")
        style.configure("FloorLabel.TLabel",font=("Arial", 13, "bold"),foreground="#333")

    def _load_icons(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_paths = {
            'select': os.path.join(base_path, 'photos', 'select.png'),
            'eraser': os.path.join(base_path, 'photos', 'eraser.png'),
            'wall':   os.path.join(base_path, 'photos', 'wall.png'),
            'window': os.path.join(base_path, 'photos', 'window.png'),
            'door':   os.path.join(base_path, 'photos', 'door1.png'),
            'vent':   os.path.join(base_path, 'photos', 'vent.png'),
        }
        for name, path in icon_paths.items():
            try:
                icon = PhotoImage(file=path).subsample(7, 7)
                self.icons[name] = icon
            except Exception as e:
                print(f"fail to load {name} : {e}")

    def _create_layout(self):
        # 3 parts of the UI
        self._create_top_bar()
        ttk.Separator(self, orient="horizontal").pack(side=tk.TOP, fill=tk.X)
        self._create_main_area()
        ttk.Separator(self, orient="horizontal").pack(side=tk.BOTTOM, fill=tk.X)
        self._create_bottom_toolbar()

    def _create_top_bar(self):
        topBarFrame = tk.Frame(self, bg=self.colors["topbar_bg"])
        topBarFrame.pack(side=tk.TOP, fill=tk.X)

        centerFrame = tk.Frame(topBarFrame, bg=self.colors["topbar_bg"])
        centerFrame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.currentFloorLabel = ttk.Label(centerFrame,
                                           text="Aucun étage sélectionné",
                                           style="FloorLabel.TLabel")
        self.currentFloorLabel.pack(anchor="center", pady=5)
        
        new_floor_btn = ttk.Button(topBarFrame, text="Nouvel étage", command=self.on_new_floor_button_click)
        new_floor_btn.pack(side=tk.RIGHT, padx=(10, 20), pady=10)

    def _create_main_area(self):
        mainFrame = tk.Frame(self, bg=self.colors["main_bg"])
        mainFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # left part
        drawWrap = tk.Frame(mainFrame, bg=self.colors["canvas_bg"])
        drawWrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        vbar = ttk.Scrollbar(drawWrap, orient="vertical")
        hbar = ttk.Scrollbar(drawWrap, orient="horizontal")
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            drawWrap, bg="white", highlightthickness=0,
            xscrollcommand=hbar.set, yscrollcommand=vbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        def _on_canvas_configure(evt):
            self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 0, 0))
            self._redraw_height_text()

        self.canvas.bind("<Configure>", _on_canvas_configure)

        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)


        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>",   self.on_canvas_move)
        self.canvas.bind("<Leave>", self.on_canvas_leave)

        #self._create_compass_layer(canvasFrame)
        self._create_compass_layer(drawWrap)

        # line to seperate
        sep = ttk.Separator(mainFrame, orient="vertical")
        sep.pack(side=tk.RIGHT, fill=tk.Y, pady=20)

        scrollWrap = tk.Frame(mainFrame, bg=self.colors["main_bg"])
        scrollWrap.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)

        self.floorCanvas = tk.Canvas(
            scrollWrap, bg=self.colors["main_bg"], highlightthickness=0, width=130
        )
        vsb = ttk.Scrollbar(scrollWrap, orient="vertical", command=self.floorCanvas.yview)
        self.floorCanvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.floorCanvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        self.floorFrame = tk.Frame(self.floorCanvas, bg=self.colors["main_bg"])
        self.floorCanvas.create_window((0, 0), window=self.floorFrame, anchor="nw")

        self.floorFrame.bind(
            "<Configure>",
            lambda e: self.floorCanvas.configure(scrollregion=self.floorCanvas.bbox("all"))
        )

        def _on_mousewheel(event):
            self.floorCanvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Windows / Linux
        self.floorCanvas.bind_all("<MouseWheel>",   _on_mousewheel)
        # macOS
        self.floorCanvas.bind_all("<Button-4>", _on_mousewheel)
        self.floorCanvas.bind_all("<Button-5>", _on_mousewheel)

    def _create_compass_layer(self, parent_frame):
        self.compass_canvas = tk.Canvas(parent_frame, width=80, height=120,
                                        bg='white', highlightthickness=0)

        self.compass_canvas.place(x=0, y=0)

        center_x = 40
        center_y = 40
        radius = 25

        self.compass_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline='black', width=2
        )
        self.compass_canvas.create_line(
            center_x, center_y - radius, center_x, center_y + radius, width=2
        )
        self.compass_canvas.create_line(
            center_x - radius, center_y, center_x + radius, center_y, width=2
        )
        self.compass_canvas.create_text(
            center_x, center_y - radius - 10,
            text='N', font=('Helvetica', 8, 'bold')
        )
        self.compass_canvas.create_text(
            center_x + radius + 10, center_y,
            text='E', font=('Helvetica', 8, 'bold')
        )
        self.compass_canvas.create_text(
            center_x, center_y + radius + 10,
            text='S', font=('Helvetica', 8, 'bold')
        )
        self.compass_canvas.create_text(
            center_x - radius - 10, center_y,
            text='O', font=('Helvetica', 8, 'bold')
        )

        line_y = center_y + radius + 25
        line_length_px = 40
        start_x = center_x - (line_length_px // 2)
        end_x   = center_x + (line_length_px // 2)

        self.compass_canvas.create_line(
            start_x, line_y, end_x, line_y,
            width=2, fill='black'
        )

        self.compass_canvas.create_text(
            center_x, line_y - 8,
            text="2m", font=("Helvetica", 9, "bold"),
            fill='black'
        )

    def _create_bottom_toolbar(self):
        toolbarFrame = tk.Frame(self, bg=self.colors["toolbar_bg"])
        toolbarFrame.pack(side=tk.BOTTOM, fill=tk.X)

        leftSpace = tk.Label(toolbarFrame, bg=self.colors["toolbar_bg"])
        leftSpace.pack(side=tk.LEFT, fill=tk.X, expand=True)

        iconFrame = tk.Frame(toolbarFrame, bg=self.colors["toolbar_bg"])
        iconFrame.pack(side=tk.LEFT)

        # Tool names in French
        tool_names = {
            'select': 'Sélection',
            'eraser': 'Gomme',
            'wall': 'Mur',
            'window': 'Fenêtre',
            'door': 'Porte',
            'vent': 'Ventilation'
        }

        for t in ['select','eraser', 'wall', 'window', 'door', 'vent']:
            btn = ttk.Button(iconFrame,
                       image=self.icons.get(t),
                       command=lambda tool=t: self.on_tool_button_click(tool)
                       )
            btn.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Create tooltip for each button
            Tooltip(self, btn, tool_names.get(t, t))

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
            item = items[-1]
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

    def on_tool_button_click(self, tool):
        self.current_tool = tool  # Update local tool state immediately
        self._update_cursor()     # Update cursor immediately for responsiveness
        
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
        ("En rouge, extraction de l'air vicié",          "#ff0000", "extraction_interne"),
        ("En orange, insufflation de l'air neuf",        "#ff9900", "insufflation_interne"),
        ("En bleu foncé, extraction à l'extérieur",       "#003366", "extraction_externe"),
        ("En bleu clair, admission d'air neuf extérieur", "#66ccff", "admission_externe"),
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
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        #self.canvas.create_line(start[0], start[1], end[0], end[1], fill=fill)

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
            item = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill=color, width=4, tags=("vent",)
            )
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            meta = (f"{data.get('name','')}\n"
                    f"Ø {data.get('diameter','')} mm\n"
                    f"{data.get('flow','')} m³/h\n"
                    f"{data.get('role','')}")
            self.canvas_item_meta[item] = meta
    
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
        floor_name  = data.get("floor_name")
        self.currentFloorLabel.config(text=f"Étage sélectionné : {floor_name}")

    def on_new_floor_update(self, data):
        """
        data = {
        "floors": ["Floor 1", "Floor 2", ...],
        "selected_floor_index": <int>
        }
        """
        floors = data.get("floors", [])
        selected_index = data.get("selected_floor_index", None)

        for btn in self.floor_buttons:
            btn.pack_forget()

        new_buttons = []
        for i, floor_name in enumerate(floors):
            if i < len(self.floor_buttons):
                btn = self.floor_buttons[i]
                btn.config(text=floor_name)
            else:
                btn = ttk.Button(
                    self.floorFrame,
                    text=floor_name,
                    command=lambda idx=i: self.on_floor_button_click(idx)
                )
                # to rename the floor
                btn.bind("<Button-3>",lambda e, idx=i:self.on_floor_button_right_click(e,idx))
            new_buttons.append(btn)

        self.floor_buttons = new_buttons

        for btn in reversed(self.floor_buttons):
            btn.pack(pady=5)

        if selected_index is not None and 0 <= selected_index < len(floors):
            self.currentFloorLabel.config(text=f"Étage sélectionné : {floors[selected_index]}")
        else:
            self.currentFloorLabel.config(text="Aucun étage sélectionné")

    def on_tool_selected_update(self, data):
        """
        When the Controller publishes 'tool_selected_update', it can update the interface status
        (such as highlighting the current tool button, or displaying "Current Tool" in the status bar)
        """
        self.current_tool = data.get("tool")
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
        self.canvas.delete("all")
        if self.height_text_id:
            self.canvas.delete(self.height_text_id)
            self.height_text_id = None
        self.current_floor_height = None
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.canvas.winfo_height()))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
    
    def _schedule_hover(self, item, x_root, y_root):
        if item == self.current_hover_item:
            return
        self._cancel_hover()
        self.current_hover_item = item
        if item in self.canvas_item_meta:
            self.hover_after_id = self.after(
                1000,
                lambda: self.tooltip.show(self.canvas_item_meta[item], x_root, y_root)
            )
    
    def _cancel_hover(self):
        if self.hover_after_id is not None:
            self.after_cancel(self.hover_after_id)
            self.hover_after_id = None
        self.tooltip.hide()
        self.current_hover_item = None

    def _handle_hover(self, event):
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        vent_item = next((i for i in items if i in self.canvas_item_meta), None)
        if vent_item:
            self._schedule_hover(vent_item, event.x_root + 10, event.y_root + 10)
        else:
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