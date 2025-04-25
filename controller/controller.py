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
                ivy_bus.publish("clear_canvas_update", {})
                
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
                ivy_bus.publish("clear_canvas_update", {})
                
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
                    "max_flow": p.max_flow
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

        obj_type = data["type"]
        coords = data["coords"]
        
        # For vents, the coordinates might have more values due to arrow shape
        # Just extract the start and end points we need for comparison
        if obj_type == "vent" and len(coords) > 4:
            # For vents with complex shapes, take just the first 4 coordinates
            x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
        else:
            # For regular items like walls, windows, and doors
            x1, y1, x2, y2 = map(int, coords)
            
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
            # Delete the vent
            floor.vents   = [v for v in floor.vents   if not same_segment(v)]
            # Send update for ventilation summary if a vent was deleted
            self.handle_get_ventilation_summary_request({})
        elif obj_type == "plenum":
            self.the_plenum = None

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
        
        self.the_plenum = True
            
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
                 return

        except Exception as e:
             print(f"[Controller] Error showing simpledialog or processing input: {e}")
             return

        plenum_type = None
        if max_flow is not None:
            try:
                type_str = simpledialog.askstring(
                    "Type de Plenum",
                    "Entrez le type de plenum (ex: simple, double):",
                )

                if type_str:
                    plenum_type = type_str
                    print(f"[Controller] User provided type: {plenum_type}")
                else:

                    plenum_type = None
                    print("[Controller] User did not provide a type or cancelled.")

            except Exception as e:
                 print(f"[Controller] Error showing type simpledialog: {e}")
                 plenum_type = None

        if max_flow is not None: 
            print("[Controller] Creating the single plenum object...")
            start_coords = (start_x, start_y)
            end_coords = (end_x, end_y)

            plenum_obj = Plenum(start_coords, end_coords, max_flow=max_flow) 
            plenum_obj.type = plenum_type
            plenum_obj.floor_index = self.selected_floor_index

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
                "type": plenum_obj.type
            })

            ivy_bus.publish("disable_tool_button", {"tool": "plenum"})
        
        else:
             print("[Controller] Failed to get valid max_flow, plenum not created.")

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
        
        # Collect vents from all floors
        for floor_idx, floor in enumerate(self.floors):
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
        
        # Debug output to verify data
        print(f"[Controller] Sending ventilation summary with {len(all_vents_data)} vents")
        
        # Send the combined data to the view
        ivy_bus.publish("ventilation_summary_update", {
            "vents": all_vents_data
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
        
        print("[Controller] Application has been reset to initial state")
