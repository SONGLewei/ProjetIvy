import os, json, math
from datetime import datetime
from PIL import Image, ImageDraw
from ivy.ivy_bus import ivy_bus
from model.wall import Wall
from model.floor import Floor
from model.window import Window
from model.door import Door
from model.vent import Vent
from model.plenum import Plenum
from tkinter import simpledialog

class Controller:
    def __init__(self):
        self.floors = []
        self.selected_floor_index = None
        self.current_tool = 'select'
        self.floor_count = 0

        # Create default Floor 0
        default_floor = Floor("Etage 0")
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
        ivy_bus.subscribe("cancel_plenum_request",  self.handle_cancel_plenum)
        ivy_bus.subscribe("plenum_cleared_notification", self.handle_plenum_cleared)

        ivy_bus.subscribe("delete_item_request", self.handle_delete_item_request)
        ivy_bus.subscribe("set_floor_height_request", self.handle_set_floor_height_request)
        ivy_bus.subscribe("delete_floor_request", self.handle_delete_floor_request)
        ivy_bus.subscribe("onion_skin_preview_request", self.handle_onion_skin_preview_request)

        ivy_bus.subscribe("save_project_request", self.handle_save_project_request)
        ivy_bus.subscribe("import_project_request", self.handle_import_project_request)
        
        # Add a handler for ventilation summary requests
        ivy_bus.subscribe("get_ventilation_summary_request", self.handle_get_ventilation_summary_request)
        
        # Add a handler for reset application requests
        ivy_bus.subscribe("reset_app_request", self.handle_reset_app_request)

        ivy_bus.subscribe("create_plenum_request", self.handle_create_plenum_request)
        
        # Add a handler for floor duplication
        ivy_bus.subscribe("duplicate_floor_request", self.handle_duplicate_floor_request)

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

        self.the_plenum = None

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

                # Check if window overlaps with any wall and modify the wall
                wall_modified, aligned_start, aligned_end = self._check_wall_overlap(start, end, is_window=True)
                
                # Create window with aligned coordinates if a wall was modified
                if wall_modified:
                    window_obj = Window(aligned_start, aligned_end, thickness=5)
                else:
                    window_obj = Window(start, end, thickness=5)

                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_window(window_obj)
                print(f"in floor {current_floor.name} create window : {window_obj}")

                ivy_bus.publish(
                    "draw_window_update",
                    {
                        "start": window_obj.start,
                        "end": window_obj.end,
                        "fill": "#ffafcc",
                        "thickness": window_obj.thickness,
                    },
                )

                # Redraw all walls to reflect any modifications made by _check_wall_overlap
                ivy_bus.publish("clear_canvas_update", {"redraw_operation": True})
                
                # Redraw all walls
                for wall_obj in current_floor.walls:
                    ivy_bus.publish("draw_wall_update", {
                        "start": wall_obj.start,
                        "end":   wall_obj.end,
                        "fill":  "black",
                    })
                
                # Redraw all windows
                for window_item in current_floor.windows:
                    ivy_bus.publish("draw_window_update", {
                        "start": window_item.start,
                        "end": window_item.end,
                        "fill": "#ffafcc",
                        "thickness": window_item.thickness,
                    })
                
                # Redraw all doors
                for door_item in current_floor.doors:
                    ivy_bus.publish("draw_door_update", {
                        "start": door_item.start,
                        "end": door_item.end,
                        "fill": "#dda15e",
                        "thickness": door_item.thickness,
                    })
                
                # Redraw all vents
                for vent_item in current_floor.vents:
                    ivy_bus.publish("draw_vent_update", {
                        "start": vent_item.start,
                        "end": vent_item.end,
                        "color": vent_item.color,
                        "name": vent_item.name,
                        "diameter": vent_item.diameter,
                        "flow": vent_item.flow_rate,
                        "role": vent_item.function
                    })
                
                # Redraw plenum if it exists
                if hasattr(current_floor, "plenums") and current_floor.plenums:
                    for plenum in current_floor.plenums:
                        ivy_bus.publish("draw_plenum_update", {
                            "start": plenum.start,
                            "end": plenum.end,
                            "max_flow": plenum.max_flow,
                            "type": plenum.type,
                            "area": plenum.area
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

                # Check if door overlaps with any wall and modify the wall
                wall_modified, aligned_start, aligned_end = self._check_wall_overlap(start, end, is_door=True)
                
                # Create door with aligned coordinates if a wall was modified
                if wall_modified:
                    door_obj = Door(aligned_start, aligned_end, thickness=5)
                else:
                    door_obj = Door(start, end, thickness=5)

                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_door(door_obj)
                print(f"in floor {current_floor.name} create door : {door_obj}")

                ivy_bus.publish(
                    "draw_door_update",
                    {
                        "start": door_obj.start,
                        "end": door_obj.end,
                        "fill": "#dda15e",
                        "thickness": door_obj.thickness,
                    },
                )

                # Redraw all walls to reflect any modifications made by _check_wall_overlap
                # Mark this as a redraw operation, not a full clear
                ivy_bus.publish("clear_canvas_update", {"redraw_operation": True})
                
                # Redraw all walls
                for wall_obj in current_floor.walls:
                    ivy_bus.publish("draw_wall_update", {
                        "start": wall_obj.start,
                        "end":   wall_obj.end,
                        "fill":  "black",
                    })
                
                # Redraw all windows
                for window_item in current_floor.windows:
                    ivy_bus.publish("draw_window_update", {
                        "start": window_item.start,
                        "end": window_item.end,
                        "fill": "#ffafcc",
                        "thickness": window_item.thickness,
                    })
                
                # Redraw all doors
                for door_item in current_floor.doors:
                    ivy_bus.publish("draw_door_update", {
                        "start": door_item.start,
                        "end": door_item.end,
                        "fill": "#dda15e",
                        "thickness": door_item.thickness,
                    })
                
                # Redraw all vents
                for vent_item in current_floor.vents:
                    ivy_bus.publish("draw_vent_update", {
                        "start": vent_item.start,
                        "end": vent_item.end,
                        "color": vent_item.color,
                        "name": vent_item.name,
                        "diameter": vent_item.diameter,
                        "flow": vent_item.flow_rate,
                        "role": vent_item.function
                    })
                
                # Redraw plenum if it exists
                if hasattr(current_floor, "plenums") and current_floor.plenums:
                    for plenum in current_floor.plenums:
                        ivy_bus.publish("draw_plenum_update", {
                            "start": plenum.start,
                            "end": plenum.end,
                            "max_flow": plenum.max_flow,
                            "type": plenum.type,
                            "area": plenum.area
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
            # First click sets the center of the circle
            self.vent_start_point = (x, y)
            self.vent_role  = role
            self.vent_color = color
            return

        if is_click and self.vent_start_point is not None:
            # Second click determines the radius
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
            # Preview the circle as the mouse moves
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
        flow_rate = data.get("flow", "N/A")
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
            
            # Send update for ventilation summary
            self.handle_get_ventilation_summary_request({})

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

            # Check if the selected floor has plenums and update the state
            has_plenum = hasattr(selected_floor, "plenums") and len(selected_floor.plenums) > 0
            if has_plenum:
                self.the_plenum = True
                ivy_bus.publish("disable_tool_button", {"tool": "plenum"})
            else:
                self.the_plenum = None
                ivy_bus.publish("enable_tool_button", {"tool": "plenum"})

            # told View to redraw all the walls      Il faut dire tous les objets apres iciiiiiiiiiiii
            for wall_obj in selected_floor.walls:
                ivy_bus.publish("draw_wall_update", {
                    "start": wall_obj.start,
                    "end":   wall_obj.end,
                    "fill":  "black",
                })

            for window_obj in selected_floor.windows:
                ivy_bus.publish(
                    "draw_window_update",
                    {
                        "start": window_obj.start,
                        "end": window_obj.end,
                        "fill": "#ffafcc",
                        "thickness": window_obj.thickness,
                    },
                )

            for door_objet in selected_floor.doors:
                ivy_bus.publish(
                    "draw_door_update",
                    {
                        "start": door_objet.start,
                        "end": door_objet.end,
                        "fill": "#dda15e",
                        "thickness": door_objet.thickness,
                    },
                )

            for v in selected_floor.vents:
                ivy_bus.publish("draw_vent_update", {
                    "start": v.start, "end": v.end,
                    "color": v.color,
                    "name": v.name,
                    "diameter": v.diameter,
                    "flow": v.flow_rate,
                    "role": v.function
                })

            for p in getattr(selected_floor, "plenums", []):
                ivy_bus.publish("draw_plenum_update", {
                    "start": p.start,
                    "end": p.end,
                    "max_flow": p.max_flow,
                    "type": p.type,
                    "area": p.area
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
        new_floor_name = f"Etage {len(self.floors)}"
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

    #def handle_modifier_the_maxflow_request(self,data):


    def handle_tool_selected_request(self, data):
        """
        when user click the botton of outils
        """
        tool = data.get("tool")

        if tool == 'plenum' and self.the_plenum is not None:
             ivy_bus.publish("show_alert_request", {
                 "title": "Plenum Existant",
                 "message": "Un seul plenum peut être créé dans l'application."
             })

             ivy_bus.publish("tool_selected_update", {"tool": 'select'})
             self.current_tool = 'select'
             return

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

        # Unpack data
        obj_type = data.get("type")
        coords = data.get("coords")
        print(f"[Controller] Deleting {obj_type} with coords {coords}")
        
        floor = self.floors[self.selected_floor_index]
        
        if obj_type == "vent":
            # For circular vents, the coordinates are [left, top, right, bottom]
            # We need to convert these to center and radius points
            if len(coords) == 4:
                left, top, right, bottom = map(float, coords)
                # Calculate center point
                center_x = (left + right) / 2
                center_y = (top + bottom) / 2
                # Calculate a point on the edge (representing the end point)
                radius = (right - left) / 2
                edge_x = center_x + radius
                edge_y = center_y
                
                # These are the points we'll use to identify the vent
                start = (center_x, center_y)
                end = (edge_x, edge_y)
                
                # Find the vent to delete by checking if it's close to these points
                vents_to_delete = []
                for i, vent in enumerate(floor.vents):
                    # Calculate center distance
                    dx = vent.start[0] - start[0]
                    dy = vent.start[1] - start[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    # If center is within 10 pixels, consider it a match
                    if distance <= 10:
                        vents_to_delete.append(i)
                
                # Delete identified vents (in reverse order to avoid index issues)
                for i in sorted(vents_to_delete, reverse=True):
                    print(f"[Controller] Deleting vent at index {i} with start {floor.vents[i].start}")
                    del floor.vents[i]
                
                # Send update for ventilation summary if a vent was deleted
                if vents_to_delete:
                    self.handle_get_ventilation_summary_request({})
            else:
                # For backwards compatibility with older code that might send start/end points
                x1, y1, x2, y2 = map(float, coords[:4])
                start = (x1, y1)
                end = (x2, y2)
                
                def same_segment(o):
                    return ({o.start, o.end} == {start, end})
                
                floor.vents = [v for v in floor.vents if not same_segment(v)]
                self.handle_get_ventilation_summary_request({})
        else:
            # For walls, windows, doors, plenums - use the original method
            if len(coords) >= 4:
                x1, y1, x2, y2 = map(float, coords[:4])
                start = (x1, y1)
                end = (x2, y2)
                
                def same_segment(o):
                    return ({o.start, o.end} == {start, end})

                if obj_type == "wall":
                    floor.walls = [w for w in floor.walls if not same_segment(w)]
                elif obj_type == "window":
                    floor.windows = [w for w in floor.windows if not same_segment(w)]
                elif obj_type == "door":
                    floor.doors = [d for d in floor.doors if not same_segment(d)]
                elif obj_type == "plenum":
                    # Delete the plenum from both the controller reference and the floor's plenums list
                    self.the_plenum = None
                    if hasattr(floor, "plenums"):
                        # Match plenum by coordinates (start and end)
                        floor.plenums = [p for p in floor.plenums if not same_segment(p)]
                        print(f"[Controller] Deleted plenum, remaining: {len(floor.plenums)}")
                        
                        # Re-enable the plenum button when a plenum is deleted
                        if len(floor.plenums) == 0:
                            ivy_bus.publish("enable_tool_button", {"tool": "plenum"})

        # Always refresh the onion skin display after deletion
        # This will ensure the onion skin is correctly updated
        self._send_onion_skin_preview()

        # Additionally, if this is the floor below the current selected floor,
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
            
        # Force view to refresh onion skin after deletion
        ivy_bus.publish("ensure_onion_skin_refresh", {})

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

    def handle_create_plenum_request(self, data):
        start_x = data["start_x"]
        start_y = data["start_y"]
        end_x   = data["end_x"]
        end_y   = data["end_y"]

        if self.the_plenum:
            ivy_bus.publish("show_alert_request", {
                "title": "Plenum Existant",
                "message": "Un seul plenum peut être créé dans l'application. L'opération a été annulée." 
            })
            return
        
        # Mark that we're starting plenum creation, but will reset if cancelled
        temp_plenum = True
            
        if self.selected_floor_index is None:
            return
        
        max_flow = None
        try:
            max_flow_str = simpledialog.askstring(
                "Débit Maximal du Plenum",
                "Entrez le débit maximal (m3/h) pour ce plenum:",
                initialvalue="1000"
            )

            if max_flow_str:
                try:
                    max_flow_val = int(max_flow_str)
                    if max_flow_val >= 0:
                        max_flow = max_flow_val
                        print(f"[Controller] User provided max_flow: {max_flow}")
                    else:
                        ivy_bus.publish("show_alert_request", {"title": "Entrée invalide", "message": "Le débit doit être un nombre positif."})
                        return
                except ValueError:
                     ivy_bus.publish("show_alert_request", {"title": "Entrée invalide", "message": "Veuillez entrer un nombre entier valide."})
                     return
            else:
                 print("[Controller] Plenum creation cancelled by user during flow input.")
                 # Reset the plenum state since this was cancelled
                 self.the_plenum = None
                 return

        except Exception as e:
             print(f"[Controller] Error showing simpledialog or processing input: {e}")
             # Reset the plenum state in case of error
             self.the_plenum = None
             return

        plenum_type = None
        if max_flow is not None:
            try:
                # Create a custom dialog for plenum type selection
                from tkinter import Toplevel, StringVar, Label, Button

                def get_plenum_type():
                    # Create a custom dialog for type selection
                    dialog = Toplevel()
                    dialog.title("Type de Plenum")
                    # Don't set fixed size to allow proper sizing based on content
                    dialog.resizable(False, False)
                    dialog.grab_set()  # Make it modal
                    
                    # Add styling with ttk
                    from tkinter import ttk
                    style = ttk.Style()
                    
                    # Configure style for better appearance on macOS
                    if 'darwin' in os.sys.platform:
                        style.configure('TLabel', font=('Helvetica', 13))
                        style.configure('TButton', font=('Helvetica', 12))
                        style.configure('TCombobox', font=('Helvetica', 12))
                        style.configure('Header.TLabel', font=('Helvetica', 14, 'bold'))
                    else:
                        style.configure('TLabel', font=('Arial', 11))
                        style.configure('TButton', font=('Arial', 11))
                        style.configure('TCombobox', font=('Arial', 11))
                        style.configure('Header.TLabel', font=('Arial', 13, 'bold'))
                    
                    # Configure the dialog background
                    dialog.configure(background='#f0f0f0')
                    
                    # Create container frame with padding
                    main_frame = ttk.Frame(dialog, padding=(20, 15, 20, 15))
                    main_frame.pack(fill="both", expand=False)
                    
                    # Create header with title
                    header = ttk.Label(main_frame, text="Type de Plenum", style='Header.TLabel')
                    header.pack(pady=(0, 15), anchor="w")
                    
                    # Create label
                    ttk.Label(main_frame, text="Choisissez le type de plenum:").pack(pady=(5, 8), anchor="w")
                    
                    # Create selection variable and set default
                    selection = StringVar(dialog)
                    selection.set("Simple")  # Default value
                    
                    # Create the option menu
                    combo = ttk.Combobox(main_frame, textvariable=selection, values=["Simple", "Double"], state="readonly")
                    combo.pack(pady=(0, 15), fill="x")
                    
                    # Result variable to store the selection
                    result = {"value": None}
                    
                    # Button callbacks
                    def on_ok():
                        result["value"] = selection.get()
                        dialog.destroy()
                        
                    def on_cancel():
                        dialog.destroy()
                    
                    # Add a separator above buttons
                    separator = ttk.Separator(main_frame, orient="horizontal")
                    separator.pack(fill="x", pady=(5, 10))
                    
                    # Create buttons with better styling
                    button_frame = ttk.Frame(main_frame)
                    button_frame.pack(fill="x", pady=(0, 0))
                    
                    # Create buttons with consistent width
                    ok_button = ttk.Button(button_frame, text="OK", command=on_ok, width=10)
                    cancel_button = ttk.Button(button_frame, text="Annuler", command=on_cancel, width=10)
                    
                    # Position buttons
                    cancel_button.pack(side="right", padx=(5, 0))
                    ok_button.pack(side="right", padx=(5, 0))
                    
                    # Set initial focus to combobox
                    combo.focus_set()
                    
                    # Update dialog size to fit content
                    dialog.update_idletasks()
                    dialog.geometry("")  # Reset geometry to fit content
                    
                    # Center the dialog on screen
                    width = dialog.winfo_reqwidth()
                    height = dialog.winfo_reqheight()
                    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
                    y = (dialog.winfo_screenheight() // 2) - (height // 2)
                    dialog.geometry(f"{width}x{height}+{x}+{y}")
                    
                    # Wait for the dialog to close
                    dialog.wait_window()
                    return result["value"]
                
                # Show the dialog and get the selection
                plenum_type = get_plenum_type()
                if plenum_type:
                    print(f"[Controller] User selected plenum type: {plenum_type}")
                else:
                    plenum_type = None
                    print("[Controller] User did not select a plenum type or cancelled.")

            except Exception as e:
                 print(f"[Controller] Error showing plenum type dialog: {e}")
                 plenum_type = None

        if max_flow is not None: 
            print("[Controller] Creating the single plenum object...")
            start_coords = (start_x, start_y)
            end_coords = (end_x, end_y)

            plenum_obj = Plenum(start_coords, end_coords, max_flow=max_flow) 
            plenum_obj.type = plenum_type
            plenum_obj.floor_index = self.selected_floor_index

            # Now that creation is confirmed, officially set the plenum
            self.the_plenum = plenum_obj 
            
            print(f"[Controller] Created the single plenum object on floor {plenum_obj.floor_index}: {plenum_obj} with Type: {plenum_obj.type}")
            
            current_floor = self.floors[self.selected_floor_index] 
            if not hasattr(current_floor, "plenums"):
                 current_floor.plenums = []
            current_floor.plenums.append(plenum_obj)

            ivy_bus.publish("draw_plenum_update", {
                "start": plenum_obj.start,
                "end": plenum_obj.end,
                "max_flow": plenum_obj.max_flow,
                "type": plenum_obj.type,
                "area": plenum_obj.area
            })

            # Disable the plenum button
            ivy_bus.publish("disable_tool_button", {"tool": "plenum"})
            
            # Switch to the selection tool automatically after placing a plenum
            self.current_tool = 'select'
            ivy_bus.publish("tool_selected_update", {"tool": 'select'})
        
        else:
             print("[Controller] Failed to get valid max_flow, plenum not created.")
             # Reset the plenum state since we couldn't create it
             self.the_plenum = None

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
            items.append(
                {
                    "type": "window",
                    "coords": (window.start, window.end),
                    "fill": "#ffafcc",
                    "thickness": window.thickness,
                }
            )

        # Add doors
        for door in floor_below.doors:
            items.append(
                {
                    "type": "door",
                    "coords": (door.start, door.end),
                    "fill": "#dda15e",
                    "thickness": door.thickness,
                }
            )

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
            
        # Add plenums
        if hasattr(floor_below, "plenums"):
            for plenum in floor_below.plenums:
                items.append({
                    "type": "plenum",
                    "coords": (plenum.start, plenum.end),
                    "fill": "blue",
                    "additional_data": {
                        "max_flow": plenum.max_flow,
                        "type": plenum.type,
                        "area": plenum.area
                    }
                })

        # Send the data to the view
        ivy_bus.publish("onion_skin_preview_update", {
            "items": items,
            "floor_below_index": floor_below_index,
            "floor_below_name": floor_below.name
        })

    def handle_save_project_request(self, data):
        """
        Save project to the selected JSON file
        """
        json_data = [floor.to_dict() for floor in self.floors]

        # Get the JSON file path from the data
        json_file_path = data.get("json_file_path")

        if not json_file_path:
            # Use a timestamped file in current working directory as fallback
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file_path = os.path.join(os.getcwd(), f"floors_{ts}.json")

        # Save the JSON file
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

        # Success alert removed for a cleaner experience
        print(f"[Controller] Project saved to: {json_file_path}")

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
        plenum_found_in_import = False
        for f_dict in floors_data:
            floor_obj = Floor(f_dict.get("name", "Etage ?"))
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
                flow_rate = v.get("flow_rate", "") or v.get("flow", "")  # Try both keys for compatibility
                function = v.get("function", "") or v.get("role", "extraction_interne")  # Default to extraction_interne if missing
                
                # Determine color based on function if not provided
                color = v.get("color", "")
                if not color:
                    if function == "extraction_interne":
                        color = "#ff0000"  # Red
                    elif function == "insufflation_interne":
                        color = "#ff9900"  # Orange
                    elif function == "extraction_externe":
                        color = "#4c7093"  # Dark blue
                    elif function == "admission_externe":
                        color = "#66ccff"  # Light blue
                    else:
                        color = "#000000"  # Black fallback
                        
                floor_obj.add_vent(
                    Vent(tuple(v["start"]), tuple(v["end"]),
                        v.get("name", ""), v.get("diameter", ""),
                        flow_rate, function, color)
                )
            
            if "plenums" in f_dict: 
                 if not hasattr(floor_obj, 'plenums'): floor_obj.plenums = [] 
                 for p_data in f_dict["plenums"]:
                     try:
                         plenum_instance = Plenum.from_dict(p_data) 
                         floor_obj.add_plenum(plenum_instance) 
                         plenum_found_in_import = True 
                     except Exception as e_plenum:
                         print(f"Error loading plenum data {p_data}: {e_plenum}") 

            new_floors.append(floor_obj)

        if not new_floors:
            ivy_bus.publish("show_alert_request", {
                "title": "L'importation a échoué",
                "message": "Aucune donnée d'étage trouvée dans JSON"
            })
            return

        self.floors = new_floors
        self.selected_floor_index = 0

        if plenum_found_in_import:
            self.the_plenum = True # **恢复你的布尔标记**
            print("[Controller] Plenum(s) found in import. Setting flag and disabling button.")
            ivy_bus.publish("disable_tool_button", {"tool": "plenum"}) # **禁用按钮**
        else:
            self.the_plenum = None # **重置标记为 None**
            print("[Controller] No plenums found in import. Resetting flag and enabling button.")
            ivy_bus.publish("enable_tool_button", {"tool": "plenum"}) # **启用按钮**

        ivy_bus.publish("clear_canvas_update", {})

        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })

        self.handle_floor_selected_request({"floor_index": 0})
        
        # Send ventilation summary data after importing
        self.handle_get_ventilation_summary_request({})

        # If the first floor is selected and there's more than one floor, force onion skin refresh
        if self.selected_floor_index > 0:
            self._send_onion_skin_preview()
        
        # Force view to refresh onion skin
        ivy_bus.publish("ensure_onion_skin_refresh", {})

        # Success alert removed for a cleaner experience
        print(f"[Controller] Project imported successfully from: {json_path}")

    def handle_get_ventilation_summary_request(self, data):
        """Handle request for ventilation summary data from all floors"""
        all_vents_data = []
        all_plenums_data = []
        
        # Collect vents and plenums from all floors
        for floor_idx, floor in enumerate(self.floors):
            # Add vents
            for vent in floor.vents:
                all_vents_data.append({
                    "floor_name": floor.name,
                    "floor_index": floor_idx,
                    "name": vent.name,
                    "diameter": vent.diameter,
                    "flow_rate": vent.flow_rate,
                    "function": vent.function,
                    "color": vent.color
                })
            
            # Add plenums if present
            if hasattr(floor, "plenums") and floor.plenums:
                for plenum in floor.plenums:
                    if hasattr(plenum, 'to_dict'):
                        plenum_data = plenum.to_dict()
                        plenum_data['floor_name'] = floor.name
                        plenum_data['floor_index'] = floor_idx
                        plenum_data['height'] = floor.height
                        all_plenums_data.append(plenum_data)
        
        # Debug output to verify data
        print(f"[Controller] Sending ventilation summary with {len(all_vents_data)} vents and {len(all_plenums_data)} plenums")
        
        # Send the combined data to the view
        ivy_bus.publish("ventilation_summary_update", {
            "vents": all_vents_data,
            "plenums": all_plenums_data
        })

    def _check_wall_overlap(self, start, end, is_door=False, is_window=False):
        """
        Checks if a door or window overlaps with any wall and removes the overlapping wall segment.
        Also aligns the door/window precisely with the wall's position.
        
        Args:
            start: The start coordinates of the door or window
            end: The end coordinates of the door or window
            is_door: Whether this is a door object
            is_window: Whether this is a window object
            
        Returns:
            tuple: (bool, new_start, new_end) - Whether a wall was modified and the aligned coordinates
        """
        if self.selected_floor_index is None:
            return False, start, end
            
        current_floor = self.floors[self.selected_floor_index]
        
        # Determine orientation
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        is_horizontal = dx >= dy
        
        for i, wall in enumerate(current_floor.walls):
            wall_dx = abs(wall.end[0] - wall.start[0])
            wall_dy = abs(wall.end[1] - wall.start[1])
            is_wall_horizontal = wall_dx >= wall_dy
            
            # Check if orientations match (both horizontal or both vertical)
            if is_horizontal == is_wall_horizontal:
                if is_horizontal:
                    # For horizontal elements, check if y-coordinates match
                    if abs(start[1] - wall.start[1]) < 10:  # Allow small tolerance
                        # Check for overlap in x-coordinates
                        min_x = min(start[0], end[0])
                        max_x = max(start[0], end[0])
                        wall_min_x = min(wall.start[0], wall.end[0])
                        wall_max_x = max(wall.start[0], wall.end[0])
                        
                        # If there's an overlap
                        if max_x >= wall_min_x and min_x <= wall_max_x:
                            overlap_min_x = max(min_x, wall_min_x)
                            overlap_max_x = min(max_x, wall_max_x)
                            
                            # If the overlap is significant
                            if overlap_max_x - overlap_min_x > 5:
                                # Align the door/window exactly with the overlapping segment
                                # Use the wall's exact y-coordinate for perfect alignment
                                aligned_start = (overlap_min_x, wall.start[1])
                                aligned_end = (overlap_max_x, wall.start[1])
                                
                                # Remove the original wall
                                current_floor.walls.pop(i)
                                
                                # Create two new walls if needed (before and after the door/window)
                                y = wall.start[1]
                                if wall_min_x < overlap_min_x:
                                    new_wall1 = Wall((wall_min_x, y), (overlap_min_x, y))
                                    current_floor.add_wall(new_wall1)
                                    
                                if overlap_max_x < wall_max_x:
                                    new_wall2 = Wall((overlap_max_x, y), (wall_max_x, y))
                                    current_floor.add_wall(new_wall2)
                                
                                return True, aligned_start, aligned_end
                else:
                    # For vertical elements, check if x-coordinates match
                    if abs(start[0] - wall.start[0]) < 10:  # Allow small tolerance
                        # Check for overlap in y-coordinates
                        min_y = min(start[1], end[1])
                        max_y = max(start[1], end[1])
                        wall_min_y = min(wall.start[1], wall.end[1])
                        wall_max_y = max(wall.start[1], wall.end[1])
                        
                        # If there's an overlap
                        if max_y >= wall_min_y and min_y <= wall_max_y:
                            overlap_min_y = max(min_y, wall_min_y)
                            overlap_max_y = min(max_y, wall_max_y)
                            
                            # If the overlap is significant
                            if overlap_max_y - overlap_min_y > 5:
                                # Align the door/window exactly with the overlapping segment
                                # Use the wall's exact x-coordinate for perfect alignment
                                aligned_start = (wall.start[0], overlap_min_y)
                                aligned_end = (wall.start[0], overlap_max_y)
                                
                                # Remove the original wall
                                current_floor.walls.pop(i)
                                
                                # Create two new walls if needed (before and after the door/window)
                                x = wall.start[0]
                                if wall_min_y < overlap_min_y:
                                    new_wall1 = Wall((x, wall_min_y), (x, overlap_min_y))
                                    current_floor.add_wall(new_wall1)
                                    
                                if overlap_max_y < wall_max_y:
                                    new_wall2 = Wall((x, overlap_max_y), (x, wall_max_y))
                                    current_floor.add_wall(new_wall2)
                                
                                return True, aligned_start, aligned_end
        
        return False, start, end

    def handle_reset_app_request(self, data):
        """
        Resets the application to its initial state.
        Clears all floors, walls, vents, etc. and creates a default floor.
        """
        # Create a new default floor
        default_floor = Floor("Etage 0")
        
        # Reset all app state
        self.floors = [default_floor]
        self.selected_floor_index = 0
        self.current_tool = 'select'
        self.floor_count = 0
        
        # Reset all drawing state
        self.wall_start_point = None
        self.is_canceled_wall_draw = False
        self.window_start_point = None
        self.is_canceled_window_draw = False
        self.door_start_point = None
        self.is_canceled_door_draw = False
        self.vent_start_point = None
        self.is_canceled_vent_draw = False
        self.vent_role = None
        self.vent_color = None
        self.temp_vent_start = None
        self.temp_vent_end = None
        self.temp_vent_role = None
        self.temp_vent_color = None
        
        # Reset plenum state
        self.the_plenum = None
        
        # Clear the canvas
        ivy_bus.publish("clear_canvas_update", {})
        
        # Update floor list in UI
        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })
        
        # Update floor selection in UI
        ivy_bus.publish("floor_selected_update", {
            "selected_floor_index": self.selected_floor_index,
            "floor_name": default_floor.name
        })
        
        # Update floor height
        self._publish_height(default_floor)
        
        # Reset tool selection
        ivy_bus.publish("tool_selected_update", {
            "tool": self.current_tool
        })
        
        # Reset ventilation summary
        self.handle_get_ventilation_summary_request({})
        
        # Enable the plenum button - this is the only place we enable it
        ivy_bus.publish("enable_tool_button", {"tool": "plenum"})
        
        print("[Controller] Application has been reset to initial state")

    def handle_cancel_plenum(self, data):
        """Handle cancellation of plenum drawing"""
        # Note: We only reset the plenum state but don't re-enable the button
        # The button will only be re-enabled when the application is reset
        self.the_plenum = None
        # We don't re-enable the button here anymore
        # ivy_bus.publish("enable_tool_button", {"tool": "plenum"})

    def handle_plenum_cleared(self, data):
        """Handle notification that the plenum has been cleared"""
        self.the_plenum = None
        ivy_bus.publish("enable_tool_button", {"tool": "plenum"})

    def handle_duplicate_floor_request(self, data):
        """
        Duplicates a floor with all its contents (walls, windows, doors, vents, plenums)
        """
        floor_index = data.get("floor_index")
        
        if floor_index is None or floor_index < 0 or floor_index >= len(self.floors):
            ivy_bus.publish("show_alert_request", {
                "title": "Erreur de duplication",
                "message": "Impossible de dupliquer cet étage."
            })
            return
            
        # Get the source floor to duplicate
        source_floor = self.floors[floor_index]
        
        # Create a new floor with a derived name
        new_floor_name = f"{source_floor.name} (copie)"
        
        # Create a deep copy of the floor by serializing and deserializing
        source_dict = source_floor.to_dict()
        
        # Create new floor with the new name
        from model.floor import Floor
        from model.wall import Wall
        from model.window import Window
        from model.door import Door
        from model.vent import Vent
        from model.plenum import Plenum
        
        new_floor = Floor(new_floor_name)
        new_floor.height = source_dict["height"]
        
        # Copy walls
        for wall_dict in source_dict["walls"]:
            new_wall = Wall(tuple(wall_dict["start"]), tuple(wall_dict["end"]))
            new_floor.add_wall(new_wall)
            
        # Copy windows
        for window_dict in source_dict["windows"]:
            new_window = Window(
                tuple(window_dict["start"]), 
                tuple(window_dict["end"]),
                thickness=window_dict.get("thickness", 5)
            )
            new_floor.add_window(new_window)
            
        # Copy doors
        for door_dict in source_dict["doors"]:
            new_door = Door(
                tuple(door_dict["start"]), 
                tuple(door_dict["end"]),
                thickness=door_dict.get("thickness", 5)
            )
            new_floor.add_door(new_door)
            
        # Copy vents
        for vent_dict in source_dict["vents"]:
            new_vent = Vent(
                tuple(vent_dict["start"]),
                tuple(vent_dict["end"]),
                vent_dict.get("name", ""),
                vent_dict.get("diameter", ""),
                vent_dict.get("flow_rate", ""),
                vent_dict.get("function", "extraction_interne"),
                vent_dict.get("color", "#ff0000")
            )
            new_floor.add_vent(new_vent)
            
        # Copy plenums
        if "plenums" in source_dict:
            for plenum_dict in source_dict["plenums"]:
                new_plenum = Plenum(
                    tuple(plenum_dict["start"]),
                    tuple(plenum_dict["end"]),
                    max_flow=plenum_dict.get("max_flow", 1000)
                )
                new_plenum.type = plenum_dict.get("type")
                new_plenum.area = plenum_dict.get("area")
                new_floor.add_plenum(new_plenum)
        
        # Insert the new floor after the source floor
        insert_index = floor_index + 1
        self.floors.insert(insert_index, new_floor)
        
        # Update selected floor index to the new floor
        self.selected_floor_index = insert_index
        
        # Clear the canvas
        ivy_bus.publish("clear_canvas_update", {})
        
        # Update the floor list and select the new floor
        ivy_bus.publish("new_floor_update", {
            "floors": [f.name for f in self.floors],
            "selected_floor_index": self.selected_floor_index
        })
        
        # Publish the height of the new floor
        self._publish_height(new_floor)
        
        # Request to draw the floor contents
        self.handle_floor_selected_request({"floor_index": insert_index})
        
        # Send onion skin preview if we're not on the first floor
        if self.selected_floor_index > 0:
            self._send_onion_skin_preview()
            
        print(f"[Controller] Duplicated floor {floor_index} ({source_floor.name}) to position {insert_index} ({new_floor_name})")
