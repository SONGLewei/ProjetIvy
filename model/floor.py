class Floor:
    def __init__(self, name):
        self.name = name
        self.objects = []
        self.walls = []
        self.doors = []
        self.windows = []
        self.vents = []
        self.height = 2.5

    def add_wall(self, wall):
        self.walls.append(wall)
        self.objects.append(wall)

    def add_door(self, door):
        self.doors.append(door)
        self.objects.append(door)

    def add_window(self, window):
        self.windows.append(window)
        self.objects.append(window)

    def add_vent(self, vent):
        self.vents.append(vent)
    
    def set_height(self, value: float):
        self.height = value

    def __repr__(self):
        return (f"<Floor '{self.name}' | "
                f"{len(self.walls)} walls, "
                f"{len(self.doors)} doors, "
                f"{len(self.windows)} windows, "
                f"{len(self.vents)} vents>")
