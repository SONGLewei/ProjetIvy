from ivy.ivy_bus import ivy_bus
from model.wall import Wall
from model.floor import Floor
from model.window import Window
from model.door import Door
from model.vent import Vent

class Controller:
    def __init__(self):
        self.floors = []
        self.selected_floor_index = None
        self.current_tool = 'select'
        self.floor_count = 0

        # Subscribe the events that UI has published
        ivy_bus.subscribe("draw_wall_request", self.handle_draw_wall_request)
        ivy_bus.subscribe("cancal_to_draw_wall_request",self.handle_cancal_to_draw_wall_request)
        ivy_bus.subscribe("floor_selected_request", self.handle_floor_selected_request)
        ivy_bus.subscribe("new_floor_request", self.handle_new_floor_request)
        ivy_bus.subscribe("tool_selected_request", self.handle_tool_selected_request)
        ivy_bus.subscribe("rename_floor_request",self.handle_rename_floor_request)
        ivy_bus.subscribe("draw_window_request", self.handle_draw_window_request)
        ivy_bus.subscribe("cancal_to_draw_window_request",self.handle_cancal_to_draw_window_request)
        ivy_bus.subscribe("draw_door_request", self.handle_draw_door_request)
        ivy_bus.subscribe("cancal_to_draw_door_request",self.handle_cancal_to_draw_door_request)

        ivy_bus.subscribe("draw_vent_request",      self.handle_draw_vent_request)
        ivy_bus.subscribe("cancal_to_draw_vent_request", self.handle_cancel_vent)
        ivy_bus.subscribe("create_vent_request",    self.handle_create_vent_request)

        ivy_bus.subscribe("delete_item_request", self.handle_delete_item_request)
        ivy_bus.subscribe("set_floor_height_request", self.handle_set_floor_height_request)

        self.wall_start_point = None
        self.is_canceled_wall_draw = False

        self.window_start_point = None
        self.is_canceled_window_draw = False

        self.door_start_point = None
        self.is_canceled_door_draw = False

        self.vent_start_point = None
        self.is_canceled_vent_draw = False
        self.vent_role  = None
        self.vent_color = None

        self.temp_vent_start = None
        self.temp_vent_end   = None
        self.temp_vent_role  = None
        self.temp_vent_color = None

    def handle_draw_wall_request(self, data):
        x, y = data.get("x"), data.get("y")
        is_click = data.get("is_click", False)
        is_preview = data.get("is_preview", False)

        if self.selected_floor_index is None or self.current_tool!='wall':
            return

        if is_click:
            if self.wall_start_point is None:
                self.wall_start_point = (x, y)
            else:
                start = self.wall_start_point
                end   = (x, y)

                wall_obj = Wall(start, end)

                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_wall(wall_obj)
                print(f"in floor {current_floor.name} create wall : {wall_obj}")

                ivy_bus.publish("draw_wall_update", {
                    "start": wall_obj.start,
                    "end":   wall_obj.end,
                    "fill":  "black",
                })

                self.wall_start_point = None

        elif is_preview:
            if self.wall_start_point is not None:
                start = self.wall_start_point
                dx = abs(x - start[0])
                dy = abs(y - start[1])

                if dx >= dy:
                    corrected_end = (x, start[1])
                else:
                    corrected_end = (start[0], y)

                ivy_bus.publish("draw_wall_update", {
                    "start": start,
                    "end":   corrected_end,
                    "fill":  "gray",
                })

    def handle_cancal_to_draw_wall_request(self,data):
        self.is_canceled_wall_draw = True
        self.wall_start_point = None
        
        ivy_bus.publish("draw_wall_update",{
            "start": (0, 0), "end": (0, 0), "fill": "gray"
        })

    def handle_draw_window_request(self,data):
        x, y = data.get("x"), data.get("y")
        is_click = data.get("is_click", False)
        is_preview = data.get("is_preview", False)

        if self.selected_floor_index is None or self.current_tool!='window':
            return

        if is_click:
            if self.window_start_point is None:
                self.window_start_point = (x, y)
            else:
                start = self.window_start_point
                end   = (x, y)

                window_obj = Window(start, end,thickness=5)

                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_window(window_obj)
                print(f"in floor {current_floor.name} create window : {window_obj}")

                ivy_bus.publish("draw_window_update", {
                    "start": window_obj.start,
                    "end":   window_obj.end,
                    "fill":  "#EE82EE",
                    "thickness": window_obj.thickness,
                })

                self.window_start_point = None

        elif is_preview:
            if self.window_start_point is not None:
                start = self.window_start_point
                dx = abs(x - start[0])
                dy = abs(y - start[1])

                if dx >= dy:
                    corrected_end = (x, start[1])
                else:
                    corrected_end = (start[0], y)

                ivy_bus.publish("draw_window_update", {
                    "start": start,
                    "end":   corrected_end,
                    "fill":  "gray",
                    "thickness": "5",
                })

    def handle_cancal_to_draw_window_request(self,data):
        self.is_canceled_window_draw = True
        self.window_start_point = None
        
        ivy_bus.publish("draw_window_update",{
            "start": (0, 0), "end": (0, 0), "fill": "gray"
        })
    
    def handle_draw_door_request(self, data):
        x, y = data.get("x"), data.get("y")
        is_click = data.get("is_click", False)
        is_preview = data.get("is_preview", False)

        if self.selected_floor_index is None or self.current_tool != 'door':
            return

        if is_click:
            if self.door_start_point is None:
                self.door_start_point = (x, y)
            else:
                start = self.door_start_point
                end = (x, y)

                door_obj = Door(start, end, thickness=5)

                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_door(door_obj)
                print(f"in floor {current_floor.name} create door : {door_obj}")

                ivy_bus.publish("draw_door_update", {
                    "start": door_obj.start,
                    "end": door_obj.end,
                    "fill": "#8B4513",
                    "thickness": door_obj.thickness,
                })

                self.door_start_point = None

        elif is_preview:
            if self.door_start_point is not None:
                start = self.door_start_point
                dx = abs(x - start[0])
                dy = abs(y - start[1])

                if dx >= dy:
                    corrected_end = (x, start[1])
                else:
                    corrected_end = (start[0], y)

                ivy_bus.publish("draw_door_update", {
                    "start": start,
                    "end": corrected_end,
                    "fill":  "gray",
                    "thickness": "5",
                })

    def handle_cancal_to_draw_door_request(self, data):
        self.is_canceled_door_draw = True
        self.door_start_point = None
        
        ivy_bus.publish("draw_door_update",{
            "start": (0, 0), "end": (0, 0), "fill": "gray"
        })   

    def handle_draw_vent_request(self, data):
        x, y       = data["x"], data["y"]
        is_click   = data.get("is_click", False)
        is_preview = data.get("is_preview", False)
        role       = data.get("role")
        color      = data.get("color", "#000")

        if self.selected_floor_index is None or self.current_tool != "vent":
            return

        if is_click and self.vent_start_point is None:
            self.vent_start_point = (x, y)
            self.vent_role  = role
            self.vent_color = color
            return

        if is_click and self.vent_start_point is not None:
            start, end = self.vent_start_point, (x, y)
            temp = Vent(start, end, "", "", "", role, color)

            self.temp_vent_start = temp.start
            self.temp_vent_end   = temp.end
            self.temp_vent_role  = role
            self.temp_vent_color = color

            ivy_bus.publish("draw_vent_update", {
                "start": temp.start, "end": temp.end,
                "color": "gray"
            })
            ivy_bus.publish("vent_need_info_request", {
                "start": temp.start, "end": temp.end,
                "role":  role, "color": color
            })

            self.vent_start_point = None
            self.vent_role = self.vent_color = None
            return

        if is_preview and self.vent_start_point:
            temp = Vent(self.vent_start_point, (x, y), "", "", "", role, color)
            ivy_bus.publish("draw_vent_update", {
                "start": temp.start, "end": temp.end,
                "color": "gray"
            })

    def handle_cancel_vent(self, data):
        self.vent_start_point = None
        self.temp_vent_start = self.temp_vent_end = None

        ivy_bus.publish("draw_vent_update", {
            "start": (0, 0), "end": (0, 0), "color": "gray"
        })

    def handle_create_vent_request(self, data):
        if self.temp_vent_start is None:
            return

        vent = Vent(self.temp_vent_start, self.temp_vent_end,
                    data["name"], data["diameter"], data["flow"],
                    self.temp_vent_role, self.temp_vent_color)

        current_floor = self.floors[self.selected_floor_index]
        current_floor.add_vent(vent)

        ivy_bus.publish("draw_vent_update", {
            "start": vent.start, "end": vent.end,
            "color": vent.color,
            "name":  vent.name,
            "diameter": vent.diameter,
            "flow": vent.flow_rate,
            "role": vent.function
        })

        self.temp_vent_start = self.temp_vent_end = None
                
    def handle_floor_selected_request(self, data):

        floor_idx = data.get("floor_index")
        self.selected_floor_index = floor_idx
        selected_floor = self.floors[floor_idx]
        print(f"[Controller] the floor is chosen now : {selected_floor.name} (index={floor_idx})")

        ivy_bus.publish("clear_canvas_update", {})

        # told View to redraw all the walls      Il faut dire tous les objets apres iciiiiiiiiiiii
        for wall_obj in selected_floor.walls:
            ivy_bus.publish("draw_wall_update", {
                "start": wall_obj.start,
                "end":   wall_obj.end,
                "fill":  "black",
            })

        for window_obj in selected_floor.windows:
            ivy_bus.publish("draw_window_update", {
                "start": window_obj.start,
                "end":   window_obj.end,
                "fill":  "black",
                "thickness": window_obj.thickness
            })

        for door_objet in selected_floor.doors:
            ivy_bus.publish("draw_door_update", {
                "start": door_objet.start,
                "end":   door_objet.end,
                "fill":  "black",
                "thickness": door_objet.thickness
            })

        for v in selected_floor.vents:
            ivy_bus.publish("draw_vent_update", {
                "start": v.start, "end": v.end,
                "color": v.color,
                "name": v.name,
                "diameter": v.diameter,
                "flow": v.flow_rate,
                "role": v.function
            })

        ivy_bus.publish("floor_selected_update", {
            "selected_floor_index": floor_idx,
            "floor_name": selected_floor.name
        })

        self._publish_height(selected_floor)
        
    def handle_new_floor_request(self, data):
        """
        When the user clicks the "New floor" button: insert a new floor above the selected floor
        If no floor is currently selected (or there is no floor at all), make it the first floor
        Clear automatic the canvas
        """
        ivy_bus.publish("clear_canvas_update", {})
        new_floor_name = f"Floor {len(self.floors)}"
        new_floor = Floor(new_floor_name)

        if self.selected_floor_index is None:
            insert_index = 0
        else:
            insert_index = self.selected_floor_index + 1

        self.floors.insert(insert_index, new_floor)

        self.selected_floor_index = insert_index

        print(f"[Controller] new floor {new_floor_name}, insert position = {insert_index}")

        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })

        self._publish_height(new_floor)

    def handle_tool_selected_request(self, data):
        """
        when user click the botton of outils
        """
        tool = data.get("tool")

        if self.selected_floor_index is None:
            ivy_bus.publish("show_alert_request",{
                "title": "No Floors Available",
                "message": "You must create a floor before using tools."
            })
            return

        self.current_tool = tool
        print(f"[Controller] current tool = {tool}")

        ivy_bus.publish("tool_selected_update", {
            "tool": tool
        })

    def handle_rename_floor_request(self,data):
        """
        when user need to rename the floor name
        """
        floor_index = data.get("floor_index")
        new_name = data.get("new_name","")

        if floor_index is None or not new_name.strip() or new_name == "":
            ivy_bus.publish("show_alert_request",{
                "title":"Floor name empty",
                "message":"The floor must have a name"
            })
            return
        
        floor_obj = self.floors[floor_index]
        floor_obj.name = new_name

        ivy_bus.publish("new_floor_update", {
        "floors": [f.name for f in self.floors],
        "selected_floor_index": self.selected_floor_index
        })
    
    def handle_delete_item_request(self, data):
        if self.selected_floor_index is None:
            return

        obj_type = data["type"]
        x1, y1, x2, y2 = map(int, data["coords"])
        start = (x1, y1)
        end   = (x2, y2)

        floor = self.floors[self.selected_floor_index]

        def same_segment(o):
            return ({o.start, o.end} == {start, end})

        if obj_type == "wall":
            floor.walls   = [w for w in floor.walls   if not same_segment(w)]
        elif obj_type == "window":
            floor.windows = [w for w in floor.windows if not same_segment(w)]
        elif obj_type == "door":
            floor.doors   = [d for d in floor.doors   if not same_segment(d)]
        elif obj_type == "vent":
            floor.vents   = [v for v in floor.vents   if not same_segment(v)]
    
    def _publish_height(self, floor):
        ivy_bus.publish("floor_height_update", {"height": floor.height})

    def handle_set_floor_height_request(self, data):
        idx    = data["floor_index"]
        height = data["height"]
        if 0 <= idx < len(self.floors):
            self.floors[idx].set_height(height)
            if idx == self.selected_floor_index:
                self._publish_height(self.floors[idx])
