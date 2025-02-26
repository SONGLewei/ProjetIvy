import os
import tkinter as tk
from tkinter import ttk, PhotoImage
from tkinter import messagebox
from ivy.ivy_bus import ivy_bus

class GraphicalView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VMC Application")
        self.geometry("1000x600")

        self.currentFloorLabel = None
        self.floor_count = 0
        self.current_floor = None
        self.floor_buttons = []
        self.current_tool = None

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

        # subscribe the update events from controller
        ivy_bus.subscribe("draw_wall_update",         self.on_draw_wall_update)
        ivy_bus.subscribe("floor_selected_update",    self.on_floor_selected_update)
        ivy_bus.subscribe("new_floor_update",         self.on_new_floor_update)
        ivy_bus.subscribe("tool_selected_update",     self.on_tool_selected_update)
        ivy_bus.subscribe("show_alert_request",       self.on_show_alert_request)
        ivy_bus.subscribe("clear_canvas_update",      self.on_clear_canvas_update)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton",font=("Helvetica", 10),padding=6,foreground="black")
        style.configure("FloorLabel.TLabel",font=("Arial", 13, "bold"),foreground="#333")

    def _load_icons(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        icon_paths = {
            'select': os.path.join(base_path, 'photos', 'select.png'),
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

        new_floor_btn = ttk.Button(topBarFrame, text="New floor", command=self.on_new_floor_button_click)
        new_floor_btn.pack(side=tk.LEFT, padx=(20, 10), pady=10)

        centerFrame = tk.Frame(topBarFrame, bg=self.colors["topbar_bg"])
        centerFrame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.currentFloorLabel = ttk.Label(centerFrame,
                                           text="No floor selected",
                                           style="FloorLabel.TLabel")
        self.currentFloorLabel.pack(anchor="center", pady=5)

    def _create_main_area(self):
        mainFrame = tk.Frame(self, bg=self.colors["main_bg"])
        mainFrame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # left part
        canvasFrame = tk.Frame(mainFrame, bg=self.colors["canvas_bg"])
        canvasFrame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.canvas = tk.Canvas(canvasFrame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_left_click_for_wall)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click_for_wall)
        self.canvas.bind("<Motion>",   self.on_canvas_move_for_wall)

        # line to seperate
        sep = ttk.Separator(mainFrame, orient="vertical")
        sep.pack(side=tk.RIGHT, fill=tk.Y, pady=20)

        # right
        self.floorFrame = tk.Frame(mainFrame, bg=self.colors["main_bg"], width=150)
        self.floorFrame.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)

    def _create_bottom_toolbar(self):
        toolbarFrame = tk.Frame(self, bg=self.colors["toolbar_bg"])
        toolbarFrame.pack(side=tk.BOTTOM, fill=tk.X)

        leftSpace = tk.Label(toolbarFrame, bg=self.colors["toolbar_bg"])
        leftSpace.pack(side=tk.LEFT, fill=tk.X, expand=True)

        iconFrame = tk.Frame(toolbarFrame, bg=self.colors["toolbar_bg"])
        iconFrame.pack(side=tk.LEFT)

        for t in ['select', 'wall', 'window', 'door', 'vent']:
            ttk.Button(iconFrame,
                       image=self.icons.get(t),
                       command=lambda tool=t: self.on_tool_button_click(tool)
                       ).pack(side=tk.LEFT, padx=10, pady=5)

        rightSpace = tk.Label(toolbarFrame, bg=self.colors["toolbar_bg"])
        rightSpace.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --------------------------------- Handle events ------------------------------------------------
    def on_canvas_left_click_for_wall(self, event):
        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request", {
                "x": event.x,
                "y": event.y,
                "is_click":True
            })
    
    def on_canvas_move_for_wall(self,event):
        if self.current_tool == "wall":
            ivy_bus.publish("draw_wall_request",{
                "x": event.x,
                "y": event.y,
                "is_preview": True
            })
    
    def on_canvas_right_click_for_wall(self,event):
        if self.current_tool == "wall":
            ivy_bus.publish("cancal_to_draw_wall_request",{})

    def on_new_floor_button_click(self):
        ivy_bus.publish("new_floor_request", {})

    def on_tool_button_click(self, tool):
        ivy_bus.publish("tool_selected_request", {"tool": tool})

    def on_floor_button_click(self, floor_index):
        ivy_bus.publish("floor_selected_request", {
            "floor_index": floor_index
        })

    # ----------------------------- GET FROM CONTROLLER --------------------------------------------------------
    def on_draw_wall_update(self, data):
        """
        Called when the Controller publishes 'draw_wall_update' to actually operate the Canvas to draw the wall
        """
        start = data.get("start")
        end   = data.get("end")
        fill  = data.get("fill", "black")

        if fill == "gray":
            if hasattr(self,"temp_line"):
                self.canvas.delete(self.temp_line)
            self.temp_line = self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="gray", dash=(4, 2)                
            )
        
        else:
            if hasattr(self, "temp_line"):
                self.canvas.delete(self.temp_line)
                del self.temp_line

            self.canvas.create_line(
                start[0], start[1], end[0], end[1],
                fill="black"
            )
        #self.canvas.create_line(start[0], start[1], end[0], end[1], fill=fill)

    def on_floor_selected_update(self, data):
        """
        data = {
        "selected_floor_index": <int>,
        "floor_name": "Floor 2"
        }
        """
        floor_name  = data.get("floor_name")
        self.currentFloorLabel.config(text=f"Selected floor: {floor_name}")

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
            new_buttons.append(btn)

        self.floor_buttons = new_buttons

        for btn in reversed(self.floor_buttons):
            btn.pack(pady=5)

        if selected_index is not None and 0 <= selected_index < len(floors):
            self.currentFloorLabel.config(text=f"Selected floor: {floors[selected_index]}")
        else:
            self.currentFloorLabel.config(text="No floor selected")

    def on_tool_selected_update(self, data):
        """
        When the Controller publishes 'tool_selected_update', it can update the interface status
        (such as highlighting the current tool button, or displaying "Current Tool" in the status bar)
        """
        self.current_tool = data.get("tool")


    def on_show_alert_request(self, data):
        """
        处理 Controller 发送的 show_alert_request 事件，
        弹出 tkinter 提示框提醒用户需要先创建楼层。
        """
        title = data.get("title", "Alert")
        message = data.get("message", "Something went wrong.")

        messagebox.showwarning(title, message)

    def on_clear_canvas_update(self, data):
        self.canvas.delete("all")