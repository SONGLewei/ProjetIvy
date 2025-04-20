import os, json, math
from datetime import datetime
from PIL import Image, ImageDraw
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
        
        # Create default Floor 0
        default_floor = Floor("etage 0")
        self.floors.append(default_floor)
        self.selected_floor_index = 0
        
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
        ivy_bus.subscribe("delete_floor_request", self.handle_delete_floor_request)
        ivy_bus.subscribe("onion_skin_preview_request", self.handle_onion_skin_preview_request)

        ivy_bus.subscribe("save_project_request", self.handle_save_project_request)
        ivy_bus.subscribe("import_project_request", self.handle_import_project_request)

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
        
        # Initialize floor height
        self._publish_height(default_floor)

    def attach_view(self,view):
        self.view = view

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
                
                # If this is the floor below the current selected floor, 
                # update the onion skin in the floor above
                if len(self.floors) > self.selected_floor_index + 1:
                    # Save current floor index
                    current_idx = self.selected_floor_index
                    # Temporarily set selected floor to the one above
                    self.selected_floor_index = current_idx + 1
                    # Send onion skin update
                    self._send_onion_skin_preview()
                    # Restore current floor index
                    self.selected_floor_index = current_idx
                
                # Also refresh the onion skin of the current floor if we're above floor 0
                # Not using elif so both conditions can be true for middle floors
                if self.selected_floor_index > 0:
                    self._send_onion_skin_preview()

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
                
                # If this is the floor below the current selected floor, 
                # update the onion skin in the floor above
                if len(self.floors) > self.selected_floor_index + 1:
                    # Save current floor index
                    current_idx = self.selected_floor_index
                    # Temporarily set selected floor to the one above
                    self.selected_floor_index = current_idx + 1
                    # Send onion skin update
                    self._send_onion_skin_preview()
                    # Restore current floor index
                    self.selected_floor_index = current_idx
                
                # Also refresh the onion skin of the current floor if we're above floor 0
                # Not using elif so both conditions can be true for middle floors
                if self.selected_floor_index > 0:
                    self._send_onion_skin_preview()

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
                
                # If this is the floor below the current selected floor, 
                # update the onion skin in the floor above
                if len(self.floors) > self.selected_floor_index + 1:
                    # Save current floor index
                    current_idx = self.selected_floor_index
                    # Temporarily set selected floor to the one above
                    self.selected_floor_index = current_idx + 1
                    # Send onion skin update
                    self._send_onion_skin_preview()
                    # Restore current floor index
                    self.selected_floor_index = current_idx
                
                # Also refresh the onion skin of the current floor if we're above floor 0
                # Not using elif so both conditions can be true for middle floors
                if self.selected_floor_index > 0:
                    self._send_onion_skin_preview()

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
        if self.temp_vent_start is None or self.temp_vent_end is None:
            return

        name = data.get("name", "Unnamed")
        diameter = data.get("diameter", "N/A")
        flow_rate = data.get("flow_rate", "N/A")
        function = data.get("role", self.vent_role)
        
        vent_obj = Vent(self.temp_vent_start, self.temp_vent_end,
                         name, diameter, flow_rate, function, self.vent_color)
        
        if self.selected_floor_index is not None:
            current_floor = self.floors[self.selected_floor_index]
            current_floor.add_vent(vent_obj)
            
            # Redraw with the saved properties
            ivy_bus.publish("draw_vent_update", {
                "start": vent_obj.start, "end": vent_obj.end,
                "color": vent_obj.color,
                "name": vent_obj.name,
                "diameter": vent_obj.diameter,
                "flow": vent_obj.flow_rate,
                "role": vent_obj.function
            })
            
            # If this is the floor below the current selected floor, 
            # update the onion skin in the floor above
            if len(self.floors) > self.selected_floor_index + 1:
                # Save current floor index
                current_idx = self.selected_floor_index
                # Temporarily set selected floor to the one above
                self.selected_floor_index = current_idx + 1
                # Send onion skin update
                self._send_onion_skin_preview()
                # Restore current floor index
                self.selected_floor_index = current_idx
            
            # Also refresh the onion skin of the current floor if we're above floor 0
            # Not using elif so both conditions can be true for middle floors
            if self.selected_floor_index > 0:
                self._send_onion_skin_preview()
                
        # Reset temporary variables
        self.temp_vent_start = self.temp_vent_end = None
                
    def handle_floor_selected_request(self, data):
        floor_idx = data.get("floor_index")
        
        # Check if floor index is valid
        if floor_idx is not None and 0 <= floor_idx < len(self.floors):
            previous_floor_index = self.selected_floor_index
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
                    "fill":  "#EE82EE",
                    "thickness": window_obj.thickness
                })

            for door_objet in selected_floor.doors:
                ivy_bus.publish("draw_door_update", {
                    "start": door_objet.start,
                    "end":   door_objet.end,
                    "fill":  "#8B4513",
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
            
            # If this is the initial floor selection, also send the floor list
            ivy_bus.publish("new_floor_update", {
                "floors": [f.name for f in self.floors],
                "selected_floor_index": self.selected_floor_index
            })

            self._publish_height(selected_floor)
            
            # Send onion skin preview data if applicable
            self._send_onion_skin_preview()
        
    def handle_new_floor_request(self, data):
        """
        When the user clicks the "New floor" button: insert a new floor above the selected floor
        If no floor is currently selected (or there is no floor at all), make it the first floor
        Clear automatic the canvas
        """
        ivy_bus.publish("clear_canvas_update", {})
        new_floor_name = f"etage {len(self.floors)}"
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
        
        # Send onion skin preview if we're not on the first floor
        if self.selected_floor_index > 0:
            self._send_onion_skin_preview()

    def handle_tool_selected_request(self, data):
        """
        when user click the botton of outils
        """
        tool = data.get("tool")

        if self.selected_floor_index is None:
            ivy_bus.publish("show_alert_request",{
                "title": "Aucun etage disponible",
                "message": "Vous devez creer un etage avant d'utiliser les outils."
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
                "title":"Nom d'etage vide",
                "message":"L'etage doit avoir un nom"
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
            
        # If we are on a floor above 0, we need to refresh the onion skin 
        # in case the floor below was modified
        if self.selected_floor_index > 0:
            # Check if the floor that was modified is the one below the current floor
            if floor == self.floors[self.selected_floor_index - 1]:
                # Refresh onion skin preview
                self._send_onion_skin_preview()
    
    def _publish_height(self, floor):
        ivy_bus.publish("floor_height_update", {"height": floor.height})

    def handle_set_floor_height_request(self, data):
        idx    = data["floor_index"]
        height = data["height"]
        if 0 <= idx < len(self.floors):
            self.floors[idx].set_height(height)
            if idx == self.selected_floor_index:
                self._publish_height(self.floors[idx])

    def handle_delete_floor_request(self, data):
        floor_index = data.get("floor_index")
        
        if floor_index is None or floor_index < 0 or floor_index >= len(self.floors):
            return

        if len(self.floors) <= 1:
            ivy_bus.publish("show_alert_request", {
                "title": "Impossible de supprimer l'etage",
                "message": "Vous ne pouvez pas supprimer le dernier etage."
            })
            return

        # Store the floor name for logging
        deleted_floor_name = self.floors[floor_index].name
        
        # Remove the floor
        self.floors.pop(floor_index)
        
        # Adjust the selected floor index if needed
        if self.selected_floor_index == floor_index:
            # If we deleted the selected floor, select another one
            if floor_index >= len(self.floors):
                self.selected_floor_index = len(self.floors) - 1
            # Otherwise keep the same index (it will now point to the next floor)
        elif self.selected_floor_index > floor_index:
            # If we deleted a floor before the selected one, decrement the index
            self.selected_floor_index -= 1
            
        print(f"[Controller] deleted floor {deleted_floor_name}, new selected index = {self.selected_floor_index}")
        
        # Update the UI
        ivy_bus.publish("clear_canvas_update", {})
        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })
        
        # Select and draw the new floor
        selected_floor = self.floors[self.selected_floor_index]
        self.handle_floor_selected_request({"floor_index": self.selected_floor_index})

    def handle_onion_skin_preview_request(self, data):
        """Handle request for onion skin preview of the floor below"""
        self._send_onion_skin_preview()
        
    def _send_onion_skin_preview(self):
        """Send data for onion skin preview of the floor below current floor"""
        if self.selected_floor_index is None or self.selected_floor_index <= 0:
            # No floor below to show
            return
            
        # Get the floor below
        floor_below_index = self.selected_floor_index - 1
        floor_below = self.floors[floor_below_index]
        
        # Prepare items to be drawn in onion skin
        items = []
        
        # Add walls
        for wall in floor_below.walls:
            items.append({
                "type": "wall",
                "coords": (wall.start, wall.end),
                "fill": "black"
            })
            
        # Add windows
        for window in floor_below.windows:
            items.append({
                "type": "window",
                "coords": (window.start, window.end),
                "fill": "#EE82EE",
                "thickness": window.thickness
            })
            
        # Add doors
        for door in floor_below.doors:
            items.append({
                "type": "door",
                "coords": (door.start, door.end),
                "fill": "#8B4513",
                "thickness": door.thickness
            })
            
        # Add vents
        for vent in floor_below.vents:
            items.append({
                "type": "vent",
                "coords": (vent.start, vent.end),
                "fill": vent.color,
                "additional_data": {
                    "name": vent.name,
                    "diameter": vent.diameter,
                    "flow_rate": vent.flow_rate,
                    "function": vent.function
                }
            })
            
        # Send the data to the view
        ivy_bus.publish("onion_skin_preview_update", {
            "items": items,
            "floor_below_index": floor_below_index,
            "floor_below_name": floor_below.name
        })

    def handle_save_project_request(self, _data):
        """
        Save as：
        └─ save_20250421_153730/
           ├─ floors.json
           ├─ floor_0.png
           ├─ floor_1.png
           └─ ...
        """
        json_data = [floor.to_dict() for floor in self.floors]

        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir   = os.path.join(os.getcwd(), f"save_{ts}")
        os.makedirs(save_dir, exist_ok=True)

        json_path  = os.path.join(save_dir, "floors.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

        for idx, floor in enumerate(self.floors):
            xs, ys = [], []
            for w in floor.walls:
                xs += [w.start[0], w.end[0]]
                ys += [w.start[1], w.end[1]]
            for win in floor.windows:
                xs += [win.start[0], win.end[0]]
                ys += [win.start[1], win.end[1]]
            for d in floor.doors:
                xs += [d.start[0], d.end[0]]
                ys += [d.start[1], d.end[1]]
            for v in floor.vents:
                xs += [v.start[0], v.end[0]]
                ys += [v.start[1], v.end[1]]

            if not xs or not ys:
                Image.new("RGB", (600, 400), "white").save(
                    os.path.join(save_dir, f"floor_{idx}.png"))
                continue

            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            MARGIN = 30
            W = int(math.ceil(x_max - x_min + 2 * MARGIN))
            H = int(math.ceil(y_max - y_min + 2 * MARGIN))

            img  = Image.new("RGB", (W, H), "white")
            draw = ImageDraw.Draw(img)

            def tr(p):
                return (int(round(p[0] - x_min + MARGIN)),
                        int(round(p[1] - y_min + MARGIN)))

            for w in floor.walls:
                draw.line([tr(w.start), tr(w.end)],
                          fill="black", width=6)

            for win in floor.windows:
                draw.line([tr(win.start), tr(win.end)],
                          fill="#EE82EE", width=win.thickness)

            for d in floor.doors:
                draw.line([tr(d.start), tr(d.end)],
                          fill="#8B4513", width=d.thickness)

            for v in floor.vents:
                p1, p2 = tr(v.start), tr(v.end)
                draw.line([p1, p2], fill=v.color, width=2)

                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                length = math.hypot(dx, dy) or 1
                ux, uy = dx / length, dy / length

                arrow_len = 10
                arrow_wid = 5
                left  = (p2[0] - arrow_len * ux + arrow_wid * uy,
                         p2[1] - arrow_len * uy - arrow_wid * ux)
                right = (p2[0] - arrow_len * ux - arrow_wid * uy,
                         p2[1] - arrow_len * uy + arrow_wid * ux)
                draw.polygon([p2, left, right], fill=v.color)

            safe_name = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in floor.name).strip()
            safe_name = safe_name.replace(' ', '_') or f"floor_{idx}"
            img_path = os.path.join(save_dir, f"{safe_name}.png")
            img.save(img_path)

        ivy_bus.publish("show_alert_request", {
            "title": "Enregistré avec succès",
            "message": f"Projet enregistré dans le dossier: \n{save_dir}"
        })

    def handle_import_project_request(self, data):

        json_path = data.get("json_path")
        if not json_path or not os.path.exists(json_path):
            ivy_bus.publish("show_alert_request", {
                "title": "L'importation a échoué",
                "message": "Le fichier n'existe pas !"
            })
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                floors_data = json.load(f)
        except Exception as e:
            ivy_bus.publish("show_alert_request", {
                "title": "L'importation a échoué",
                "message": f"Erreur lors de l'analyse de JSON：{e}"
            })
            return

        new_floors = []
        for f_dict in floors_data:
            floor_obj = Floor(f_dict.get("name", "etage ?"))
            floor_obj.height = f_dict.get("height", 2.5)

            # walls
            for w in f_dict.get("walls", []):
                floor_obj.add_wall(Wall(tuple(w["start"]), tuple(w["end"])))

            # windows
            for w in f_dict.get("windows", []):
                floor_obj.add_window(
                    Window(tuple(w["start"]), tuple(w["end"]),
                        thickness=w.get("thickness", 5))
                )

            # doors
            for d in f_dict.get("doors", []):
                floor_obj.add_door(
                    Door(tuple(d["start"]), tuple(d["end"]),
                        thickness=d.get("thickness", 5))
                )

            # vents
            for v in f_dict.get("vents", []):
                floor_obj.add_vent(
                    Vent(tuple(v["start"]), tuple(v["end"]),
                        v.get("name", ""), v.get("diameter", ""),
                        v.get("flow_rate", ""), v.get("function", ""),
                        v.get("color", "#000"))
                )

            new_floors.append(floor_obj)

        if not new_floors:
            ivy_bus.publish("show_alert_request", {
                "title": "L'importation a échoué",
                "message": "Aucune donnée d'étage trouvée dans JSON"
            })
            return

        self.floors = new_floors
        self.selected_floor_index = 0

        ivy_bus.publish("clear_canvas_update", {})

        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })

        self.handle_floor_selected_request({"floor_index": 0})

        ivy_bus.publish("show_alert_request", {
            "title": "Importation terminée",
            "message": "Projet importé avec succès"
        })