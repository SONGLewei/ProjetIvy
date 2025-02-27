from ivy.ivy_bus import ivy_bus
from model.wall import Wall
from model.floor import Floor

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

        self.wall_start_point = None
        self.is_canceled_wall_draw = False

    def handle_draw_wall_request(self, data):
        """
        When the user clicks on the canvas in the View -> If the current tool is 'wall' and there is a selected floor
        add a wall to that floor
        """
        x, y = data.get("x"), data.get("y")
        is_click = data.get("is_click", False)
        is_preview = data.get("is_preview", False)

        if self.selected_floor_index is None or self.current_tool!='wall':
            return

        if is_click:
            #print(f"[Controller] received draw_wall_request: the point of click=({x}, {y})")
            if self.wall_start_point is None:
                self.wall_start_point = (x, y)

            else:
                start = self.wall_start_point
                end   = (x, y)

                wall_obj = Wall(start, end)

                # info pour affichier
                current_floor = self.floors[self.selected_floor_index]
                current_floor.add_wall(wall_obj)
                print(f"in floor {current_floor.name} create wall : {wall_obj}")
                # -------------------

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

        ivy_bus.publish("floor_selected_update", {
            "selected_floor_index": floor_idx,
            "floor_name": selected_floor.name
        })
        
    def handle_new_floor_request(self, data):
        """
        When the user clicks the "New floor" button: insert a new floor above the selected floor
        If no floor is currently selected (or there is no floor at all), make it the first floor
        Clear automatic the canvas
        """
        ivy_bus.publish("clear_canvas_update", {})
        new_floor_name = f"Floor {len(self.floors) + 1}"
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