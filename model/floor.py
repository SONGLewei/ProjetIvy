class Floor:
    def __init__(self, name):
        self.name = name
        self.walls = []
        self.doors = []
        self.windows = []
        self.vents = []

    def add_wall(self, wall):
        self.walls.append(wall)

    def add_door(self, door):
        self.doors.append(door)

    def add_window(self, window):
        self.windows.append(window)

    def add_vent(self, vent):
        self.vents.append(vent)

    def __repr__(self):
        return (f"<Floor '{self.name}' | "
                f"{len(self.walls)} walls, "
                f"{len(self.doors)} doors, "
                f"{len(self.windows)} windows, "
                f"{len(self.vents)} vents>")
